"""
LangSmith Evaluation for WordAgent - Writing Quality Metrics

This script evaluates AI-generated writing using LLM-based evaluation without tools.
Metrics: task_completion, clarity, naturalness, conciseness, redundancy
"""

import os
import csv
import asyncio
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client as LangSmithClient

load_dotenv()

# Configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
DATASET_NAME = os.getenv("LANGSMITH_DATASET_NAME") or "WordAgent_test"
EVAL_OPENAI_MODEL = os.getenv("EVAL_OPENAI_MODEL") or "gpt-5.5"
EVAL_OPENAI_API_KEY = os.getenv("EVAL_OPENAI_API_KEY") or None
EVAL_OPENAI_BASE_URL = os.getenv("EVAL_OPENAI_BASE_URL") or None
EVAL_CONCURRENCY = int(os.getenv("EVAL_CONCURRENCY") or "5")

# Output directory
OUTPUT_BASE_DIR = Path(__file__).parent / "output"

# Prompt file path
PROMPT_FILE = Path(__file__).parent / "evaluator_prompt.md"


def load_evaluator_prompt() -> str:
    """Load evaluator prompt template from file."""
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Evaluator prompt file not found: {PROMPT_FILE}")


EVALUATOR_PROMPT_TEMPLATE = load_evaluator_prompt()


@dataclass
class EvaluationMetrics:
    """Writing quality evaluation metrics."""
    task_completion: int = 0
    clarity: int = 0
    naturalness: int = 0
    conciseness: int = 0
    redundancy: int = 0


@dataclass
class EvaluationResult:
    """Result of a single evaluation."""
    example_id: str
    model_name: str
    user_input: str
    model_output: str
    metrics: EvaluationMetrics


class LLMEvaluator:
    """LLM-based evaluator using the specified rubric."""

    def __init__(self, model_name: str = None, api_key: str = None, base_url: str = None):
        from openai import AsyncOpenAI
        if model_name is None:
            model_name = EVAL_OPENAI_MODEL
        self.model_name = model_name

        effective_api_key = api_key or EVAL_OPENAI_API_KEY
        effective_base_url = base_url or EVAL_OPENAI_BASE_URL

        self.client = AsyncOpenAI(
            api_key=effective_api_key,
            base_url=effective_base_url if effective_base_url else None,
        )

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API directly with raw client."""
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=4096,
            stream=False,
        )

        if isinstance(response, str):
            return response

        if hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content

        return str(response)

    async def evaluate(self, user_input: str, model_output: str) -> EvaluationMetrics:
        import json
        import re

        prompt = EVALUATOR_PROMPT_TEMPLATE.format(input=user_input, output=model_output)
        content = await self._call_llm(prompt)
        if not isinstance(content, str):
            content = str(content)

        json_pattern = (
            r'\{\s*"task_completion"\s*:\s*([01])\s*,'
            r'\s*"clarity"\s*:\s*([0-5])\s*,'
            r'\s*"naturalness"\s*:\s*([0-5])\s*,'
            r'\s*"conciseness"\s*:\s*([0-5])\s*,'
            r'\s*"redundancy"\s*:\s*([0-5])\s*\}'
        )

        matches = list(re.finditer(json_pattern, content, re.DOTALL))

        if matches:
            match = matches[-1]
            scores = {
                "task_completion": int(match.group(1)),
                "clarity": int(match.group(2)),
                "naturalness": int(match.group(3)),
                "conciseness": int(match.group(4)),
                "redundancy": int(match.group(5)),
            }
        else:
            json_start = content.find('"task_completion"')
            if json_start != -1:
                partial = content[json_start:]
                open_braces = partial.count("{") - partial.count("}")
                if open_braces > 0:
                    partial += "}" * open_braces
                try:
                    scores = json.loads(partial)
                except json.JSONDecodeError:
                    scores = None
            else:
                scores = None

        if scores:
            return EvaluationMetrics(
                task_completion=int(scores.get("task_completion", 0)),
                clarity=int(scores.get("clarity", 0)),
                naturalness=int(scores.get("naturalness", 0)),
                conciseness=int(scores.get("conciseness", 0)),
                redundancy=int(scores.get("redundancy", 0)),
            )

        print(f"Warning: Could not parse evaluation response: {content[:300]}")
        return EvaluationMetrics()


class DatasetFetcher:
    """Fetch and parse LangSmith dataset."""

    def __init__(self):
        self.client = LangSmithClient(api_key=LANGSMITH_API_KEY)

    def get_dataset(self, dataset_name: str = DATASET_NAME):
        dataset = None
        for ds in self.client.list_datasets(dataset_name=dataset_name):
            dataset = ds
            break

        if dataset is None:
            raise ValueError(f"Dataset '{dataset_name}' not found")

        examples = list(self.client.list_examples(dataset_id=dataset.id))
        return dataset, examples

    @staticmethod
    def extract_user_input(messages: List[Dict]) -> str:
        for msg in messages:
            if msg.get("type") == "human":
                return msg.get("content", "")
        return ""

    @staticmethod
    def extract_model_output(messages: List[Dict]) -> str:
        last_ai = ""
        for msg in messages:
            if msg.get("type") == "ai":
                last_ai = msg.get("content", "")
        return last_ai

    @staticmethod
    def extract_model_name(metadata: Dict) -> str:
        return metadata.get("model", "unknown")


class CSVExporter:
    """Export evaluation results to CSV."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_results(self, results: List[EvaluationResult]) -> Path:
        filename = self.output_dir / "summary.csv"

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "example_id", "model", "task_completion", "clarity",
                "naturalness", "conciseness", "redundancy",
            ])
            for result in results:
                writer.writerow([
                    result.example_id,
                    result.model_name,
                    result.metrics.task_completion,
                    result.metrics.clarity,
                    result.metrics.naturalness,
                    result.metrics.conciseness,
                    result.metrics.redundancy,
                ])

        print(f"Summary CSV: {filename}")
        return filename


async def _evaluate_single(
    evaluator: LLMEvaluator,
    semaphore: asyncio.Semaphore,
    example,
    dataset_fetcher: DatasetFetcher,
    index: int,
    total: int,
    lock: asyncio.Lock,
) -> EvaluationResult:
    async with semaphore:
        input_messages = example.inputs.get("messages", [])
        output_messages = example.outputs.get("messages", [])

        user_input = dataset_fetcher.extract_user_input(input_messages)
        model_output = dataset_fetcher.extract_model_output(output_messages)
        model_name = dataset_fetcher.extract_model_name(example.metadata or {})

        metrics = await evaluator.evaluate(user_input, model_output)

        result = EvaluationResult(
            example_id=str(example.id),
            model_name=model_name,
            user_input=user_input,
            model_output=model_output,
            metrics=metrics,
        )

        async with lock:
            print(
                f"[{index}/{total}] task_completion={metrics.task_completion}, "
                f"clarity={metrics.clarity}, naturalness={metrics.naturalness}, "
                f"conciseness={metrics.conciseness}, redundancy={metrics.redundancy}"
            )

        return result


async def run_evaluation():
    """Main evaluation function with concurrent processing."""
    print("=" * 60)
    print("WordAgent Writing Quality Evaluation")
    print("=" * 60)
    print()
    print(f"Model: {EVAL_OPENAI_MODEL}")
    if EVAL_OPENAI_BASE_URL:
        print(f"Base URL: {EVAL_OPENAI_BASE_URL}")
    print(f"Concurrency: {EVAL_CONCURRENCY}")
    print()

    dataset_fetcher = DatasetFetcher()
    evaluator = LLMEvaluator(
        model_name=EVAL_OPENAI_MODEL,
        api_key=EVAL_OPENAI_API_KEY,
        base_url=EVAL_OPENAI_BASE_URL,
    )

    print("Loading dataset...")
    dataset, examples = dataset_fetcher.get_dataset()
    print(f"Dataset: {dataset.name}")
    print(f"Number of examples: {len(examples)}")
    print()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_BASE_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        semaphore = asyncio.Semaphore(EVAL_CONCURRENCY)
        lock = asyncio.Lock()
        tasks = [
            _evaluate_single(evaluator, semaphore, example, dataset_fetcher, i + 1, len(examples), lock)
            for i, example in enumerate(examples)
        ]
        results: List[EvaluationResult] = await asyncio.gather(*tasks)

        print()

        csv_exporter = CSVExporter(output_dir)
        csv_path = csv_exporter.export_results(results)

        print()
        print("=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)

        n = len(results)
        if n > 0:
            avg_tc = sum(r.metrics.task_completion for r in results) / n * 100
            completed = sum(r.metrics.task_completion for r in results)
            avg_c = sum(r.metrics.clarity for r in results) / n
            avg_n = sum(r.metrics.naturalness for r in results) / n
            avg_con = sum(r.metrics.conciseness for r in results) / n
            avg_r = sum(r.metrics.redundancy for r in results) / n

            print(f"Examples: {n}")
            print(f"Task Completion: {avg_tc:.1f}% ({completed}/{n})")
            print(f"Clarity: {avg_c:.2f}/5")
            print(f"Naturalness: {avg_n:.2f}/5")
            print(f"Conciseness: {avg_con:.2f}/5")
            print(f"Redundancy: {avg_r:.2f}/5")

        print()
        print("Generating charts...")
        from evaluation.utils import plot_task_completion, plot_quality_metrics
        task_completion_chart_path = output_dir / "task_completion.png"
        quality_chart_path = output_dir / "quality_metrics.png"
        plot_task_completion(csv_path, task_completion_chart_path)
        plot_quality_metrics(csv_path, quality_chart_path)

        print()
        print(f"Results saved to: {output_dir}")

    except Exception:
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)
        raise


def main():
    """Entry point for running evaluation."""
    import asyncio
    asyncio.run(run_evaluation())


if __name__ == "__main__":
    main()
