"""
多智能体文档处理系统 - 使用 LangGraph 编排 5 个专业 Agent

流程: Planner → Research → Outline → Writer → Reviewer (→ Writer 重写循环)
"""

import asyncio
import concurrent.futures
import json
import traceback
from collections.abc import AsyncGenerator

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
from app.services.utils import parse_tool_args_with_repair
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
    web_search,
    web_fetch,
    query_document,
)

# 所有多智能体工具的映射（含新增工具）
_ALL_TOOL_MAP = {
    **TOOL_MAP,
    "create_workflow": create_workflow,
    "review_document": review_document,
}

MAX_REWRITE = 2  # 最大重写次数


# region State


class MultiAgentState(BaseModel):
    """多智能体共享状态"""

    # 用户原始请求
    user_message: str = ""
    document_range: list[dict] = Field(default_factory=list)

    # 各阶段产出
    workflow: dict = Field(default_factory=dict)  # planner 输出的工作流
    research_data: str = ""  # research 收集的资料
    outline: str = ""  # outline 生成的大纲
    document_json: dict = Field(default_factory=dict)  # writer 输出的文档 JSON
    review_result: dict = Field(default_factory=dict)  # reviewer 审核结果

    # 控制流
    rewrite_count: int = 0
    current_step_index: int = 0  # 当前执行到第几步

    # 消息历史（每个 agent 内部 ReAct 循环传递的 messages）
    messages: list = Field(default_factory=list)


# region LLM Factory


def _create_llm(model_name: str):
    """创建 LLM 实例"""
    import os
    from app.services.llm_client import get_temperature, get_https_proxy_url, get_http_proxy_url
    from langchain_openai import ChatOpenAI

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


# region Sub-Agent ReAct runner


def _run_sub_agent(
    llm,
    agent_name: str,
    task: str,
    tools: list,
    context: str = "",
    max_iterations: int = 10,
) -> tuple[str, dict | None, list[dict]]:
    """
    运行一个 sub-agent 的 ReAct 循环（同步，在线程中运行）。

    Returns:
        (text_output, tool_result_json | None, tool_data)
        text_output: agent 最终的文字回复
        tool_result_json: 如果 agent 调用了 generate_document / create_workflow / review_document，
                          返回最后一次调用的结构化结果
        tool_data: 收集的文档相关工具调用记录（read_document / query_document）
    """
    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)
    system_prompt = get_agent_prompt(agent_name)

    messages = [
        SystemMessage(content=system_prompt),
    ]

    # 注入当前时间
    from datetime import datetime

    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    now = datetime.now()
    current_time = now.strftime("%Y年%m月%d日 %H:%M") + " " + weekdays[now.weekday()]
    messages.append(SystemMessage(content=f"当前时间: {current_time}"))

    # 组合任务指令
    user_content = task
    if context:
        user_content = f"{task}\n\n---\n以下是前序步骤的参考资料：\n{context}"
    messages.append(HumanMessage(content=user_content))

    last_structured_result = None
    text_output = ""
    _writer_generated = False  # writer 是否已成功调用 generate_document
    _tool_data: list[dict] = []  # 收集文档相关工具调用结果
    _retry_count = 0  # 无效 tool call 重试计数

    chat_id = _current_chat_id.get(None)

    def _should_stop() -> bool:
        if is_stop_requested(chat_id):
            print(f"  [{agent_name}] ⛔ 检测到停止信号，终止子Agent执行 (session={chat_id})")
            return True
        return False

    def _fmt_invalid_tool_call(tc) -> str:
        """格式化 invalid_tool_calls 诊断信息，便于终端排查。"""
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

        raw_args_str = ""
        if raw_args is not None:
            raw_args_str = str(raw_args)
            if len(raw_args_str) > 300:
                raw_args_str = raw_args_str[:300] + "...(truncated)"

        return f"name={name}, id={call_id}, error={err}, raw_args={raw_args_str}"

    def _diagnose_invalid_args(tc) -> str:
        """尝试解析 invalid tool call 的原始参数，返回可读诊断信息。"""
        raw_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", None)
        if raw_args is None:
            return "args_missing"

        # 某些模型会返回 dict；多数 invalid 情况是字符串 JSON
        if isinstance(raw_args, dict):
            return "args_is_dict_but_marked_invalid"

        if not isinstance(raw_args, str):
            return f"args_type_unexpected={type(raw_args).__name__}"

        s = raw_args.strip()
        if not s:
            return "args_empty"

        try:
            json.loads(s)
            return "json_parse_ok_but_tool_call_marked_invalid"
        except Exception as e:
            # 给出 json 解析的具体位置，帮助定位是截断还是引号问题
            msg = str(e)
            return f"json_parse_error={msg}"

    def _try_repair_and_execute_invalid_calls(invalid_calls) -> bool:
        """尝试修复 invalid_tool_calls，并直接执行可修复的调用。"""
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
                result = tool_fn.invoke(parsed_args)
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
                        "args": parsed_args,
                        "id": tool_call_id,
                        "type": "tool_call",
                    }
                )
                repaired_tool_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id, name=tool_name))
                repaired_any = True
                print(f"  [{agent_name}] ✅ 已修复并执行 invalid tool_call: {tool_name}")

                if tool_name == "query_document":
                    _tool_data.append({"tool": tool_name, "args": parsed_args, "result": content})

                if agent_name == "writer" and tool_name == "generate_document":
                    _writer_generated = True
            except Exception as e:
                print(f"  [{agent_name}] ❌ 修复后工具执行失败: {tool_name}, error={e}")

        if repaired_any:
            messages.append(AIMessage(content="", tool_calls=repaired_tool_calls))
            messages.extend(repaired_tool_messages)

        return repaired_any

    for iteration in range(max_iterations):
        if _should_stop():
            text_output = ""
            break

        response = llm_with_tools.invoke(messages)

        # 处理无效的工具调用（模型生成了不完整的 tool call JSON）
        invalid_calls = getattr(response, "invalid_tool_calls", [])
        if invalid_calls:
            finish_reason = None
            if hasattr(response, "response_metadata") and isinstance(response.response_metadata, dict):
                finish_reason = response.response_metadata.get("finish_reason")

            if not hasattr(response, "tool_calls") or not response.tool_calls:
                if _try_repair_and_execute_invalid_calls(invalid_calls):
                    print(f"  [{agent_name}] 🔧 invalid tool_calls 已自动修复，继续流程")
                    continue

                # 只有无效工具调用，没有有效的 — 跳过这条消息，提示重试
                _retry_count += 1
                invalid_names = [
                    tc.get("name", "?") if isinstance(tc, dict) else getattr(tc, "name", "?") for tc in invalid_calls
                ]
                print(f"  [{agent_name}] ⚠️ 检测到无效工具调用: {invalid_names}，重试 ({_retry_count})")
                for idx, tc in enumerate(invalid_calls, 1):
                    print(f"  [{agent_name}]    ↳ invalid#{idx}: {_fmt_invalid_tool_call(tc)}")
                    print(f"  [{agent_name}]    ↳ diagnose#{idx}: {_diagnose_invalid_args(tc)}")
                if finish_reason:
                    print(f"  [{agent_name}]    ↳ finish_reason={finish_reason}")

                if _retry_count <= 2:
                    if _should_stop():
                        text_output = ""
                        break
                    messages.append(
                        SystemMessage(
                            content="你刚才的工具调用格式不完整（JSON 被截断或参数非法）。请重新调用工具，确保 tool arguments 是完整且可解析的 JSON，字符串中的双引号必须正确转义。必须使用新版样式引用格式：pStyle/rStyle/cStyle/tStyle 只能是样式ID（如 pS_1/rS_1/cS_1/tS_1），禁止直接传样式数组；并在 styles 字典提供对应定义。"
                        )
                    )
                    continue
                else:
                    # 重试次数超限，放弃
                    text_output = response.content or ""
                    print(f"  [{agent_name}] ❌ 重试次数超限，放弃工具调用")
                    break
            else:
                # 同时有有效和无效的工具调用 — 重建干净的 AIMessage，只保留有效的
                print(f"  [{agent_name}] ⚠️ 过滤掉无效工具调用，保留有效的")
                for idx, tc in enumerate(invalid_calls, 1):
                    print(f"  [{agent_name}]    ↳ dropped_invalid#{idx}: {_fmt_invalid_tool_call(tc)}")
                    print(f"  [{agent_name}]    ↳ diagnose#{idx}: {_diagnose_invalid_args(tc)}")
                if finish_reason:
                    print(f"  [{agent_name}]    ↳ finish_reason={finish_reason}")
                response = AIMessage(
                    content=response.content,
                    tool_calls=response.tool_calls,
                )

        messages.append(response)

        if not hasattr(response, "tool_calls") or not response.tool_calls:
            # 没有 tool call，agent 给出了最终文字回复
            text_output = response.content or ""
            # writer 必须调用 generate_document，如果没调用则追加提醒重试
            if agent_name == "writer" and not _writer_generated:
                messages.append(
                    HumanMessage(
                        content="你必须调用 generate_document 工具将内容输出为文档，不要在对话中直接输出文本。请立即调用 generate_document。"
                    )
                )
                continue
            break

        # 执行工具调用
        for tc in response.tool_calls:
            if _should_stop():
                break
            tool_name = tc["name"]
            print(f"  [{agent_name}] 调用工具: {tool_name}")
            tool_fn = tool_map.get(tool_name)
            if tool_fn:
                try:
                    result = tool_fn.invoke(tc["args"])
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

                    # 收集文档搜索工具的调用结果（位置信息），供下游 agent 共享
                    # 注意：只收集 query_document（位置信息小），不收集 read_document（文档内容大）
                    if tool_name == "query_document":
                        _tool_data.append({"tool": tool_name, "args": tc["args"], "result": content})

                    # writer 调用 generate_document 完成后标记退出
                    if agent_name == "writer" and tool_name == "generate_document":
                        _writer_generated = True
                except Exception as e:
                    err = f"错误: 工具 {tool_name} 调用失败: {e}。请严格按工具 schema 重新构造参数。"
                    print(f"  [{agent_name}] ❌ {err}")
                    messages.append(ToolMessage(content=err, tool_call_id=tc["id"], name=tool_name))
            else:
                messages.append(
                    ToolMessage(
                        content=f"错误: 未知工具 {tool_name}",
                        tool_call_id=tc["id"],
                        name=tool_name,
                    )
                )

        # writer 完成 generate_document 后直接退出循环
        if _writer_generated:
            break
    else:
        # 达到最大迭代但还在调用工具 — 取最后一条 AI 回复
        for m in reversed(messages):
            if isinstance(m, AIMessage) and m.content:
                text_output = m.content
                break

    return text_output, last_structured_result, _tool_data


def _format_shared_tool_data(tool_data: list[dict]) -> str:
    """将收集的工具调用数据格式化为可共享的上下文文本（仅包含搜索定位结果）。"""
    if not tool_data:
        return ""
    parts = []
    for item in tool_data:
        tool_name = item["tool"]
        args = item["args"]
        result = item["result"]
        if tool_name == "query_document":
            filters = args.get("filters", {})
            filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items())
            parts.append(f"### 文档搜索: {filter_desc}\n{result}")
    result_text = "\n\n".join(parts)
    # 安全截断，避免上下文过大
    if len(result_text) > 8000:
        result_text = result_text[:8000] + "\n\n...(已截断)"
    return result_text


# region Graph Nodes


def _build_multi_agent_graph(llm, model_name: str):
    """
    构建多智能体 LangGraph 工作流。

    图结构:
    START → planner → execute_workflow → END

    execute_workflow 内部按 workflow.steps 顺序执行各 sub-agent。
    reviewer 如果不通过，回写 writer 再次审核（最多 MAX_REWRITE 次）。
    """
    from langgraph.config import get_stream_writer

    graph = StateGraph(MultiAgentState)

    # ---- Planner 节点 ----
    def planner_node(state: MultiAgentState) -> dict:
        chat_id = _current_chat_id.get(None)
        if is_stop_requested(chat_id):
            print(f"[MultiAgent] ⛔ planner 收到停止信号，终止 (session={chat_id})")
            return {}

        writer = get_stream_writer()
        writer({"type": "status", "content": "🧠 开始分析任务"})
        print("[MultiAgent] Planner 开始规划")

        # 构建 planner 的任务
        task = state.user_message
        if state.document_range:
            range_info = json.dumps(state.document_range, ensure_ascii=False)
            task += f"\n\n用户选中了文档范围: {range_info}"

        text, structured, _ = _run_sub_agent(llm, "planner", task, AGENT_TOOLS["planner"])

        workflow = {}
        if structured and "steps" in structured:
            workflow = structured
            step_count = len(workflow.get("steps", []))
            writer(
                {"type": "status", "content": f"📋 工作流已规划（{step_count} 个步骤）: {workflow.get('summary', '')}"}
            )
        else:
            # planner 没有调用 create_workflow — 简单问答，流式 token 会通过 messages stream 自然输出
            print("[MultiAgent] Planner 没有规划出工作流，直接输出文本结果")
            pass

        return {
            "workflow": workflow,
            "messages": [{"role": "planner", "content": text}],
        }

    # ---- 工作流执行节点 ----
    def execute_workflow_node(state: MultiAgentState) -> dict:
        chat_id = _current_chat_id.get(None)
        if is_stop_requested(chat_id):
            print(f"[MultiAgent] ⛔ 工作流收到停止信号，终止 (session={chat_id})")
            return {}

        writer = get_stream_writer()
        workflow = state.workflow

        if not workflow or not workflow.get("steps"):
            # 没有工作流，planner 的文字回复直接作为最终输出
            return {}

        steps = workflow["steps"]
        step_results: list[str] = []
        research_data = ""
        outline = ""
        document_json = {}
        review_result = {}
        rewrite_count = 0
        shared_doc_data: list[dict] = []  # 跨步骤共享的文档工具数据

        for i, step in enumerate(steps):
            if is_stop_requested(chat_id):
                print(f"[MultiAgent] ⛔ 用户停止，结束后续步骤 (session={chat_id})")
                break

            agent_name = step["agent"]
            task = step["task"]
            tools = AGENT_TOOLS.get(agent_name, [])

            # 通知消费端当前 agent 阶段（用于决定是否转发流式 token）
            writer({"type": "__phase", "agent": agent_name})
            writer(
                {
                    "type": "status",
                    "content": f"⚙️ 步骤 {i + 1}/{len(steps)}: {agent_name} 开始执行",
                }
            )
            print(f"[MultiAgent] 步骤 {i + 1}: {agent_name} - {task[:50]}")

            # 构建上下文 — 收集依赖步骤的输出
            context_parts = []
            for dep_idx in step.get("depends_on", []):
                if 0 <= dep_idx < len(step_results):
                    context_parts.append(step_results[dep_idx])
            # 始终把已有的 research_data 和 outline 传给后续 agent
            if agent_name in ("outline", "writer") and research_data:
                context_parts.insert(0, f"[研究资料]\n{research_data}")
            if agent_name == "writer" and outline:
                context_parts.insert(0, f"[写作大纲]\n{outline}")
            # 将前序步骤收集的文档数据共享给 outline / writer
            if agent_name in ("outline", "writer") and shared_doc_data:
                formatted = _format_shared_tool_data(shared_doc_data)
                if formatted:
                    context_parts.insert(0, f"[前序步骤获取的文档数据]\n{formatted}")

            context = "\n\n---\n\n".join(context_parts)

            text, structured, tool_data = _run_sub_agent(llm, agent_name, task, tools, context=context)

            # 累积文档工具数据供后续步骤使用
            if tool_data:
                shared_doc_data.extend(tool_data)

            step_results.append(text)

            # 按 agent 类型保存结果
            if agent_name == "research":
                research_data += ("\n\n" + text) if research_data else text

            elif agent_name == "outline":
                outline = text

            elif agent_name == "writer":
                if structured and "paragraphs" in structured:
                    document_json = structured
                    # 直接通过 custom stream 发送文档 JSON 给前端
                    writer({"type": "json", "content": structured})

                else:
                    writer({"type": "status", "content": "⚠️ Writer 未生成文档结构"})

            elif agent_name == "reviewer":
                if structured and "score" in structured:
                    review_result = structured
                    passed = structured.get("passed", True)
                    feedback = structured.get("feedback", "")

                    if passed:
                        # 通过，简单总结
                        summary = feedback[:100] if feedback else "文档质量合格"
                        writer({"type": "status", "content": f"✅ 审核通过: {summary}"})
                    else:
                        # 不通过，显示不足
                        rewrite_instructions = structured.get("rewrite_instructions", "")
                        summary = rewrite_instructions[:100] if rewrite_instructions else feedback[:100]
                        writer({"type": "status", "content": f"✏️ 审核发现不足: {summary}"})

                    # 不通过且未超过重写上限 → 回写 writer 再审
                    if not passed and rewrite_count < MAX_REWRITE:
                        rewrite_count += 1
                        rewrite_instructions = structured.get("rewrite_instructions", "")
                        writer(
                            {
                                "type": "status",
                                "content": f"🔄 第 {rewrite_count} 次重写",
                            }
                        )

                        rewrite_task = f"请根据以下审核意见，修改并重新生成文档：\n{rewrite_instructions}"
                        writer({"type": "__phase", "agent": "writer"})
                        rewrite_context_parts = []
                        if research_data:
                            rewrite_context_parts.append(f"[研究资料]\n{research_data}")
                        if outline:
                            rewrite_context_parts.append(f"[写作大纲]\n{outline}")
                        rewrite_context = "\n\n---\n\n".join(rewrite_context_parts)

                        w_text, w_structured, _ = _run_sub_agent(
                            llm,
                            "writer",
                            rewrite_task,
                            AGENT_TOOLS["writer"],
                            context=rewrite_context,
                        )
                        if w_structured and "paragraphs" in w_structured:
                            document_json = w_structured
                            writer({"type": "json", "content": w_structured})

                        # 再次审核
                        writer({"type": "__phase", "agent": "reviewer"})
                        review_task = "请审核 writer 重写后的文档质量。"
                        review_context = w_text
                        r_text, r_structured, _ = _run_sub_agent(
                            llm,
                            "reviewer",
                            review_task,
                            AGENT_TOOLS["reviewer"],
                            context=review_context,
                        )
                        if r_structured and "score" in r_structured:
                            review_result = r_structured
                            passed2 = r_structured.get("passed", True)
                            feedback2 = r_structured.get("feedback", "")
                            if passed2:
                                writer({"type": "status", "content": f"✅ 重写审核通过: {feedback2[:80]}"})
                            else:
                                writer({"type": "status", "content": f"✏️ 重写后仍有不足: {feedback2[:80]}"})
                else:
                    writer({"type": "status", "content": f"✅ 审核完成"})

        return {
            "research_data": research_data,
            "outline": outline,
            "document_json": document_json,
            "review_result": review_result,
            "rewrite_count": rewrite_count,
        }

    # ---- 路由 ----
    def route_after_planner(state: MultiAgentState) -> str:
        if state.workflow and state.workflow.get("steps"):
            return "execute_workflow"
        return END

    # ---- 构建图 ----
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


# region 主入口


async def process_writing_request_stream(
    message: str,
    document_range: list[dict] | None = None,
    history: list | None = None,
    model: str | None = None,
    mode: str | None = None,
    chat_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    多智能体流式处理写作请求（与单 agent 接口完全兼容）。

    Yields:
        SSE 格式的流式输出
    """
    print("[MultiAgent] 开始处理请求")

    model_name = resolve_model(model or "auto")
    llm = _create_llm(model_name)
    app = _build_multi_agent_graph(llm, model_name)

    try:
        # 获取事件循环，注册供 tool 使用
        loop = asyncio.get_running_loop()
        if chat_id:
            register_loop(chat_id, loop)

        initial_state = MultiAgentState(
            user_message=message,
            document_range=document_range or [],
        )

        queue: asyncio.Queue = asyncio.Queue()
        # 追踪当前 agent 阶段，决定是否转发流式 token
        # 只有 writer 的流式 token 不转发（直接 invoke 拿结果），其他 agent 全部流式输出
        _SUPPRESS_STREAM = {"writer"}
        current_agent = "planner"

        def run_stream():
            """在独立线程中运行同步的 LangGraph stream"""
            try:
                if chat_id:
                    _current_chat_id.set(chat_id)

                response = app.stream(
                    initial_state.model_dump(),
                    stream_mode=["messages", "custom"],
                )
                for stream_item in response:
                    if chat_id and is_stop_requested(chat_id):
                        print(f"[MultiAgent] ⛔ 检测到停止信号，结束流式处理 (session={chat_id})")
                        break
                    asyncio.run_coroutine_threadsafe(queue.put(stream_item), loop)
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
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

            if not isinstance(stream_item, tuple):
                continue

            input_type, chunk = stream_item

            if input_type == "messages":
                if not chunk or len(chunk) == 0:
                    continue
                msg = chunk[0]
                # 只转发非 writer agent 的 AI 文字 token
                if isinstance(msg, AIMessageChunk) and msg.content and current_agent not in _SUPPRESS_STREAM:
                    yield f"data: {json.dumps({'type': 'text', 'content': msg.content}, ensure_ascii=False)}\n\n"

            elif input_type == "custom" and chunk:
                if isinstance(chunk, dict):
                    # __phase 是内部标记，用于切换 agent 阶段，不发给前端
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
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
