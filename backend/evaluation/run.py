import os
import csv
import asyncio
import json
import sys
from typing import List
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client as LangSmithClient, traceable
from tqdm import tqdm

# 添加项目根目录到 path，以便导入 utils
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入绘图工具
from evaluation.utils import plot_task_success, plot_quality_with_tool_usage, plot_radar_chart

load_dotenv()

# Configuration（必须在设置 tracing 环境变量之前定义）
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_EVALUATION_PROJECT") or "WordAgent_evaluation"
DATASET_NAME = os.getenv("LANGSMITH_DATASET_NAME") or "WordAgent_test"

# 启用 LangChain/LangSmith tracing（必须在使用 LANGSMITH_PROJECT 之后）
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT

# 使用百炼的 API（OpenAI 兼容端点）
EVAL_OPENAI_MODEL = os.getenv("EVAL_OPENAI_MODEL")
EVAL_OPENAI_API_KEY = os.getenv("EVAL_OPENAI_API_KEY")
EVAL_OPENAI_BASE_URL = os.getenv("EVAL_OPENAI_BASE_URL")

EVAL_CONCURRENCY = int(os.getenv("EVAL_CONCURRENCY") or "5")

OUTPUT_BASE_DIR = Path(__file__).parent / "outputs"
PROMPT_FILE = Path(__file__).parent / "evaluator_prompt.md"


def load_evaluator_prompt() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Evaluator prompt file not found: {PROMPT_FILE}")


EVALUATOR_PROMPT_TEMPLATE = load_evaluator_prompt()


@dataclass
class EvaluationMetrics:
    """评估指标

    一级指标:
    - task_success: 任务完成度 (0-1)

    核心质量:
    - correctness: 正确性 (0-5)
    - faithfulness: 忠诚度 (0-5)
    - relevance: 相关性 (0-5)

    表达质量:
    - clarity: 清晰度 (0-5)
    - conciseness: 简洁性 (0-5)

    Agent能力:
    - tool_usage: 工具使用 (0-2)
    """
    task_success: int = 0
    correctness: int = 0
    faithfulness: int = 0
    relevance: int = 0
    clarity: int = 0
    conciseness: int = 0
    tool_usage: int = 1

    def to_dict(self) -> dict:
        return asdict(self)

    def quality_score(self) -> float:
        """计算综合质量分数（核心质量 + 表达质量）"""
        return (self.correctness + self.faithfulness + self.relevance + self.clarity + self.conciseness) / 5


@dataclass
class EvaluationResult:
    example_id: str
    model_name: str
    user_input: str
    model_output: str
    metrics: EvaluationMetrics


class LLMEvaluator:
    def __init__(self):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(
            api_key=EVAL_OPENAI_API_KEY,
            base_url=EVAL_OPENAI_BASE_URL,
        )

    @traceable(name="llm_evaluation_call", project_name=LANGSMITH_PROJECT)
    async def _call_llm(self, prompt: str) -> str:
        resp = await self.client.chat.completions.create(
            model=EVAL_OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )
        return resp.choices[0].message.content

    @traceable(name="evaluate_example", project_name=LANGSMITH_PROJECT)
    async def evaluate(self, user_request: str, agent_trace: str) -> EvaluationMetrics:
        prompt = EVALUATOR_PROMPT_TEMPLATE.format(input=user_request, output=agent_trace)

        content = await self._call_llm(prompt)

        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end != 0:
            content = content[start:end]

        try:
            scores = json.loads(content)
        except Exception:
            print(f"JSON parse failed: {content[:200]}")
            return EvaluationMetrics()

        return EvaluationMetrics(
            task_success=int(scores.get("task_success", 0)),
            correctness=int(scores.get("correctness", 0)),
            faithfulness=int(scores.get("faithfulness", 0)),
            relevance=int(scores.get("relevance", 0)),
            clarity=int(scores.get("clarity", 0)),
            conciseness=int(scores.get("conciseness", 0)),
            tool_usage=int(scores.get("tool_usage", 1)),
        )


class DatasetFetcher:
    def __init__(self):
        self.client = LangSmithClient(api_key=LANGSMITH_API_KEY)

    def get_dataset(self):
        dataset = next(self.client.list_datasets(dataset_name=DATASET_NAME), None)
        if not dataset:
            raise ValueError("Dataset not found")

        examples = list(self.client.list_examples(dataset_id=dataset.id))
        return dataset, examples

    @staticmethod
    def format_conversation(messages):
        """Format complete conversation history including tool calls."""
        lines = []
        for msg in messages:
            msg_type = msg.get("type", "")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])

            if msg_type == "human":
                lines.append(f"[User] {content}")

            elif msg_type == "ai":
                if tool_calls:
                    for tc in tool_calls:
                        func_name = tc.get("name", "unknown")
                        args = tc.get("args", {})
                        lines.append(f"[AI -> tool:{func_name}] {args}")
                if content:
                    lines.append(f"[AI Response] {content}")

            elif msg_type == "tool":
                tool_name = msg.get("name", "unknown")
                lines.append(f"[Tool Result: {tool_name}] {content[:500]}...")

        return "\n".join(lines)

    def extract_for_evaluation(self, example):
        """Extract formatted input/output for evaluation."""
        inputs = example.inputs.get("messages", [])
        outputs = example.outputs.get("messages", [])

        human_msgs = [m for m in inputs if m.get("type") == "human"]
        user_request = human_msgs[-1].get("content", "") if human_msgs else ""

        agent_trace = self.format_conversation(outputs)

        return {
            "user_request": user_request,
            "agent_trace": agent_trace,
            "model_name": example.metadata.get("model", "unknown") if example.metadata else "unknown",
        }


class CSVExporter:
    METRICS_COLUMNS = [
        "example_id",
        "model",
        "task_success",
        "correctness",
        "faithfulness",
        "relevance",
        "clarity",
        "conciseness",
        "tool_usage",
    ]

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_results(self, results: List[EvaluationResult]) -> Path:
        csv_file = self.output_dir / "results.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.METRICS_COLUMNS)

            for r in results:
                writer.writerow([
                    r.example_id,
                    r.model_name,
                    r.metrics.task_success,
                    r.metrics.correctness,
                    r.metrics.faithfulness,
                    r.metrics.relevance,
                    r.metrics.clarity,
                    r.metrics.conciseness,
                    r.metrics.tool_usage,
                ])

        return csv_file

    def _export_summary(self, results: List[EvaluationResult], summary_file: Path):
        """Export aggregated summary by model."""
        from collections import defaultdict

        model_results = defaultdict(list)
        for r in results:
            model_results[r.model_name].append(r)

        with open(summary_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "model",
                "total_count",
                "task_success_rate",
                "correctness_avg",
                "faithfulness_avg",
                "relevance_avg",
                "clarity_avg",
                "conciseness_avg",
                "tool_usage_avg",
            ])

            for model, model_results_list in sorted(model_results.items()):
                total = len(model_results_list)
                successful = sum(1 for r in model_results_list if r.metrics.task_success == 1)

                metrics_sums = {
                    "correctness": 0,
                    "faithfulness": 0,
                    "relevance": 0,
                    "clarity": 0,
                    "conciseness": 0,
                    "tool_usage": 0,
                }

                for r in model_results_list:
                    for m in metrics_sums:
                        metrics_sums[m] += getattr(r.metrics, m)

                writer.writerow([
                    model,
                    total,
                    f"{successful / total * 100:.1f}%" if total > 0 else "0%",
                    f"{metrics_sums['correctness'] / total:.2f}" if total > 0 else "0",
                    f"{metrics_sums['faithfulness'] / total:.2f}" if total > 0 else "0",
                    f"{metrics_sums['relevance'] / total:.2f}" if total > 0 else "0",
                    f"{metrics_sums['clarity'] / total:.2f}" if total > 0 else "0",
                    f"{metrics_sums['conciseness'] / total:.2f}" if total > 0 else "0",
                    f"{metrics_sums['tool_usage'] / total:.2f}" if total > 0 else "0",
                ])


async def run_evaluation():
    print("Starting evaluation...")

    dataset_fetcher = DatasetFetcher()
    evaluator = LLMEvaluator()

    dataset, examples = dataset_fetcher.get_dataset()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_BASE_DIR / timestamp

    semaphore = asyncio.Semaphore(EVAL_CONCURRENCY)

    async def process(example):
        async with semaphore:
            eval_data = dataset_fetcher.extract_for_evaluation(example)
            metrics = await evaluator.evaluate(eval_data["user_request"], eval_data["agent_trace"])

            return EvaluationResult(
                example_id=str(example.id),
                model_name=eval_data["model_name"],
                user_input=eval_data["user_request"],
                model_output=eval_data["agent_trace"][:500],
                metrics=metrics,
            )

    results = []
    with tqdm(total=len(examples), desc="Evaluating", unit="task") as pbar:
        async def process_with_progress(example):
            result = await process(example)
            pbar.update(1)
            return result

        results = await asyncio.gather(*[process_with_progress(e) for e in examples])

    csv_exporter = CSVExporter(output_dir)
    csv_path = csv_exporter.export_results(results)

    # 生成可视化图表
    print("Generating charts...")

    # 1. Task Success 柱状图
    plot_task_success(csv_path, output_dir / "task_success.png")

    # 2. 质量指标 + Tool Usage 柱状图（合并在一张图）
    plot_quality_with_tool_usage(csv_path, output_dir / "quality_metrics.png")

    # 3. 雷达图
    plot_radar_chart(csv_path, output_dir / "radar_chart.png")

    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
