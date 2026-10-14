import asyncio
import json

import pytest
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.message import add_messages

from app.services import llm_client, memory
from app.services.agent import agent as production_agent
from app.services.agent.middleware import build_agent_middleware
from app.services.middleware.tool_history import ToolHistoryMiddleware


def assistant(*call_ids):
    return AIMessage(
        id="interrupted-assistant",
        content="",
        additional_kwargs={"reasoning_content": "Original reasoning"},
        tool_calls=[
            {"name": "edit_document", "args": {"value": index}, "id": call_id} for index, call_id in enumerate(call_ids)
        ],
    )


def assert_valid_tool_history(messages):
    pending = set()
    for message in messages:
        if isinstance(message, ToolMessage):
            assert message.tool_call_id in pending
            pending.remove(message.tool_call_id)
        else:
            assert not pending, "An assistant tool call has no contiguous result before the next message"
            if isinstance(message, AIMessage):
                pending = {call["id"] for call in message.tool_calls}
    assert not pending


def test_partial_parallel_results_preserve_successes_and_mark_only_missing_results_unconfirmed():
    original = assistant("done", "missing")
    completed = ToolMessage(id="real-result", tool_call_id="done", content='{"success":true}')
    newer = HumanMessage(id="new-turn", content="Continue")
    messages = [HumanMessage(content="Fill the table"), original, completed, newer]
    update = ToolHistoryMiddleware().before_model({"messages": messages}, None)
    repaired = add_messages(messages, update["messages"])
    assert_valid_tool_history(repaired)
    assert repaired[1] is original
    assert repaired[2] is completed
    assert repaired[-1] is newer
    missing = repaired[3]
    assert missing.tool_call_id == "missing"
    assert missing.status == "error"
    payload = json.loads(missing.content)
    assert payload["success"] is None
    assert payload["requiresRead"] is True
    assert original.additional_kwargs["reasoning_content"] == "Original reasoning"
    assert ToolHistoryMiddleware().before_model({"messages": repaired}, None) is None


def test_current_pending_calls_and_complete_history_are_unchanged():
    middleware = ToolHistoryMiddleware()
    pending = [HumanMessage(content="Ask"), assistant("pending")]
    assert middleware.before_model({"messages": pending}, None) is None
    completed = [*pending, ToolMessage(content="Done", tool_call_id="pending"), HumanMessage(content="Next")]
    assert middleware.before_model({"messages": completed}, None) is None


class ValidatingModel(FakeMessagesListChatModel):
    seen: list = []

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        assert_valid_tool_history(messages)
        self.seen.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def guarded_tool(attempts):
    @tool
    def edit_document(value: int) -> str:
        """Change a document; old interrupted calls must never be replayed."""
        attempts.append(value)
        raise AssertionError("Replayed an interrupted document mutation")

    return edit_document


@pytest.mark.parametrize("asynchronous", [False, True])
def test_real_agent_repairs_checkpoint_before_its_first_model_call_without_replaying_writes(asynchronous):
    attempts = []
    model = ValidatingModel(responses=[AIMessage(content="Continue with a valid history")])
    graph = create_agent(
        model=model,
        tools=[guarded_tool(attempts)],
        middleware=build_agent_middleware(summary_model=model),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "stopped-session"}}
    graph.update_state(
        config, {"messages": [HumanMessage(content="Old request"), assistant("old-write")]}, as_node="model"
    )
    request = {"messages": [HumanMessage(content="New request")]}
    output = asyncio.run(graph.ainvoke(request, config)) if asynchronous else graph.invoke(request, config)
    assert output["messages"][-1].content == "Continue with a valid history"
    assert attempts == []
    assert len(model.seen) == 1
    stored = graph.get_state(config).values["messages"]
    assert_valid_tool_history(stored)
    assert any(isinstance(message, ToolMessage) and message.tool_call_id == "old-write" for message in stored)


def test_sqlite_restart_keeps_existing_history_and_repairs_the_missing_result_before_continuing(tmp_path):
    async def run():
        path = str(tmp_path / "checkpoint.db")
        config = {"configurable": {"thread_id": "stopped-session"}}
        attempts = []
        model = ValidatingModel(responses=[AIMessage(content="Resumed"), AIMessage(content="Still valid")])

        def graph(saver):
            return create_agent(
                model=model,
                tools=[guarded_tool(attempts)],
                middleware=build_agent_middleware(summary_model=model),
                checkpointer=saver,
            )

        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            await graph(saver).aupdate_state(
                config,
                {
                    "messages": [
                        HumanMessage(content="Keep the original task"),
                        assistant("read-done", "write-missing"),
                        ToolMessage(content="Existing document data", tool_call_id="read-done"),
                        HumanMessage(content="The request that previously failed with 400"),
                    ]
                },
                as_node="model",
            )
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            output = await graph(saver).ainvoke({"messages": [HumanMessage(content="Retry")]}, config)
            assert output["messages"][-1].content == "Resumed"
            assert_valid_tool_history(output["messages"])
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            output = await graph(saver).ainvoke({"messages": [HumanMessage(content="Continue")]}, config)
            assert output["messages"][-1].content == "Still valid"
            assert_valid_tool_history(output["messages"])
            missing_results = [
                message
                for message in output["messages"]
                if isinstance(message, ToolMessage) and message.tool_call_id == "write-missing"
            ]
            assert len(missing_results) == 1
            assert any(message.content == "Existing document data" for message in output["messages"])
        assert attempts == []

    asyncio.run(run())


def test_production_stream_can_continue_the_same_sqlite_session_after_an_interrupted_tool(tmp_path, monkeypatch):
    attempts = []
    model = ValidatingModel(responses=[AIMessage(content="The same conversation can continue")])
    tools = [guarded_tool(attempts)]
    monkeypatch.setattr(production_agent, "resolve_model", lambda *_args: "fake-model")
    monkeypatch.setattr(production_agent, "init_chat_model_with_reasoning", lambda *_args, **_kwargs: model)
    monkeypatch.setattr(production_agent, "get_base_tools_for_mode", lambda _mode: tools)
    monkeypatch.setattr(production_agent, "build_skills_prompt", lambda: "")
    monkeypatch.setattr(llm_client, "get_custom_prompt", lambda: "")
    monkeypatch.setattr(memory, "is_long_term_memory_enabled", lambda: False)

    async def no_mcp():
        return [], [], []

    monkeypatch.setattr(production_agent, "load_mcp_tools", no_mcp)

    async def run():
        session_id = "stopped-production-session"
        config = memory.build_thread_config(session_id)
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "checkpoint.db")) as saver:
            seeded = create_agent(
                model=model,
                tools=tools,
                state_schema=production_agent.WordAgentState,
                middleware=build_agent_middleware(summary_model=model),
                checkpointer=saver,
            )
            await seeded.aupdate_state(
                config,
                {
                    "messages": [
                        HumanMessage(content="Previous request"),
                        assistant("interrupted-write"),
                        HumanMessage(content="Previous request rejected with 400"),
                    ]
                },
                as_node="model",
            )
            chunks = [
                chunk
                async for chunk in production_agent.process_writing_request_stream(
                    message="Retry this conversation",
                    model="fake-model",
                    session_id=session_id,
                    checkpointer=saver,
                )
            ]
            assert not any('"type": "error"' in chunk for chunk in chunks)
            assert "The same conversation can continue" in "".join(chunks)
            saved = await saver.aget_tuple(config)
            assert_valid_tool_history(saved.checkpoint["channel_values"]["messages"])
        assert attempts == []

    asyncio.run(run())
