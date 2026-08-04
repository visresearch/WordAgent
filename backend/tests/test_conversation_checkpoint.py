import asyncio

from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.services.memory import build_thread_config, get_thread_token_stats, single_agent_thread_lock


async def _save_messages(checkpointer, session_id: int, messages: list) -> None:
    checkpoint = empty_checkpoint()
    checkpoint["channel_values"]["messages"] = messages
    checkpoint["channel_versions"]["messages"] = "1"
    config = build_thread_config(session_id)
    config["configurable"]["checkpoint_ns"] = ""
    await checkpointer.aput(
        config,
        checkpoint,
        {"source": "input", "step": 0, "parents": {}},
        {"messages": "1"},
    )


async def _load_messages(checkpointer, session_id: int) -> list:
    saved = await checkpointer.aget_tuple(build_thread_config(session_id))
    if saved is None:
        return []
    return saved.checkpoint["channel_values"]["messages"]


def test_single_agent_same_session_restores_memory(tmp_path) -> None:
    async def run() -> None:
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "checkpoint.db")) as checkpointer:
            await _save_messages(
                checkpointer,
                11,
                [HumanMessage(content="第一轮问题"), AIMessage(content="第一轮回答")],
            )
            restored = await _load_messages(checkpointer, 11)

        assert [message.content for message in restored] == ["第一轮问题", "第一轮回答"]

    asyncio.run(run())


def test_single_agent_different_sessions_are_isolated(tmp_path) -> None:
    async def run() -> None:
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "checkpoint.db")) as checkpointer:
            await _save_messages(checkpointer, 21, [HumanMessage(content="仅属于会话 21")])
            assert [message.content for message in await _load_messages(checkpointer, 21)] == ["仅属于会话 21"]
            assert await _load_messages(checkpointer, 22) == []

    asyncio.run(run())


def test_single_agent_restart_restores_memory(tmp_path) -> None:
    async def run() -> None:
        database = tmp_path / "checkpoint.db"
        async with AsyncSqliteSaver.from_conn_string(str(database)) as checkpointer:
            await _save_messages(checkpointer, 31, [HumanMessage(content="重启后仍需保留")])

        async with AsyncSqliteSaver.from_conn_string(str(database)) as reopened:
            restored = await _load_messages(reopened, 31)

        assert [message.content for message in restored] == ["重启后仍需保留"]

    asyncio.run(run())


def test_single_agent_tool_calls_are_restored(tmp_path) -> None:
    async def run() -> None:
        tool_call = {
            "name": "read_document",
            "args": {"doc_id": 7},
            "id": "call-7",
            "type": "tool_call",
        }
        messages = [
            HumanMessage(content="读取文档"),
            AIMessage(content="", tool_calls=[tool_call]),
            ToolMessage(content="文档内容", name="read_document", tool_call_id="call-7"),
        ]
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "checkpoint.db")) as checkpointer:
            await _save_messages(checkpointer, 41, messages)
            restored = await _load_messages(checkpointer, 41)

        assert restored[1].tool_calls == [tool_call]
        assert isinstance(restored[2], ToolMessage)
        assert restored[2].content == "文档内容"

    asyncio.run(run())


def test_single_agent_token_stats_are_restored_from_checkpoint(tmp_path) -> None:
    async def run() -> None:
        messages = [
            HumanMessage(content="问题"),
            AIMessage(
                content="回答",
                usage_metadata={
                    "input_tokens": 41848,
                    "output_tokens": 431,
                    "total_tokens": 42279,
                },
            ),
        ]
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "checkpoint.db")) as checkpointer:
            await _save_messages(checkpointer, 45, messages)
            stats = await get_thread_token_stats(checkpointer, 45, 50000)

        assert stats == {"current": 41848, "max": 50000, "percentage": 83.7}

    asyncio.run(run())


def test_single_agent_summarization_preserves_recent_messages() -> None:
    model = FakeMessagesListChatModel(responses=[AIMessage(content="较早对话摘要")])
    middleware = SummarizationMiddleware(
        model=model,
        trigger=("messages", 4),
        keep=("messages", 2),
    )
    messages = [
        HumanMessage(content="旧问题"),
        AIMessage(content="旧回答"),
        HumanMessage(content="较新问题"),
        AIMessage(content="较新回答"),
        HumanMessage(content="最新问题"),
    ]

    update = middleware.before_model({"messages": messages}, None)
    contents = [message.content for message in update["messages"]]

    assert any("较早对话摘要" in content for content in contents)
    assert contents[-2:] == ["较新回答", "最新问题"]


def test_single_agent_same_thread_is_not_run_concurrently() -> None:
    async def run() -> None:
        active = 0
        maximum_active = 0

        async def worker() -> None:
            nonlocal active, maximum_active
            async with single_agent_thread_lock(51, "ignored-chat-id"):
                active += 1
                maximum_active = max(maximum_active, active)
                await asyncio.sleep(0.01)
                active -= 1

        await asyncio.gather(worker(), worker())
        assert maximum_active == 1

    asyncio.run(run())
