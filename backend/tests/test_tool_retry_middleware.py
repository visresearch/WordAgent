import asyncio

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from app.services.agent import agent as single_agent
from app.services.middleware import (
    _BUILTIN_TOOL_NAMES,
    DEFAULT_AGENT_MIDDLEWARE,
    MODEL_CALL_LIMIT_MIDDLEWARE,
    TOOL_RETRY_MIDDLEWARE,
)


class _BindableFakeChatModel(FakeMessagesListChatModel):
    bound_tool_names: list[str] = []

    def bind_tools(self, tools, **kwargs):
        self.bound_tool_names = [tool.name for tool in tools]
        return self


def _tool_call(name: str, call_id: str = "call-1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": name,
                "args": {"value": 7},
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def test_tool_retry_middleware_retries_until_success(monkeypatch) -> None:
    attempts = 0

    @tool
    def flaky_tool(value: int) -> str:
        """Fail twice, then return the value."""
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("temporary failure")
        return str(value)

    monkeypatch.setattr(TOOL_RETRY_MIDDLEWARE, "initial_delay", 0)
    monkeypatch.setattr(TOOL_RETRY_MIDDLEWARE, "jitter", False)

    model = _BindableFakeChatModel(responses=[_tool_call("flaky_tool"), AIMessage(content="完成")])
    agent = create_agent(model=model, tools=[flaky_tool], middleware=DEFAULT_AGENT_MIDDLEWARE)
    output = agent.invoke({"messages": [{"role": "user", "content": "开始"}]})
    result = next(message for message in output["messages"] if getattr(message, "name", "") == "flaky_tool")

    assert attempts == 3
    assert result.content == "7"
    assert result.status == "success"


def test_tool_retry_middleware_returns_error_after_retries(monkeypatch) -> None:
    attempts = 0

    @tool
    def failing_tool(value: int) -> str:
        """Always fail."""
        nonlocal attempts
        attempts += 1
        raise TimeoutError(f"timeout for {value}")

    monkeypatch.setattr(TOOL_RETRY_MIDDLEWARE, "initial_delay", 0)
    monkeypatch.setattr(TOOL_RETRY_MIDDLEWARE, "jitter", False)

    model = _BindableFakeChatModel(responses=[_tool_call("failing_tool"), AIMessage(content="已处理失败")])
    agent = create_agent(model=model, tools=[failing_tool], middleware=DEFAULT_AGENT_MIDDLEWARE)
    output = agent.invoke({"messages": [{"role": "user", "content": "开始"}]})
    result = next(message for message in output["messages"] if getattr(message, "name", "") == "failing_tool")

    assert attempts == 3
    assert result.status == "error"
    assert "failed after 3 attempts" in result.content
    assert "TimeoutError" in result.content


def test_todo_list_middleware_adds_tool_and_state() -> None:
    assert "ask" not in _BUILTIN_TOOL_NAMES
    assert "write_todos" in _BUILTIN_TOOL_NAMES

    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "write_todos",
                "args": {"todos": [{"content": "完成重构", "status": "in_progress"}]},
                "id": "todo-1",
                "type": "tool_call",
            }
        ],
    )
    model = _BindableFakeChatModel(responses=[message, AIMessage(content="规划完成")])
    agent = create_agent(model=model, tools=[], middleware=DEFAULT_AGENT_MIDDLEWARE)
    output = agent.invoke({"messages": [{"role": "user", "content": "制定计划"}]})

    assert output["todos"] == [{"content": "完成重构", "status": "in_progress"}]
    assert any(getattr(item, "tool_call_id", "") == "todo-1" for item in output["messages"])
    assert model.bound_tool_names == ["write_todos"]


def test_model_call_limit_middleware_ends_run_and_preserves_streaming() -> None:
    @tool
    def looping_tool(value: int) -> str:
        """Return a value while the model keeps requesting tools."""
        return str(value)

    model = _BindableFakeChatModel(responses=[_tool_call("looping_tool")])
    middleware = [ModelCallLimitMiddleware(run_limit=1, exit_behavior="end")]
    agent = create_agent(model=model, tools=[looping_tool], middleware=middleware)

    stream_items = list(
        agent.stream(
            {"messages": [{"role": "user", "content": "持续调用工具"}]},
            stream_mode=["messages", "values"],
        )
    )

    streamed_messages = [chunk[0] for mode, chunk in stream_items if mode == "messages"]
    final_state = [chunk for mode, chunk in stream_items if mode == "values"][-1]

    assert MODEL_CALL_LIMIT_MIDDLEWARE.run_limit == 100
    assert any(message.content == "7" for message in streamed_messages)
    assert final_state["run_model_call_count"] == 1
    assert "Model call limit" in final_state["messages"][-1].content


def test_create_agent_preserves_retry_message_and_custom_streaming(monkeypatch) -> None:
    attempts = 0

    @tool
    def emitting_tool(value: int) -> str:
        """Emit progress and return a value."""
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionError("temporary stream tool failure")
        get_stream_writer()({"type": "tool_progress", "content": f"value={value}"})
        return str(value)

    monkeypatch.setattr(TOOL_RETRY_MIDDLEWARE, "initial_delay", 0)
    monkeypatch.setattr(TOOL_RETRY_MIDDLEWARE, "jitter", False)

    model = _BindableFakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "emitting_tool",
                        "args": {"value": 9},
                        "id": "stream-call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="流式完成"),
        ]
    )
    agent = create_agent(
        model=model,
        tools=[emitting_tool],
        system_prompt="test system prompt",
        middleware=DEFAULT_AGENT_MIDDLEWARE,
    )

    stream_items = list(
        agent.stream(
            {"messages": [{"role": "user", "content": "开始"}]},
            stream_mode=["messages", "custom"],
        )
    )

    custom_events = [chunk for mode, chunk in stream_items if mode == "custom"]
    streamed_messages = [chunk[0] for mode, chunk in stream_items if mode == "messages"]
    assert custom_events == [{"type": "tool_progress", "content": "value=9"}]
    assert attempts == 2
    assert any(message.content == "9" for message in streamed_messages)
    assert streamed_messages[-1].content == "流式完成"
    assert model.bound_tool_names == ["write_todos", "emitting_tool"]


def test_single_agent_create_agent_streams_sse_and_tool_events(monkeypatch) -> None:
    @tool
    def emitting_tool(value: int) -> str:
        """Emit progress and return a value."""
        get_stream_writer()({"type": "tool_progress", "content": f"value={value}"})
        return str(value)

    model = _BindableFakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "emitting_tool",
                        "args": {"value": 5},
                        "id": "single-stream-call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="最终流式回答"),
        ]
    )

    async def fake_load_mcp_tools():
        return [], [], []

    monkeypatch.setattr(single_agent, "resolve_model", lambda *_args, **_kwargs: "fake-model")
    monkeypatch.setattr(single_agent, "supports_thinking", lambda _model: False)
    monkeypatch.setattr(single_agent, "init_chat_model_with_reasoning", lambda *_args, **_kwargs: model)
    monkeypatch.setattr(single_agent, "load_mcp_tools", fake_load_mcp_tools)
    monkeypatch.setattr(single_agent, "get_base_tools_for_mode", lambda _mode: [emitting_tool])
    monkeypatch.setattr(single_agent, "build_skills_prompt", lambda: "")

    from app.services import llm_client, memory

    monkeypatch.setattr(memory, "is_long_term_memory_enabled", lambda: False)
    monkeypatch.setattr(memory, "build_short_term_messages", lambda _history: [])
    monkeypatch.setattr(llm_client, "get_custom_prompt", lambda: "")

    async def collect_stream() -> list[str]:
        return [
            item
            async for item in single_agent.process_writing_request_stream(
                message="执行流式测试",
                mode="agent",
                model="fake-model",
                enable_thinking=False,
            )
        ]

    output = asyncio.run(collect_stream())

    assert any('"type": "tool_progress"' in item and "value=5" in item for item in output)
    assert any('"type": "text"' in item and "最终流式回答" in item for item in output)
    assert "data: [DONE]\n\n" in output
    assert any(item.startswith("__memory_conversation__:") and "最终流式回答" in item for item in output)
    assert any(item.startswith("__tool_json__:") and "emitting_tool" in item for item in output)
