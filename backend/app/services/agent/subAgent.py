"""子智能体实现与运行逻辑。"""

import json
import traceback
from typing import Literal

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.config import get_stream_writer

# ---------------------------------------------------------------------------
# 子智能体工具集
# ---------------------------------------------------------------------------

AGENT_TYPE_TOOL_NAMES: dict[str, list[str]] = {
    "reviewer": ["read_document", "search_documnet"],
    "explorer": ["read_document", "search_documnet"],
}


def resolve_sub_agent_tools(agent_type: str):
    """根据子智能体类型返回 (tools_list, tool_map)。"""
    # 延迟导入，避免模块初始化时的循环依赖。
    from app.services.agent.tools.document_tools import (
        delete_document,
        generate_document,
        read_document,
        search_documnet,
    )

    all_tools = {
        "read_document": read_document,
        "generate_document": generate_document,
        "search_documnet": search_documnet,
        "delete_document": delete_document,
    }
    names = AGENT_TYPE_TOOL_NAMES.get(agent_type, [])
    tools = [all_tools[n] for n in names if n in all_tools]
    tool_map = {t.name: t for t in tools}
    return tools, tool_map


# ---------------------------------------------------------------------------
# 子智能体提示文件
# ---------------------------------------------------------------------------

SUB_AGENT_PROMPT_FILES: dict[str, list[str]] = {
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


def build_sub_agent_system_prompt(agent_type: str) -> str:
    """根据子智能体类型拼接系统提示。"""
    from app.services.agent.prompts import _read_prompt_file

    parts: list[str] = []
    for fname in SUB_AGENT_PROMPT_FILES.get(agent_type, []):
        try:
            parts.append(_read_prompt_file(fname))
        except FileNotFoundError:
            pass
    if not parts:
        parts.append("You are a document reviewer. Use read_document and search_documnet to review content.")
    return "\n\n".join(parts)


def run_sub_agent_task(
    description: str,
    prompt: str,
    agent_type: Literal["reviewer", "explorer"],
) -> str:
    """运行子智能体并返回最终文本或统计信息。"""
    from app.services.agent.tools.callback import _current_chat_id, _current_model_name, is_stop_requested
    from app.services.llm_client import resolve_model, init_chat_model_with_reasoning
    from langchain.agents import create_agent
    from langchain_core.messages import HumanMessage

    writer = get_stream_writer()

    if agent_type not in AGENT_TYPE_TOOL_NAMES:
        return f"Error: Unknown sub-agent type '{agent_type}'. Available: {', '.join(AGENT_TYPE_TOOL_NAMES.keys())}"

    writer({"type": "status", "content": f"🤖 正在启动 {agent_type} 子智能体: {description}"})
    print(f"[SubAgent] 启动 {agent_type} 子智能体: {description}")

    tools, _ = resolve_sub_agent_tools(agent_type)

    model_name = _current_model_name.get(None) or resolve_model("auto")
    llm = init_chat_model_with_reasoning(model_name)
    print(f"[SubAgent] 使用模型: {model_name}")

    system_prompt = build_sub_agent_system_prompt(agent_type)
    sub_app = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    messages = [
        HumanMessage(content=prompt),
    ]

    final_text = ""
    generated_docs: list[dict] = []
    seen_tool_call_ids: set[str] = set()
    tool_call_count = 0

    try:
        for stream_item in sub_app.stream(
            input={"messages": messages},
            stream_mode=["values", "custom"],
        ):
            chat_id = _current_chat_id.get(None)
            if is_stop_requested(chat_id):
                print(f"[SubAgent] ⛔ 收到停止信号 (session={chat_id})")
                break

            if not isinstance(stream_item, tuple):
                continue

            input_type, chunk = stream_item

            if input_type == "custom":
                if isinstance(chunk, dict):
                    writer(chunk)

            elif input_type == "values":
                current_messages = chunk.get("messages", [])
                for msg in current_messages:
                    if not isinstance(msg, ToolMessage):
                        continue
                    tid = getattr(msg, "tool_call_id", None)
                    if tid and tid in seen_tool_call_ids:
                        continue
                    if tid:
                        seen_tool_call_ids.add(tid)
                    tool_call_count += 1

                    if getattr(msg, "name", "") == "generate_document":
                        try:
                            doc_json = json.loads(msg.content)
                            if "paragraphs" in doc_json:
                                writer({"type": "json", "content": doc_json})
                                generated_docs.append(doc_json)
                        except (json.JSONDecodeError, TypeError):
                            pass

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


__all__ = [
    "AGENT_TYPE_TOOL_NAMES",
    "SUB_AGENT_PROMPT_FILES",
    "build_sub_agent_system_prompt",
    "resolve_sub_agent_tools",
    "run_sub_agent_task",
]
