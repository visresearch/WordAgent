"""主智能体调用子智能体的工具。"""

import json
import traceback
from typing import Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from .callback import _current_chat_id, _current_model_name, is_stop_requested

# ---------------------------------------------------------------------------
# 子智能体工具集
# ---------------------------------------------------------------------------

_AGENT_TYPE_TOOL_NAMES: dict[str, list[str]] = {
    "reviewer": ["read_document", "search_documnet"],
    "explorer": ["read_document", "search_documnet"],
}


def _resolve_tools(agent_type: str):
    """根据子智能体类型返回 (tools_list, tool_map)。"""
    from .document_tools import delete_document, generate_document, read_document, search_documnet

    _all = {
        "read_document": read_document,
        "generate_document": generate_document,
        "search_documnet": search_documnet,
        "delete_document": delete_document,
    }
    names = _AGENT_TYPE_TOOL_NAMES.get(agent_type, [])
    tools = [_all[n] for n in names if n in _all]
    tool_map = {t.name: t for t in tools}
    return tools, tool_map


# ---------------------------------------------------------------------------
# 子智能体提示文件
# ---------------------------------------------------------------------------

# 每类子智能体预加载的提示文件
_SUB_AGENT_PROMPT_FILES: dict[str, list[str]] = {
    "reviewer": [
        "agent-prompt-reviewer.md",
        "system-prompt-tone-and-style-concise-output.md",
        "system-prompt-tool-usage-read-document.md",
        "system-prompt-tool-usage-search-document.md",
    ],
    "explorer": [
        "agent-prompt-explorer.md",
        "system-prompt-tone-and-style-concise-output.md",
        "system-prompt-tool-usage-read-document.md",
        "system-prompt-tool-usage-search-document.md",
    ],
}


def _build_sub_agent_system_prompt(agent_type: str) -> str:
    """根据子智能体类型拼接系统提示。"""
    from app.services.agent.prompts import _read_prompt_file

    parts: list[str] = []
    for fname in _SUB_AGENT_PROMPT_FILES.get(agent_type, []):
        try:
            parts.append(_read_prompt_file(fname))
        except FileNotFoundError:
            pass
    if not parts:
        parts.append("You are a document reviewer. Use read_document and search_documnet to review content.")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# 子智能体最大工具轮次
# ---------------------------------------------------------------------------

_SUB_AGENT_MAX_TOOL_ROUNDS = 15


# ---------------------------------------------------------------------------
# 工具定义
# ---------------------------------------------------------------------------


@tool
def run_sub_agent(
    description: str,
    prompt: str,
    agent_type: Literal["reviewer", "explorer"],
) -> str:
    """创建并运行子智能体来完成专项任务。

    可用子智能体类型：
    - reviewer: 审阅智能体（读取 + 搜索）
    - explorer: 探索智能体（快速搜索 + 分析，只读）

    Args:
        description: 任务简要描述
        prompt: 给子智能体的详细任务指令
        agent_type: 子智能体类型（reviewer / explorer）
    """
    writer = get_stream_writer()

    if agent_type not in _AGENT_TYPE_TOOL_NAMES:
        return f"Error: Unknown sub-agent type '{agent_type}'. Available: {', '.join(_AGENT_TYPE_TOOL_NAMES.keys())}"

    writer({"type": "status", "content": f"🤖 正在启动 {agent_type} 子智能体: {description}"})
    print(f"[SubAgent] 启动 {agent_type} 子智能体: {description}")

    # ---- 准备工具 ----
    tools, _ = _resolve_tools(agent_type)

    # ---- 创建 LLM（继承主 Agent 的模型）----
    from langchain.agents import create_agent
    from langchain.chat_models import init_chat_model

    from app.services.llm_client import get_llm_init_kwargs, resolve_model

    model_name = _current_model_name.get(None) or resolve_model("auto")
    llm = init_chat_model(**get_llm_init_kwargs(model_name))
    print(f"[SubAgent] 使用模型: {model_name}")

    # ---- 使用 create_agent 构建子智能体（与主 Agent 一致）----
    system_prompt = _build_sub_agent_system_prompt(agent_type)
    sub_app = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    from langchain_core.messages import HumanMessage

    messages = [
        HumanMessage(content=prompt),
    ]

    # ---- 运行子智能体 ----
    final_text = ""
    generated_docs: list[dict] = []
    _seen_tool_call_ids: set[str] = set()
    tool_call_count = 0

    try:
        for stream_item in sub_app.stream(
            input={"messages": messages},
            stream_mode=["values", "custom"],
        ):
            # 检查停止信号
            chat_id = _current_chat_id.get(None)
            if is_stop_requested(chat_id):
                print(f"[SubAgent] ⛔ 收到停止信号 (session={chat_id})")
                break

            if not isinstance(stream_item, tuple):
                continue

            input_type, chunk = stream_item

            if input_type == "custom":
                # 转发子智能体状态消息到主流
                if isinstance(chunk, dict):
                    writer(chunk)

            elif input_type == "values":
                current_messages = chunk.get("messages", [])
                for msg in current_messages:
                    if not isinstance(msg, ToolMessage):
                        continue
                    tid = getattr(msg, "tool_call_id", None)
                    if tid and tid in _seen_tool_call_ids:
                        continue
                    if tid:
                        _seen_tool_call_ids.add(tid)
                    tool_call_count += 1

                    # 转发 generate_document 的文档 JSON 到前端
                    if getattr(msg, "name", "") == "generate_document":
                        try:
                            doc_json = json.loads(msg.content)
                            if "paragraphs" in doc_json:
                                writer({"type": "json", "content": doc_json})
                                generated_docs.append(doc_json)
                        except (json.JSONDecodeError, TypeError):
                            pass

                # 提取最后一条 AI 消息（无 tool_calls 即最终回复）
                for msg in reversed(current_messages):
                    if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", []):
                        final_text = msg.content
                        break

        writer({"type": "status", "content": f"✅ {agent_type} 子智能体完成任务"})
        print(f"[SubAgent] ✅ {agent_type} 子智能体完成，工具调用 {tool_call_count} 次")

    except Exception as e:
        print(f"[SubAgent] ❌ 子智能体执行失败: {e}")
        traceback.print_exc()
        return f"Sub-agent execution failed: {e}"

    if final_text:
        return final_text
    if generated_docs:
        return f"{agent_type} sub-agent completed, generated {len(generated_docs)} document fragments."
    if tool_call_count > 0:
        return f"{agent_type} sub-agent completed, executed {tool_call_count} tool calls."
    return "Sub-agent returned no results"
