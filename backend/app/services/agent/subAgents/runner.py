"""
子智能体运行逻辑
"""

import time
import traceback
from pathlib import Path
from typing import Any, Literal

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.services.agent.tools.callback import (
    _current_chat_id,
    _current_model_name,
    is_stop_requested,
)
from app.services.llm_client import resolve_model, init_chat_model_with_reasoning

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

# 子智能体类型到提示文件的映射
SUB_AGENT_PROMPT_FILES: dict[str, list[str]] = {
    "reviewer": ["agent-prompt-reviewer.md"],
    "explore": ["agent-prompt-explore.md"],
    "plan": ["agent-prompt-plan.md"],
    "general-purpose": ["agent-prompt-general-purpose.md"],
}

# 子智能体类型到工具的映射
SUB_AGENT_TOOLS: dict[str, list[str]] = {
    "reviewer": ["read_document", "search_documnet"],
    "explore": ["read_document", "search_documnet"],
    "plan": ["read_document", "search_documnet"],
    "general-purpose": ["read_document", "search_documnet", "generate_document", "delete_document"],
}


# ---------------------------------------------------------------------------
# 工具解析
# ---------------------------------------------------------------------------


def _get_all_tools() -> dict[str, Any]:
    """获取所有可用工具。"""
    from app.services.agent.tools.document_tools import (
        delete_document,
        generate_document,
        read_document,
        search_documnet,
    )

    return {
        "read_document": read_document,
        "search_documnet": search_documnet,
        "generate_document": generate_document,
        "delete_document": delete_document,
    }


def resolve_sub_agent_tools(agent_type: str) -> tuple[list, dict[str, Any]]:
    """根据子智能体类型解析工具列表。"""
    all_tools = _get_all_tools()
    allowed_names = SUB_AGENT_TOOLS.get(agent_type, [])
    tools = [all_tools[name] for name in allowed_names if name in all_tools]
    return tools, {t.name: t for t in tools}


# ---------------------------------------------------------------------------
# 提示词构建
# ---------------------------------------------------------------------------


def _read_prompt_file(fname: str) -> str | None:
    """读取提示文件。"""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    file_path = prompts_dir / fname
    try:
        if file_path.exists():
            return file_path.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return None


def build_sub_agent_system_prompt(agent_type: str) -> str:
    """构建子智能体系统提示。"""
    parts = []
    for fname in SUB_AGENT_PROMPT_FILES.get(agent_type, []):
        content = _read_prompt_file(fname)
        if content:
            parts.append(content)

    if not parts:
        defaults = {
            "reviewer": "You are a professional document reviewer.",
            "explore": "You are a document search specialist.",
            "plan": "You are a planning specialist.",
            "general-purpose": "You are a general-purpose document assistant.",
        }
        parts.append(defaults.get(agent_type, "You are a document assistant."))

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# 运行子智能体
# ---------------------------------------------------------------------------


def run_sub_agent_task(
    description: str,
    prompt: str,
    agent_type: Literal["reviewer", "explore", "plan", "general-purpose"] = "reviewer",
    model: str | None = None,
    max_turns: int | None = None,
) -> str:
    """运行子智能体并返回结果。"""
    from langgraph.config import get_stream_writer

    writer = get_stream_writer()

    if agent_type not in SUB_AGENT_TOOLS:
        available = ", ".join(SUB_AGENT_TOOLS.keys())
        return f"Error: Unknown sub-agent type '{agent_type}'. Available: {available}"

    # 状态消息
    emojis = {"reviewer": "🔍", "explore": "🗺️", "plan": "📋", "general-purpose": "🤖"}
    writer({"type": "status", "content": f"{emojis.get(agent_type, '🤖')} 启动 {agent_type}: {description}"})
    print(f"[SubAgent] 启动 {agent_type}: {description}")

    # 解析工具
    tools, _ = resolve_sub_agent_tools(agent_type)

    # 解析模型
    parent_model = _current_model_name.get(None) or resolve_model("auto")
    use_model = model or parent_model
    llm = init_chat_model_with_reasoning(use_model)

    # 构建提示
    system_prompt = build_sub_agent_system_prompt(agent_type)

    # 创建 agent
    app = create_agent(model=llm, tools=tools, system_prompt=system_prompt, checkpointer=InMemorySaver())

    # 输入消息
    messages = [HumanMessage(content=prompt)]

    # 执行统计
    final_text = ""
    tool_call_count = 0
    start_time = time.time()

    try:
        for stream_item in app.stream(input={"messages": messages}, stream_mode=["values", "custom"]):
            chat_id = _current_chat_id.get(None)
            if is_stop_requested(chat_id):
                print(f"[SubAgent] ⛔ 停止信号")
                break

            if not isinstance(stream_item, tuple):
                continue

            input_type, chunk = stream_item

            if input_type == "custom" and isinstance(chunk, dict):
                writer(chunk)

            elif input_type == "values":
                current_messages = chunk.get("messages", [])

                for msg in current_messages:
                    if isinstance(msg, ToolMessage):
                        tool_call_count += 1

                for msg in reversed(current_messages):
                    if isinstance(msg, AIMessage):
                        content = getattr(msg, "content", "")
                        if content and not getattr(msg, "tool_calls", []):
                            final_text = content
                            break

        duration = time.time() - start_time
        writer(
            {"type": "status", "content": f"✅ {agent_type} 完成，耗时 {duration:.1f}s，工具调用 {tool_call_count} 次"}
        )
        print(f"[SubAgent] ✅ {agent_type} 完成")

    except Exception as e:
        print(f"[SubAgent] ❌ 失败: {e}")
        traceback.print_exc()
        return f"Sub-agent failed: {e}"

    if final_text:
        return final_text
    if tool_call_count > 0:
        return f"{agent_type} completed, executed {tool_call_count} tool calls."
    return "Sub-agent returned no results"


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------


def run_explore_agent(description: str, prompt: str, **kwargs) -> str:
    return run_sub_agent_task(description, prompt, "explore", **kwargs)


def run_plan_agent(description: str, prompt: str, **kwargs) -> str:
    return run_sub_agent_task(description, prompt, "plan", **kwargs)


def run_reviewer_agent(description: str, prompt: str, **kwargs) -> str:
    return run_sub_agent_task(description, prompt, "reviewer", **kwargs)


def run_general_purpose_agent(description: str, prompt: str, **kwargs) -> str:
    return run_sub_agent_task(description, prompt, "general-purpose", **kwargs)


# ---------------------------------------------------------------------------
# 信息
# ---------------------------------------------------------------------------


def get_sub_agent_info(agent_type: str) -> dict[str, Any]:
    """获取子智能体信息。"""
    descriptions = {
        "reviewer": "专业文档评审专家，提供具体的修改建议",
        "explore": "文档搜索和探索专家，快速定位内容",
        "plan": "软件架构师和规划专家，设计实现方案",
        "general-purpose": "通用目的智能体，执行多步骤复杂任务",
    }
    return {
        "type": agent_type,
        "description": descriptions.get(agent_type, "未知类型"),
        "tools": SUB_AGENT_TOOLS.get(agent_type, []),
    }


def list_available_sub_agents() -> list[dict[str, Any]]:
    """列出所有可用的子智能体。"""
    return [get_sub_agent_info(t) for t in SUB_AGENT_TOOLS.keys()]
