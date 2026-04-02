"""主智能体调用子智能体的工具。

子智能体类型：
- simplifier: 简化智能体（read_document, generate_document, search_documnet, delete_document）
- reviewer:   审阅智能体（read_document, search_documnet）
"""

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
    "simplifier": ["read_document", "generate_document", "search_documnet", "delete_document"],
    "reviewer": ["read_document", "search_documnet"],
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
# 子智能体系统提示
# ---------------------------------------------------------------------------

_SUB_AGENT_BASE_PROMPTS: dict[str, str] = {
    "simplifier": (
        "你是专业的文档简化与改写智能体。你的职责是根据指令操作 Word 文档。\n"
        "可用工具：read_document（读取文档段落）、generate_document（生成/输出文档内容）、"
        "search_documnet（搜索文档中的内容）、delete_document（删除文档段落）。\n\n"
        "工作流程：\n"
        "1. 凡是简化或改写已有段落，必须先 read_document 读取目标段落，获取原段落样式与 styles。\n"
        "2. 修改已有段落时，必须先 delete_document 删除旧段落，再 generate_document 在原位置插入新段落（delete + generate）。\n"
        "3. 修改已有段落时，除非用户明确要求改格式，否则必须保持原 pStyle/rStyle 与 styles 引用一致。\n"
        "4. 如需定位目标段落，可先用 search_documnet 定位再 read_document 读取。\n"
        "5. 仅新增内容（不是修改已有段落）时，可直接 generate_document。\n\n"
        "请专注于简化、通俗化、压缩冗余和表达重写。完成后，用简短文字总结你做了什么。"
    ),
    "reviewer": (
        "你是专业的文档审阅智能体。你的职责是根据指令审阅和分析文档内容。\n"
        "可用工具：read_document（读取文档段落）、search_documnet（搜索文档中的内容）。\n\n"
        "工作流程：\n"
        "1. 用 search_documnet 定位需要审阅的内容\n"
        "2. 用 read_document 读取相关段落\n"
        "3. 仔细分析内容，给出详细的审阅意见\n\n"
        "请给出专业、具体的审阅反馈，包括问题描述和改进建议。"
    ),
}

# 各类型子智能体需要预加载的提示文件
_SUB_AGENT_PROMPT_FILES: dict[str, list[str]] = {
    "simplifier": [
        "style.md",
        "tool_strategy.md",
        "execution_rules.md",
        "read_document.md",
        "search_documnet.md",
        "generate_document.md",
        "delete_document.md",
    ],
    "reviewer": [
        "style.md",
        "read_document.md",
        "search_documnet.md",
    ],
}


def _build_sub_agent_system_prompt(agent_type: str) -> str:
    """构建子智能体系统提示，包括基础提示和预加载的提示。"""
    from app.services.agent.prompts import _read_prompt_file

    parts = [_SUB_AGENT_BASE_PROMPTS.get(agent_type, "")]
    for fname in _SUB_AGENT_PROMPT_FILES.get(agent_type, []):
        try:
            parts.append(_read_prompt_file(fname))
        except FileNotFoundError:
            pass
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# 子智能体 ReAct 图
# ---------------------------------------------------------------------------

_SUB_AGENT_MAX_TOOL_ROUNDS = 15


def _build_sub_agent_graph(llm_with_tools, tool_map: dict):
    """构建子智能体的 ReAct 工作流（含 repair/retry，与主 Agent 一致）。"""
    from langchain_core.messages import RemoveMessage, SystemMessage
    from langgraph.graph import END, START, MessagesState, StateGraph

    from app.services.utils import normalize_tool_args, parse_tool_args_with_repair

    graph = StateGraph(MessagesState)

    def agent_node(state: MessagesState) -> dict:
        chat_id = _current_chat_id.get(None)
        if is_stop_requested(chat_id):
            return {"messages": []}
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(state: MessagesState) -> dict:
        last_message = state["messages"][-1]
        results = []
        chat_id = _current_chat_id.get(None)
        for tc in last_message.tool_calls:
            if is_stop_requested(chat_id):
                break
            tool_name = tc["name"]
            tool_fn = tool_map.get(tool_name)
            if tool_fn:
                try:
                    args = normalize_tool_args(tool_name, tc.get("args", {}))
                    result = tool_fn.invoke(args)
                    if isinstance(result, dict):
                        content = json.dumps(result, ensure_ascii=False)
                    elif isinstance(result, str):
                        content = result
                    else:
                        content = str(result)
                    results.append(ToolMessage(content=content, tool_call_id=tc["id"], name=tool_name))
                except Exception as e:
                    err = f"错误: 工具 {tool_name} 调用失败: {e}。请按工具 schema 重新构造参数。"
                    print(f"[SubAgent/Tools] ❌ {err}")
                    results.append(ToolMessage(content=err, tool_call_id=tc["id"], name=tool_name))
            else:
                results.append(
                    ToolMessage(content=f"错误: 未知工具 {tool_name}", tool_call_id=tc["id"], name=tool_name)
                )
        return {"messages": results}

    def repair_node(state: MessagesState) -> dict:
        """尝试修复 invalid_tool_calls 并直接执行。"""
        last_message = state["messages"][-1]
        invalid_calls = getattr(last_message, "invalid_tool_calls", []) or []
        chat_id = _current_chat_id.get(None)
        repaired_tool_calls = []
        repaired_results = []

        for tc in invalid_calls:
            if is_stop_requested(chat_id):
                break
            tool_name = tc.get("name", "")
            tool_fn = tool_map.get(tool_name)
            if not tool_fn:
                continue

            parsed_args = parse_tool_args_with_repair(tc.get("args", {}))
            if parsed_args is None:
                print(f"[SubAgent/Repair] ❌ 无法修复工具参数: {tool_name}")
                continue

            try:
                normalized_args = normalize_tool_args(tool_name, parsed_args)
                result = tool_fn.invoke(normalized_args)
                if isinstance(result, dict):
                    content = json.dumps(result, ensure_ascii=False)
                elif isinstance(result, str):
                    content = result
                else:
                    content = str(result)

                repaired_tool_calls.append(
                    {
                        "name": tool_name,
                        "args": normalized_args,
                        "id": tc.get("id", "repaired_invalid_tool_call"),
                        "type": "tool_call",
                    }
                )
                repaired_results.append(
                    ToolMessage(
                        content=content,
                        tool_call_id=tc.get("id", "repaired_invalid_tool_call"),
                        name=tool_name,
                    )
                )
                print(f"[SubAgent/Repair] ✅ 已修复并执行工具: {tool_name}")
            except Exception as e:
                print(f"[SubAgent/Repair] ❌ 工具执行失败: {tool_name}, error={e}")

        if repaired_results:
            return {
                "messages": [
                    RemoveMessage(id=last_message.id),
                    AIMessage(content="", tool_calls=repaired_tool_calls),
                    *repaired_results,
                ]
            }

        # 无法修复，提示重试
        return {
            "messages": [
                RemoveMessage(id=last_message.id),
                SystemMessage(
                    content="[RETRY] 你刚才的 tool call 参数不是合法 JSON。"
                    "请重试，确保 JSON 完整。若内容过长可拆成多次调用。"
                ),
            ]
        }

    def retry_node(state: MessagesState) -> dict:
        """输出被截断时移除失败消息并提示重试。"""
        last_message = state["messages"][-1]
        return {
            "messages": [
                RemoveMessage(id=last_message.id),
                SystemMessage(
                    content="[RETRY] 你刚才的输出被截断（finish_reason=length）。"
                    "请重试，若内容过长可拆成多次工具调用分批输出。"
                ),
            ]
        }

    def should_continue(state: MessagesState) -> str:
        chat_id = _current_chat_id.get(None)
        if is_stop_requested(chat_id):
            return END
        last_message = state["messages"][-1]

        # 有合法 tool_calls → 执行工具
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_rounds = sum(1 for m in state["messages"] if isinstance(m, ToolMessage))
            if tool_rounds >= _SUB_AGENT_MAX_TOOL_ROUNDS:
                print(f"[SubAgent/Router] -> END (已达最大轮次 {_SUB_AGENT_MAX_TOOL_ROUNDS})")
                return END
            return "tools"

        # 有 invalid_tool_calls → 尝试修复
        invalid_calls = getattr(last_message, "invalid_tool_calls", [])
        if invalid_calls:
            print(f"[SubAgent/Router] ⚠️ 检测到 invalid_tool_calls: {[tc.get('name', '?') for tc in invalid_calls]}")
            return "repair"

        # finish_reason=length → 重试一次
        metadata = getattr(last_message, "response_metadata", {})
        if metadata.get("finish_reason") == "length":
            has_retried = any(isinstance(m, SystemMessage) and "[RETRY]" in m.content for m in state["messages"])
            if not has_retried:
                print("[SubAgent/Router] ⚠️ 输出被截断 -> retry")
                return "retry"

        return END

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("repair", repair_node)
    graph.add_node("retry", retry_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "repair": "repair", "retry": "retry", END: END},
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("repair", "agent")
    graph.add_edge("retry", "agent")

    return graph.compile()


# ---------------------------------------------------------------------------
# 工具定义
# ---------------------------------------------------------------------------


@tool
def run_sub_agent(
    description: str,
    prompt: str,
    agent_type: Literal["simplifier", "reviewer"],
) -> str:
    """创建并运行子智能体来完成专项任务。

    可用的子智能体类型：
    - simplifier: 简化智能体，具备读取、生成、搜索、删除文档的能力
    - reviewer:   审阅智能体，具备读取和搜索文档的能力

    Args:
        description: 任务简要描述（如"生成项目报告"、"审阅合同条款"）
        prompt: 给子智能体的详细任务指令
        agent_type: 子智能体类型（simplifier / reviewer）
    """
    writer = get_stream_writer()

    if agent_type not in _AGENT_TYPE_TOOL_NAMES:
        return f"错误: 未知的子智能体类型 '{agent_type}'。可选: {', '.join(_AGENT_TYPE_TOOL_NAMES.keys())}"

    writer({"type": "status", "content": f"🤖 正在启动 {agent_type} 子智能体: {description}"})
    print(f"[SubAgent] 启动 {agent_type} 子智能体: {description}")

    # ---- 准备工具 ----
    tools, tool_map = _resolve_tools(agent_type)

    # ---- 创建 LLM（继承主 Agent 的模型）----
    from langchain.chat_models import init_chat_model

    from app.services.llm_client import get_llm_init_kwargs, resolve_model

    model_name = _current_model_name.get(None) or resolve_model("auto")
    llm = init_chat_model(**get_llm_init_kwargs(model_name))
    print(f"[SubAgent] 使用模型: {model_name}")
    llm_with_tools = llm.bind_tools(tools)

    # ---- 构建子图 ----
    sub_app = _build_sub_agent_graph(llm_with_tools, tool_map)

    from langchain_core.messages import HumanMessage, SystemMessage

    system_prompt = _build_sub_agent_system_prompt(agent_type)
    messages = [
        SystemMessage(content=system_prompt),
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
                # 转发子智能体的状态消息到主流
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

                # 提取最后一条 AI 消息（无 tool_calls 即为最终回复）
                for msg in reversed(current_messages):
                    if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", []):
                        final_text = msg.content
                        break

        writer({"type": "status", "content": f"✅ {agent_type} 子智能体完成任务"})
        print(f"[SubAgent] ✅ {agent_type} 子智能体完成，工具调用 {tool_call_count} 次")

    except Exception as e:
        print(f"[SubAgent] ❌ 子智能体执行失败: {e}")
        traceback.print_exc()
        return f"子智能体执行失败: {e}"

    if final_text:
        return final_text
    if generated_docs:
        return f"{agent_type} 子智能体已完成任务，生成了 {len(generated_docs)} 个文档片段。"
    if tool_call_count > 0:
        return f"{agent_type} 子智能体已完成任务，执行了 {tool_call_count} 次工具调用。"
    return "子智能体未返回结果"
