# 评估模块

该目录用于评估 Word Agent 在文档编辑场景中的 Agent 执行结果。评估流程会从 LangSmith 数据集中读取样本，将用户请求和 Agent 执行轨迹交给评估模型打分，最后输出 CSV 结果和可视化图表。

评估重点不是单纯判断最终文本好不好，而是综合判断：

- 是否完成用户请求
- 内容是否正确、相关、清晰
- 是否遵循用户约束和工具结果
- 工具调用是否合理
- 不同模型在同一批任务上的表现差异

## 目录说明

| 文件 | 说明 |
|------|------|
| `run.py` | 主评估入口，负责读取数据集、调用评估模型、导出结果和图表 |
| `dataset.py` | LangSmith 数据集查看工具，可用于检查数据集内容 |
| `utils.py` | CSV 读取、指标聚合和图表绘制工具 |
| `evaluator_prompt.md` | 评估模型使用的打分提示词 |
| `outputs/` | 实际评估输出目录 |
| `outputs-example/` | 示例评估图表和结果 |

## 评估流程

1. 从 LangSmith 读取 `LANGSMITH_DATASET_NAME` 指定的数据集。
2. 提取每条样本中的用户请求、Agent 执行轨迹和模型名称。
3. 使用 OpenAI 兼容接口调用评估模型。
4. 评估模型按照 `evaluator_prompt.md` 中的标准返回 JSON 分数。
5. 将每条样本的指标写入 `results.csv`。
6. 基于 CSV 生成任务完成率、质量指标和雷达图。

## 环境配置

在 `backend/.env` 中配置评估所需的 API 和 LangSmith 信息：

```bash
# LangSmith
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_DATASET_NAME=WordAgent_test
LANGSMITH_EVALUATION_PROJECT=WordAgent_evaluation

# 评估模型，支持 OpenAI 兼容接口
EVAL_OPENAI_API_KEY=your_eval_api_key
EVAL_OPENAI_BASE_URL=https://api.openai.com/v1
EVAL_OPENAI_MODEL=gpt-4o

# 并发数量，默认 5
EVAL_CONCURRENCY=5
```

说明：

- `LANGSMITH_API_KEY` 也可以用 `LANGCHAIN_API_KEY` 代替。
- `EVAL_OPENAI_*` 可以和主服务使用不同模型，建议使用稳定、推理能力较强的模型作为裁判模型。
- `EVAL_CONCURRENCY` 过高可能触发接口限流，请根据服务商限制调整。

## 数据集格式

当前实现默认读取 LangSmith Dataset。每条样本应包含：

| 位置 | 字段 | 类型 | 说明 |
|------|------|------|------|
| `inputs` | `messages` | list | 用户输入消息列表 |
| `outputs` | `messages` | list | Agent 输出消息列表，包含最终回复和工具调用轨迹 |
| `metadata` | `model` | str | 生成该条结果的模型名称，用于按模型聚合对比 |

`messages` 中常见消息类型：

| type | 说明 |
|------|------|
| `human` | 用户请求 |
| `ai` | Agent 回复或工具调用 |
| `tool` | 工具执行结果 |

`run.py` 会将这些消息整理为类似下面的执行轨迹：

```text
[User] 帮我润色这段文字
[AI -> tool:read_document] {"startParaIndex": 1}
[Tool Result: read_document] ...
[AI Response] ...
```

如果你的数据不是 LangSmith 格式，可以修改 `run.py` 中的 `DatasetFetcher`：

- `get_dataset()`：改成读取你的数据源
- `extract_for_evaluation()`：改成输出 `user_request`、`agent_trace`、`model_name`

## 查看数据集

运行评估前可以先检查 LangSmith 数据集是否能正常读取：

```bash
cd backend
uv run python -m evaluation.dataset --name WordAgent_test
```

如需导出一份 JSON 方便排查：

```bash
cd backend
uv run python -m evaluation.dataset --name WordAgent_test --output evaluation/outputs/dataset.json
```

## 运行评估

```bash
cd backend
uv run python -m evaluation.run
```

评估结果会输出到：

```text
backend/evaluation/outputs/{timestamp}/
```

当前会生成：

| 文件 | 说明 |
|------|------|
| `results.csv` | 每条样本的原始打分结果 |
| `task_success.png` | 各模型任务完成率柱状图 |
| `quality_metrics.png` | 正确性、忠诚度、相关性、清晰度、简洁性和工具使用的柱状图 |
| `radar_chart.png` | 各模型质量指标雷达图 |

## 评估指标

### 一级指标

| 指标 | 范围 | 说明 |
|------|------|------|
| `task_success` | 0 或 1 | 是否完整完成用户请求。只要明显偏离任务、格式错误或只完成一部分，就应为 0 |

### 内容质量

| 指标 | 范围 | 说明 |
|------|------|------|
| `correctness` | 0-5 | 内容正确性，包括事实、语法、拼写和逻辑 |
| `faithfulness` | 0-5 | 是否忠实遵循用户指令、约束和工具返回结果 |
| `relevance` | 0-5 | 是否围绕用户请求展开，是否存在跑题或无关内容 |
| `clarity` | 0-5 | 表达是否清晰，结构是否容易理解 |
| `conciseness` | 0-5 | 表达是否简洁，是否存在明显冗余 |

### Agent 能力

| 指标 | 范围 | 说明 |
|------|------|------|
| `tool_usage` | 0-2 | 工具选择、调用参数和工具结果使用是否合理 |

评估模型必须返回严格 JSON，字段定义见 `evaluator_prompt.md`。

## 示例效果

### 任务完成率

![](./outputs-example/task_success.png)

### 各项质量指标

| 柱状图 | 雷达图 |
|---|---|
| ![](./outputs-example/quality_metrics.png) | ![](./outputs-example/radar_chart.png) |

## 注意事项

- 评估结果会受裁判模型能力影响，建议固定 `EVAL_OPENAI_MODEL` 后再对比不同被评估模型。
- 数据集中不同模型应使用相同任务集合，否则模型间指标不可直接横向比较。
- 如果评估模型返回的不是合法 JSON，该条样本会回退为默认低分。
- 日志、文档内容或工具结果中如果包含隐私信息，上传 LangSmith 前应先脱敏。
