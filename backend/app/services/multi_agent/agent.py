"""
Multi-agent document processing system - Uses LangGraph to orchestrate 5 specialized Agents.

Flow: Planner -> Research -> Outline -> Writer -> Reviewer (loop to Writer if needed)
"""

import asyncio
import concurrent.futures
import json
import os
import sys
import time
import traceback
from collections.abc import AsyncGenerator


def _get_env_int(name: str, default: int) -> int:
    """Read positive int env var with fallback."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
        return value if value > 0 else default
    except Exception:
        return default


class ContextOverflowError(Exception):
    """Context overflow exception with compressed history for retry."""

    def __init__(self, message: str, compressed_history: list):
        super().__init__(message)
        self.compressed_history = compressed_history


def _is_transient_stream_error(exc: Exception) -> bool:
    """Check if error is a retryable streaming network error."""
    text = str(exc).lower()
    transient_signals = [
        "incomplete chunked read",
        "peer closed connection",
        "server disconnected",
        "connection reset",
        "read timeout",
        "remoteprotocolerror",
    ]
    return any(sig in text for sig in transient_signals)


def _is_context_overflow_error(exc: Exception) -> bool:
    """Check if error is a context overflow error."""
    text = str(exc).lower()
    overflow_signals = [
        "413",
        "context_length",
        "too many tokens",
        "maximum context",
        "exceeds context",
        "token limit",
    ]
    return any(sig in text for sig in overflow_signals)


# region LangSmith (optional)


def _try_init_langsmith():
    """Try to load .env and init LangSmith env vars, skip silently on failure."""
    try:
        from pathlib import Path
        from dotenv import load_dotenv

        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).parent / ".env")
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(Path(meipass) / ".env")

        candidates.append(Path(__file__).resolve().parent.parent.parent.parent / ".env")
        candidates.append(Path.cwd() / ".env")

        seen: set[Path] = set()
        for env_path in candidates:
            try:
                resolved = env_path.resolve()
            except Exception:
                resolved = env_path
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.exists():
                load_dotenv(resolved, override=False)

        if os.environ.get("LANGSMITH_API_KEY") and os.environ.get("LANGSMITH_PROJECT"):
            print("[LangSmith] Multi-agent tracing enabled, project =", os.environ.get("LANGSMITH_PROJECT", "default"))
            return True
    except Exception:
        pass
    return False


_langsmith_enabled = _try_init_langsmith()
_AGENT_RECURSION_LIMIT = _get_env_int("WORDAGENT_AGENT_RECURSION_LIMIT", 25)

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.services.llm_client import LLMClientManager, resolve_model
from app.services.multi_agent.prompts import get_agent_prompt
from app.services.utils import normalize_tool_args, parse_tool_args_with_repair
from app.services.multi_agent.tools import (
    AGENT_TOOLS,
    TOOL_MAP,
    _current_chat_id,
    register_loop,
    is_stop_requested,
    create_workflow,
    review_document,
    read_document,
    generate_document,
    delete_document,
    search_documnet,
    load_skill_context,
    load_mcp_tools,
    build_mcp_tools_prompt,
)
from app.services.agent.tools.callback import _current_model_name
from app.services.agent.skills import build_skills_prompt


# region State


class MultiAgentState(BaseModel):
    """Multi-agent shared state."""

    user_message: str = ""
    document_range: list[dict] = Field(default_factory=list)
    document_meta: list | dict = Field(default_factory=dict)  # 支持单个文档（dict）和多个文档（list）
    attached_files: list[dict] = Field(default_factory=list)
    memory_context: str = ""
    workflow: dict = Field(default_factory=dict)
    research_data: str = ""
    outline: str = ""
    document_json: dict = Field(default_factory=dict)
    review_result: dict = Field(default_factory=dict)
    current_step_index: int = 0
    messages: list = Field(default_factory=list)


# region LLM Factory


def _create_llm(model_name: str):
    """Create LLM instance (with reasoning_content support)."""
    from app.services.llm_client import get_temperature, get_https_proxy_url, get_http_proxy_url, ChatOpenAI

    provider_info = LLMClientManager.get_provider_info(model_name)
    proxy_url = get_https_proxy_url() or get_http_proxy_url()

    _proxy_env_keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]
    saved_env = {}
    if not proxy_url:
        for key in _proxy_env_keys:
            if key in os.environ:
                saved_env[key] = os.environ.pop(key)

    try:
        import httpx

        http_client = httpx.Client(proxy=proxy_url)
        http_async_client = httpx.AsyncClient(proxy=proxy_url)
        return ChatOpenAI(
            model=model_name,
            openai_api_key=provider_info.api_key,
            openai_api_base=provider_info.base_url,
            temperature=get_temperature(),
            max_tokens=16384,
            streaming=True,
            http_client=http_client,
            http_async_client=http_async_client,
        )
    finally:
        os.environ.update(saved_env)


# region Sub-Agent ReAct Runner


def _run_sub_agent(
    llm,
    agent_name: str,
    task: str,
    tools: list,
    context: str = "",
    max_iterations: int | None = None,
) -> tuple[str, dict | None, list[dict]]:
    """Run a sub-agent ReAct loop (synchronous, in thread)."""
    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)
    system_prompt = get_agent_prompt(agent_name)

    messages = [SystemMessage(content=system_prompt)]

    from datetime import datetime

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M") + " " + weekdays[now.weekday()]
    messages.append(SystemMessage(content=f"Current time: {current_time}"))

    user_content = task
    if context:
        user_content = f"{task}\n\n---\nReference materials from previous steps:\n{context}"
    messages.append(HumanMessage(content=user_content))

    last_structured_result = None
    text_output = ""
    _writer_generated = False
    _tool_data: list[dict] = []
    _retry_count = 0

    chat_id = _current_chat_id.get(None)
    if max_iterations is None:
        max_iterations = _AGENT_RECURSION_LIMIT
    print(f"[MultiAgent] {agent_name} sub-agent max_iterations={max_iterations}")

    def _should_stop() -> bool:
        if is_stop_requested(chat_id):
            print(f"  [{agent_name}] Stop requested, terminating (session={chat_id})")
            return True
        return False

    def _fmt_invalid_tool_call(tc) -> str:
        if isinstance(tc, dict):
            name = tc.get("name", "?")
            call_id = tc.get("id", "?")
            err = tc.get("error") or "unknown_error"
            raw_args = tc.get("args")
        else:
            name = getattr(tc, "name", "?")
            call_id = getattr(tc, "id", "?")
            err = getattr(tc, "error", None) or "unknown_error"
            raw_args = getattr(tc, "args", None)

        raw_args_str = (
            str(raw_args)[:300] + "..." if raw_args and len(str(raw_args)) > 300 else str(raw_args) if raw_args else ""
        )
        return f"name={name}, id={call_id}, error={err}, raw_args={raw_args_str}"

    def _diagnose_invalid_args(tc) -> str:
        raw_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", None)
        if raw_args is None:
            return "args_missing"
        if isinstance(raw_args, dict):
            return "args_is_dict_but_marked_invalid"
        if not isinstance(raw_args, str):
            return f"args_type_unexpected={type(raw_args).__name__}"
        try:
            json.loads(raw_args)
            return "json_parse_ok_but_tool_call_marked_invalid"
        except Exception as e:
            return f"json_parse_error={e}"

    def _try_repair_and_execute_invalid_calls(invalid_calls) -> bool:
        nonlocal last_structured_result, _writer_generated, _tool_data

        repaired_any = False
        repaired_tool_calls = []
        repaired_tool_messages = []
        for tc in invalid_calls:
            if _should_stop():
                break

            if isinstance(tc, dict):
                tool_name = tc.get("name", "")
                tool_call_id = tc.get("id", "repaired_invalid_tool_call")
                raw_args = tc.get("args")
            else:
                tool_name = getattr(tc, "name", "")
                tool_call_id = getattr(tc, "id", "repaired_invalid_tool_call")
                raw_args = getattr(tc, "args", None)

            tool_fn = tool_map.get(tool_name)
            if not tool_fn:
                continue

            parsed_args = parse_tool_args_with_repair(raw_args)
            if parsed_args is None:
                continue

            try:
                normalized_args = normalize_tool_args(tool_name, parsed_args)
                result = tool_fn.invoke(normalized_args)
                if isinstance(result, dict):
                    content = json.dumps(result, ensure_ascii=False)
                    last_structured_result = result
                elif isinstance(result, str):
                    content = result
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, dict):
                            last_structured_result = parsed
                    except (json.JSONDecodeError, ValueError):
                        pass
                else:
                    content = str(result)

                repaired_tool_calls.append(
                    {
                        "name": tool_name,
                        "args": normalized_args,
                        "id": tool_call_id,
                        "type": "tool_call",
                    }
                )
                repaired_tool_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id, name=tool_name))
                repaired_any = True
                print(f"  [{agent_name}] Repaired invalid tool_call: {tool_name}")

                # 收集所有工具调用结果，用于后续步骤共享
                _tool_data.append(
                    {
                        "tool": tool_name,
                        "args": normalized_args,
                        "result": content,
                        "is_mcp": tool_name.startswith("mcp_")
                        or tool_name
                        not in (
                            "search_documnet",
                            "read_document",
                            "generate_document",
                            "delete_document",
                            "load_skill_context",
                            "create_workflow",
                            "review_document",
                        ),
                    }
                )

                if agent_name == "writer" and tool_name == "generate_document":
                    _writer_generated = True
            except Exception as e:
                err_text = f"Repaired tool '{tool_name}' execution failed: {e}"
                print(f"  [{agent_name}] Repair failed: {err_text}")
                repaired_tool_messages.append(ToolMessage(content=err_text, tool_call_id=tool_call_id, name=tool_name))

        if repaired_any:
            messages.append(AIMessage(content="", tool_calls=repaired_tool_calls))
            messages.extend(repaired_tool_messages)

        return repaired_any

    for iteration in range(max_iterations):
        if _should_stop():
            text_output = ""
            break

        response = llm_with_tools.invoke(messages)

        invalid_calls = getattr(response, "invalid_tool_calls", [])
        if invalid_calls:
            finish_reason = None
            if hasattr(response, "response_metadata") and isinstance(response.response_metadata, dict):
                finish_reason = response.response_metadata.get("finish_reason")

            if not hasattr(response, "tool_calls") or not response.tool_calls:
                if _try_repair_and_execute_invalid_calls(invalid_calls):
                    print(f"  [{agent_name}] Invalid tool_calls auto-repaired, continuing")
                    continue

                _retry_count += 1
                invalid_names = [
                    tc.get("name", "?") if isinstance(tc, dict) else getattr(tc, "name", "?") for tc in invalid_calls
                ]
                print(f"  [{agent_name}] Invalid tool calls: {invalid_names}, retry ({_retry_count})")
                for idx, tc in enumerate(invalid_calls, 1):
                    print(f"  [{agent_name}]    invalid#{idx}: {_fmt_invalid_tool_call(tc)}")

                if _retry_count <= 2:
                    if _should_stop():
                        text_output = ""
                        break
                    messages.append(
                        SystemMessage(
                            content="Tool call format incomplete. Use proper JSON format with correct style references (pS_*, rS_*, etc.). Define all referenced styles in styles dictionary. For long content, split into multiple generate_document calls."
                        )
                    )
                    continue
                else:
                    text_output = response.content or ""
                    print(f"  [{agent_name}] Retry limit exceeded, giving up")
                    break
            else:
                print(f"  [{agent_name}] Filtering invalid tool calls, keeping valid ones")
                for idx, tc in enumerate(invalid_calls, 1):
                    print(f"  [{agent_name}]    dropped_invalid#{idx}: {_fmt_invalid_tool_call(tc)}")
                response = AIMessage(content=response.content, tool_calls=response.tool_calls)

        messages.append(response)

        if not hasattr(response, "tool_calls") or not response.tool_calls:
            text_output = response.content or ""
            if agent_name == "writer" and not _writer_generated:
                messages.append(
                    HumanMessage(
                        content="You must call generate_document tool to output content. Do not output text directly."
                    )
                )
                continue
            break

        for tc in response.tool_calls:
            if _should_stop():
                break
            tool_name = tc["name"]
            print(f"  [{agent_name}] Calling tool: {tool_name}")
            tool_fn = tool_map.get(tool_name)
            if tool_fn:
                try:
                    tool_args = normalize_tool_args(tool_name, tc.get("args", {}))
                    result = tool_fn.invoke(tool_args)
                    if isinstance(result, dict):
                        content = json.dumps(result, ensure_ascii=False)
                        last_structured_result = result
                    elif isinstance(result, str):
                        content = result
                        try:
                            parsed = json.loads(content)
                            if isinstance(parsed, dict):
                                last_structured_result = parsed
                        except (json.JSONDecodeError, ValueError):
                            pass
                    else:
                        content = str(result)

                    messages.append(ToolMessage(content=content, tool_call_id=tc["id"], name=tool_name))

                    # 收集所有工具调用结果，用于后续步骤共享
                    _tool_data.append(
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "result": content,
                            "is_mcp": tool_name.startswith("mcp_")
                            or tool_name
                            not in (
                                "search_documnet",
                                "read_document",
                                "generate_document",
                                "delete_document",
                                "load_skill_context",
                                "create_workflow",
                                "review_document",
                            ),
                        }
                    )

                    if agent_name == "writer" and tool_name == "generate_document":
                        _writer_generated = True
                except Exception as e:
                    # 为不同工具生成友好的错误消息
                    is_mcp_tool = tool_name.startswith("mcp_") or tool_name not in (
                        "search_documnet",
                        "read_document",
                        "generate_document",
                        "delete_document",
                        "load_skill_context",
                        "create_workflow",
                        "review_document",
                    )
                    if is_mcp_tool:
                        err = f"MCP tool '{tool_name}' execution failed: {e}. The error has been returned as tool result. Please analyze the error and decide how to proceed - you may retry with corrected parameters, use an alternative tool, or report the failure in your response."
                    elif tool_name == "generate_document":
                        err = f"Tool {tool_name} failed: {e}. Use correct schema format. For generate_document, document must be an object, not a JSON string."
                    else:
                        err = f"Tool {tool_name} failed: {e}. Please check the parameters and try again."
                    print(f"  [{agent_name}] {err}")
                    messages.append(ToolMessage(content=err, tool_call_id=tc["id"], name=tool_name))
            else:
                messages.append(
                    ToolMessage(content=f"Unknown tool: {tool_name}", tool_call_id=tc["id"], name=tool_name)
                )
    else:
        for m in reversed(messages):
            if isinstance(m, AIMessage) and m.content:
                text_output = m.content
                break

    return text_output, last_structured_result, _tool_data


def _format_shared_tool_data(tool_data: list[dict]) -> str:
    """Format collected tool data for sharing (all tools including MCP)."""
    if not tool_data:
        return ""
    parts = []
    for item in tool_data:
        tool_name = item["tool"]
        args = item.get("args", {})
        result = item.get("result", "")
        is_mcp = item.get("is_mcp", False)

        # 截断过长的结果
        max_result_len = 4000
        if len(result) > max_result_len:
            result = result[:max_result_len] + "\n\n...(结果已截断)"

        if tool_name == "search_documnet":
            filters = args.get("filters", {})
            filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items())
            parts.append(f"### 文档搜索: {filter_desc}\n{result}")
        elif tool_name == "read_document":
            doc_id = args.get("document_id", "unknown")
            parts.append(f"### 读取文档 (ID: {doc_id})\n{result}")
        elif tool_name == "load_skill_context":
            skill_name = args.get("skill_name", "unknown")
            parts.append(f"### 技能上下文: {skill_name}\n{result}")
        elif is_mcp or tool_name.startswith("mcp_"):
            # MCP 工具调用 - 提取关键信息
            tool_display_name = args.get("_display_name", tool_name)
            input_summary = _summarize_mcp_input(args, tool_name)
            parts.append(f"### MCP工具调用: {tool_display_name}\n输入: {input_summary}\n\n返回结果:\n{result}")
        else:
            # 其他工具
            parts.append(f"### 工具调用: {tool_name}\n参数: {args}\n\n结果:\n{result}")

    result_text = "\n\n".join(parts)
    if len(result_text) > 8000:
        result_text = result_text[:8000] + "\n\n...(已截断)"
    return result_text


def _summarize_mcp_input(args: dict, tool_name: str) -> str:
    """生成 MCP 工具输入参数的摘要描述。"""
    if not args:
        return "无参数"

    # 过滤内部字段
    public_args = {k: v for k, v in args.items() if not k.startswith("_")}

    if not public_args:
        return "无参数"

    # 尝试提取关键参数
    key_params = []
    for key in ["location", "city", "query", "keyword", "date", "time", "type", "name"]:
        if key in public_args:
            key_params.append(f"{key}={public_args[key]}")

    if key_params:
        return ", ".join(key_params)

    # 如果没有关键参数，列出所有参数（限制数量）
    param_list = list(public_args.items())[:5]
    return ", ".join(f"{k}={v}" for k, v in param_list if isinstance(v, (str, int, float, bool)))


# region Graph Nodes


def _build_multi_agent_graph(llm, model_name: str, mcp_tools: list = None):
    """Build multi-agent LangGraph workflow."""
    if mcp_tools is None:
        mcp_tools = []
    from langgraph.config import get_stream_writer

    graph = StateGraph(MultiAgentState)

    def planner_node(state: MultiAgentState) -> dict:
        chat_id = _current_chat_id.get(None)
        if is_stop_requested(chat_id):
            print(f"[MultiAgent] Planner 收到停止信号，终止 (session={chat_id})")
            return {}

        writer = get_stream_writer()
        writer({"type": "status", "content": "🧠 开始分析任务"})
        print("[MultiAgent] Planner 开始规划")

        task = state.user_message
        if state.document_range:
            # 构建文档范围描述
            range_lines = []
            for r in state.document_range:
                doc_name = r.get("docName", "")
                start = r.get("startParaIndex", 0)
                end = r.get("endParaIndex", -1)
                range_str = f"「{doc_name}」paragraphs {start} to {end}"
                range_lines.append(range_str)
            task += f"\n\nUser has selected the following document content:\n" + "\n".join(
                f"  - {line}" for line in range_lines
            )

        if state.document_meta:
            # 使用 JSON 格式输出元信息（紧凑模式，不换行）
            meta_json = json.dumps(
                state.document_meta if isinstance(state.document_meta, list) else [state.document_meta],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            task += f"\n\n[Document Global Metadata]\nThe following fields come from frontend document state and are not body content.\n{meta_json}\nUse these metadata fields in task analysis. The first document in the array is the active document the user is currently viewing."

        if state.attached_files:
            from app.api.routes.files import read_text_file

            for f in state.attached_files:
                filename = f.get("filename", "")
                is_image = f.get("is_image", False)
                if is_image:
                    task += f"\n\n[Attached image: {filename}]"
                else:
                    text = read_text_file(f.get("file_id", ""), filename)
                    if text:
                        task += f"\n\n--- Attachment: {filename} ---\n{text}"

        context = state.memory_context if state.memory_context else ""

        text, structured, _ = _run_sub_agent(llm, "planner", task, AGENT_TOOLS["planner"], context=context)

        workflow = {}
        if structured and "steps" in structured:
            workflow = structured
            step_count = len(workflow.get("steps", []))
            writer(
                {"type": "status", "content": f"Workflow planned: {step_count} steps - {workflow.get('summary', '')}"}
            )
        else:
            print("[MultiAgent] Planner did not create workflow, direct text output")

        return {"workflow": workflow, "messages": [{"role": "planner", "content": text}]}

    def execute_workflow_node(state: MultiAgentState) -> dict:
        chat_id = _current_chat_id.get(None)
        if is_stop_requested(chat_id):
            print(f"[MultiAgent] ⛔ 工作流收到停止信号，终止 (session={chat_id})")
            return {}

        writer = get_stream_writer()
        workflow = state.workflow

        if not workflow or not workflow.get("steps"):
            return {}

        steps = workflow["steps"]
        step_results: list[str] = []
        research_data = ""
        outline = ""
        document_json = {}
        review_result = {}
        shared_doc_data: list[dict] = []

        for i, step in enumerate(steps):
            if is_stop_requested(chat_id):
                print(f"[MultiAgent] ⛔ 用户停止，结束后续步骤 (session={chat_id})")
                break

            agent_name = step["agent"]
            task = step["task"]
            base_tools = AGENT_TOOLS.get(agent_name, [])

            # For research agent, add MCP tools dynamically
            if agent_name == "research":
                tools = list(base_tools) + list(mcp_tools)
            else:
                tools = base_tools

            agent_cn = {
                "planner": "规划",
                "research": "研究",
                "outline": "大纲",
                "writer": "写作",
                "reviewer": "审核",
            }.get(agent_name, agent_name)
            writer({"type": "__phase", "agent": agent_name})
            writer({"type": "status", "content": f"⚙️ 步骤 {i + 1}/{len(steps)}: {agent_cn} 开始执行"})
            print(f"[MultiAgent] 步骤 {i + 1}: {agent_name} - {task[:50]}")

            context_parts = []

            # 添加共享的长期记忆上下文给所有 Agent
            if state.memory_context:
                context_parts.append(f"[长期记忆]\n{state.memory_context}")

            # 添加文档元信息给所有 Agent（让他们知道有哪些文档可用）
            if state.document_meta:
                meta_json = json.dumps(
                    state.document_meta if isinstance(state.document_meta, list) else [state.document_meta],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                context_parts.append(f"[Document Metadata]\nThe following documents are available:\n{meta_json}")

            for dep_idx in step.get("depends_on", []):
                if 0 <= dep_idx < len(step_results):
                    context_parts.append(step_results[dep_idx])
            if agent_name in ("outline", "writer") and research_data:
                context_parts.append(f"[研究资料]\n{research_data}")
            if agent_name == "writer" and outline:
                context_parts.append(f"[写作大纲]\n{outline}")
            if agent_name in ("outline", "writer") and shared_doc_data:
                formatted = _format_shared_tool_data(shared_doc_data)
                if formatted:
                    context_parts.append(f"[前序步骤获取的文档数据]\n{formatted}")

            context = "\n\n---\n\n".join(context_parts)

            text, structured, tool_data = _run_sub_agent(llm, agent_name, task, tools, context=context)

            if tool_data:
                shared_doc_data.extend(tool_data)

            step_results.append(text)

            if agent_name == "research":
                research_data += ("\n\n" + text) if research_data else text
            elif agent_name == "outline":
                outline = text
            elif agent_name == "writer":
                # generate_document 工具已经通过 stream_writer 发送了 {"type": "json", ...} 事件
                # 这里不需要重复发送，只需要记录结果
                if structured and "paragraphs" in structured:
                    document_json = structured
            elif agent_name == "reviewer":
                if structured and "score" in structured:
                    review_result = structured
                    score = structured.get("score", 0)
                    summary = structured.get("feedback", "")[:100]
                    writer({"type": "status", "content": f"📝 审核评分: {score}/10 - {summary}"})
                else:
                    writer({"type": "status", "content": "✅ 审核完成"})

        return {
            "research_data": research_data,
            "outline": outline,
            "document_json": document_json,
            "review_result": review_result,
        }

    def route_after_planner(state: MultiAgentState) -> str:
        if state.workflow and state.workflow.get("steps"):
            return "execute_workflow"
        return END

    graph.add_node("planner", planner_node)
    graph.add_node("execute_workflow", execute_workflow_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {"execute_workflow": "execute_workflow", END: END},
    )
    graph.add_edge("execute_workflow", END)

    return graph.compile()


# region Main Entry


async def process_writing_request_stream(
    message: str,
    document_range: list[dict] | None = None,
    document_meta: list | dict | None = None,  # 支持单个文档（dict）和多个文档（list）
    history: list | None = None,
    model: str | None = None,
    provider: str | None = None,
    mode: str | None = None,
    chat_id: str | None = None,
    attached_files: list[dict] | None = None,
    enable_thinking: bool = True,
) -> AsyncGenerator[str, None]:
    """Multi-agent streaming handler (compatible with single agent interface)."""
    print("[MultiAgent] Starting request")
    print(f"[MultiAgent] Deep thinking: {enable_thinking}")

    model_name = resolve_model(model or "auto", provider or "")
    llm = _create_llm(model_name)

    # Load MCP tools dynamically for multi-agent (research agent uses MCP tools)
    # MUST load BEFORE building the graph so the closure captures mcp_tools
    mcp_tools, mcp_clients, mcp_failed_servers = await load_mcp_tools()
    if mcp_failed_servers:
        for failed in mcp_failed_servers:
            server_name = str(failed.get("name") or "未命名服务器")
            error_text = str(failed.get("error") or "未知错误")
            if len(error_text) > 300:
                error_text = error_text[:300] + "..."
            yield f"data: {json.dumps({'type': 'status', 'content': f'⚠️ MCP 服务器 {server_name} 加载失败: {error_text}'}, ensure_ascii=False)}\n\n"
    if mcp_tools:
        print(f"[MultiAgent] MCP tools loaded: {[t.name for t in mcp_tools]}")
        # Build and cache MCP tools prompt for research agent
        mcp_prompt = build_mcp_tools_prompt(mcp_tools)
        from app.services.multi_agent.prompts import update_mcp_tools_prompt

        update_mcp_tools_prompt(mcp_prompt)

    # Build and cache skills prompt for research agent
    skills_prompt = build_skills_prompt()
    if skills_prompt:
        from app.services.multi_agent.prompts import update_skills_prompt

        update_skills_prompt(skills_prompt)

    # Build graph AFTER mcp_tools is loaded
    app = _build_multi_agent_graph(llm, model_name, mcp_tools)

    try:
        loop = asyncio.get_running_loop()
        if chat_id:
            register_loop(chat_id, loop)

        memory_context = ""

        from app.services.memory import build_long_term_memory_prompt

        long_term_prompt = build_long_term_memory_prompt()
        if long_term_prompt:
            memory_context += long_term_prompt + "\n\n"
            print("[MultiAgent] Loaded long-term memory")

        if history:
            from app.services.memory import build_short_term_messages

            short_term_msgs = build_short_term_messages(history)
            if short_term_msgs:
                parts = []
                for m in short_term_msgs:
                    if isinstance(m, SystemMessage):
                        parts.append(m.content)
                    elif isinstance(m, HumanMessage):
                        parts.append(f"[User] {m.content}")
                    elif isinstance(m, AIMessage):
                        parts.append(f"[Assistant] {m.content}")
                if parts:
                    memory_context += "## Recent Conversation\n" + "\n\n".join(parts) + "\n\n"
                    print(f"[MultiAgent] Built short-term memory: {len(parts)} messages")

        initial_state = MultiAgentState(
            user_message=message,
            document_range=document_range or [],
            document_meta=document_meta or {},
            memory_context=memory_context,
            attached_files=attached_files or [],
        )

        queue: asyncio.Queue = asyncio.Queue()
        _SUPPRESS_STREAM = {"writer"}
        current_agent = "planner"
        _collected_text_parts: list[str] = []
        _last_input_tokens = 0
        _conversation_history: list = []

        langsmith_config = None
        if _langsmith_enabled:
            try:
                run_name = f"multi_agent:{model_name}"
                langsmith_config = {
                    "run_name": run_name,
                    "tags": ["multi_agent", model_name, mode or "plan"],
                    "metadata": {
                        "model": model_name,
                        "mode": mode or "plan",
                        "has_document_range": bool(document_range),
                        "has_document_meta": bool(document_meta),
                        "chat_id": chat_id or "",
                    },
                }
            except Exception:
                langsmith_config = None

        def run_stream():
            try:
                if chat_id:
                    _current_chat_id.set(chat_id)
                _current_model_name.set(model_name)

                stream_kwargs = {
                    "input": initial_state.model_dump(),
                    "stream_mode": ["messages", "custom"],
                }
                if langsmith_config:
                    stream_kwargs["config"] = langsmith_config

                max_attempts = 2
                for attempt in range(1, max_attempts + 1):
                    has_any_stream_item = False
                    try:
                        response = app.stream(**stream_kwargs)
                        for stream_item in response:
                            if chat_id and is_stop_requested(chat_id):
                                print(f"[MultiAgent] Stop requested, ending stream (session={chat_id})")
                                break
                            asyncio.run_coroutine_threadsafe(queue.put(stream_item), loop)
                        asyncio.run_coroutine_threadsafe(queue.put(None), loop)
                        return
                    except Exception as e:
                        if _is_context_overflow_error(e):
                            print(f"[MultiAgent] Context overflow, triggering heavy compaction")
                            asyncio.run_coroutine_threadsafe(queue.put(("context_overflow", str(e))), loop)
                            raise
                        if attempt < max_attempts and (not has_any_stream_item) and _is_transient_stream_error(e):
                            print(f"[MultiAgent] Streaming error ({attempt}): {e}, retrying")
                            time.sleep(0.5)
                            continue
                        raise
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(("error", str(e))), loop)

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(run_stream)

        while True:
            stream_item = await queue.get()

            if stream_item is None:
                break

            if isinstance(stream_item, tuple) and stream_item[0] == "error":
                raise Exception(stream_item[1])

            if isinstance(stream_item, tuple) and stream_item[0] == "context_overflow":
                print(f"[MultiAgent] Context overflow, triggering passive heavy compaction")
                from app.services.context import (
                    compress_conversation_history_if_needed,
                    _estimate_messages_tokens,
                    MAX_CONTEXT_TOKENS,
                )

                current_tokens = _estimate_messages_tokens(_conversation_history)
                compressed, meta = compress_conversation_history_if_needed(
                    _conversation_history,
                    llm=llm,
                    query=message,
                    history=history,
                    compact_level="heavy",
                    current_input_tokens=_last_input_tokens,
                )
                heavy_meta = meta.get("heavy_compact", {})
                if heavy_meta.get("heavy_compact_triggered"):
                    before = heavy_meta.get("before_tokens", current_tokens)
                    after = heavy_meta.get("after_tokens", 0)
                    print(f"[MultiAgent] Heavy compaction done: {before} -> {after} tokens")
                    updated_history = []
                    for m in compressed:
                        role = {"HumanMessage": "user", "AIMessage": "assistant", "SystemMessage": "system"}.get(
                            type(m).__name__, "assistant"
                        )
                        content_val = getattr(m, "content", "")
                        if hasattr(content_val, "__iter__") and not isinstance(content_val, str):
                            text_content = "".join(
                                part.get("text", "")
                                if isinstance(part, dict)
                                else (part if isinstance(part, str) else "")
                                for part in content_val
                            )
                            content_val = text_content
                        if isinstance(m, (HumanMessage, AIMessage, SystemMessage)):
                            updated_history.append({"role": role, "content": str(content_val)})
                    raise ContextOverflowError("Context overflow, heavy compaction triggered", updated_history)
                else:
                    print("[MultiAgent] Heavy compaction failed")
                    raise Exception("Context overflow but heavy compaction failed")

            if not isinstance(stream_item, tuple):
                continue

            input_type, chunk = stream_item

            if input_type == "messages":
                if not chunk or len(chunk) == 0:
                    continue
                msg = chunk[0]

                if isinstance(msg, AIMessage):
                    _conversation_history.append(msg)
                    usage = getattr(msg, "usage_metadata", None)
                    if isinstance(usage, dict) and "input_tokens" in usage and usage.get("input_tokens", 0) > 0:
                        _last_input_tokens = int(usage.get("input_tokens", 0))
                elif isinstance(msg, AIMessageChunk):
                    from app.services.agent.agent import _extract_text_content

                    normalized = _extract_text_content(msg.content)
                    if normalized:
                        _collected_text_parts.append(normalized)
                    usage = getattr(msg, "usage_metadata", None)
                    if isinstance(usage, dict) and "input_tokens" in usage and usage.get("input_tokens", 0) > 0:
                        _last_input_tokens = int(usage.get("input_tokens", 0))
                        from app.services.context import MAX_CONTEXT_TOKENS

                        yield f"data: {json.dumps({'type': 'token_stats', 'current_tokens': _last_input_tokens, 'max_tokens': MAX_CONTEXT_TOKENS}, ensure_ascii=False)}\n\n"

                if isinstance(msg, (AIMessage, ToolMessage)):
                    try:
                        from app.services.context import MAX_CONTEXT_TOKENS

                        current_tokens = (
                            _last_input_tokens
                            if _last_input_tokens > 0
                            else _estimate_messages_tokens(_conversation_history)
                        )
                        tokens_k = current_tokens / 1000
                        max_tokens_k = MAX_CONTEXT_TOKENS / 1000
                        # print(f"[MultiAgent] Context: {tokens_k:.1f}k tokens")
                        yield f"data: {json.dumps({'type': 'token_stats', 'current_tokens': current_tokens, 'max_tokens': MAX_CONTEXT_TOKENS}, ensure_ascii=False)}\n\n"
                    except Exception:
                        pass

                if enable_thinking and isinstance(msg, AIMessageChunk):
                    reasoning_content = getattr(msg, "additional_kwargs", {}).get("reasoning_content")
                    if reasoning_content:
                        yield f"data: {json.dumps({'type': 'thinking', 'content': reasoning_content}, ensure_ascii=False)}\n\n"

                if isinstance(msg, AIMessageChunk) and msg.content and current_agent not in _SUPPRESS_STREAM:
                    from app.services.agent.agent import _extract_text_content

                    normalized = _extract_text_content(msg.content)
                    if normalized:
                        yield f"data: {json.dumps({'type': 'text', 'content': normalized}, ensure_ascii=False)}\n\n"

            elif input_type == "custom" and chunk:
                if isinstance(chunk, dict):
                    if chunk.get("type") == "__phase":
                        current_agent = chunk.get("agent", "")
                        continue
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'status', 'content': str(chunk)}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[MultiAgent Error] {e}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'Error: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
