import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk

from app.api.routes import chat
from app.services.agent import agent as single_agent


def test_idle_watchdog_thresholds_are_valid() -> None:
    assert chat.IDLE_WARN_SECONDS > 0
    assert chat.IDLE_ABORT_SECONDS > chat.IDLE_WARN_SECONDS


class _WebSocket:
    def __init__(self, checkpointer=None, *, expose_state: bool = True):
        self.sent: list[str] = []
        if expose_state:
            self.app = SimpleNamespace(state=SimpleNamespace(checkpointer=checkpointer, memory_tasks=set()))

    async def send_text(self, payload: str) -> None:
        self.sent.append(payload)

    async def close(self, **_kwargs) -> None:
        return None


def test_single_agent_does_not_load_business_history(monkeypatch) -> None:
    received_calls: list[dict] = []

    async def fake_stream(**kwargs):
        received_calls.append(kwargs)
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(chat, "single_agent_stream", fake_stream)

    async def run() -> None:
        arguments = {
            "checkpointer": SimpleNamespace(aget_tuple=AsyncMock(return_value=None)),
            "session_id": 61,
            "chat_id": "chat-61",
            "message": "继续",
            "document_range": None,
            "document_meta": None,
            "model": "fake",
            "provider": "fake",
            "mode": "agent",
            "attached_files": [],
        }
        assert [chunk async for chunk in chat._single_agent_stream_with_state(**arguments)]

    asyncio.run(run())
    assert len(received_calls) == 1
    assert "bootstrap_messages" not in received_calls[0]


def test_single_agent_summary_tokens_not_forwarded(monkeypatch) -> None:
    class FakeGraph:
        def stream(self, **_kwargs):
            yield "custom", {"type": "context_compaction", "status": "started", "content": "压缩开始"}
            yield (
                "messages",
                (
                    AIMessageChunk(content="内部摘要，不应显示"),
                    {"langgraph_node": "NotifyingSummarizationMiddleware.before_model", "lc_source": "summarization"},
                ),
            )
            yield "custom", {"type": "context_compaction", "status": "completed", "content": "压缩完成"}
            yield (
                "messages",
                (AIMessageChunk(content="用户可见回答"), {"langgraph_node": "model"}),
            )
            yield (
                "messages",
                (AIMessage(content="用户可见回答"), {"langgraph_node": "model"}),
            )

    async def fake_load_mcp_tools():
        return [], [], []

    monkeypatch.setattr(single_agent, "resolve_model", lambda *_args, **_kwargs: "fake-model")
    monkeypatch.setattr(single_agent, "init_chat_model_with_reasoning", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(single_agent, "load_mcp_tools", fake_load_mcp_tools)
    monkeypatch.setattr(single_agent, "get_base_tools_for_mode", lambda _mode: [])
    monkeypatch.setattr(single_agent, "build_skills_prompt", lambda: "")
    monkeypatch.setattr(single_agent, "build_agent_middleware", lambda **_kwargs: [])
    monkeypatch.setattr(single_agent, "create_agent", lambda **_kwargs: FakeGraph())

    from app.services import llm_client, memory

    monkeypatch.setattr(memory, "is_long_term_memory_enabled", lambda: False)
    monkeypatch.setattr(llm_client, "get_custom_prompt", lambda: "")

    async def collect() -> list[str]:
        return [
            chunk
            async for chunk in single_agent.process_writing_request_stream(
                message="测试摘要过滤",
                model="fake-model",
            )
        ]

    output = asyncio.run(collect())
    rendered = "".join(output)
    assert "内部摘要，不应显示" not in rendered
    assert "用户可见回答" in rendered
    events = [json.loads(chunk[6:]) for chunk in output if chunk.startswith("data: {")]
    assert [event["status"] for event in events if event.get("type") == "context_compaction"] == [
        "started",
        "completed",
    ]


@pytest.mark.parametrize("memory_fails", [False, True])
def test_compaction_notifications_are_sent_and_saved(monkeypatch, memory_fails, caplog):
    websocket = _WebSocket(checkpointer=object())
    saved = []
    events = [
        {"type": "context_compaction", "status": "started", "content": "压缩开始"},
        {"type": "context_compaction", "status": "completed", "content": "压缩完成"},
        {"type": "text", "content": "继续回答"},
    ]

    async def stream(**_kwargs):
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    async def persist(**kwargs):
        saved.append(kwargs)

    async def record_usage(**_kwargs):
        return None

    monkeypatch.setattr(chat, "_single_agent_stream_with_state", stream)
    monkeypatch.setattr(chat, "_persist_chat_turn", persist)
    monkeypatch.setattr(chat, "record_token_usage", record_usage)

    def extract_memory(*_args):
        if memory_fails:
            raise RuntimeError("memory service unavailable")

    monkeypatch.setattr(chat, "_extract_long_term_memory_sync", extract_memory)

    async def run():
        await chat._run_ws_stream(
            websocket=websocket,
            chat_id="test-compaction",
            session_id="test-session",
            message="继续",
            mode="agent",
            model="fake",
            provider="fake",
            document_range=None,
            document_meta=None,
        )
        await asyncio.gather(*websocket.app.state.memory_tasks, return_exceptions=True)
        await asyncio.sleep(0)
        assert not websocket.app.state.memory_tasks

    asyncio.run(run())
    assert [json.loads(payload) for payload in websocket.sent] == [*events, {"type": "done"}]
    assert len(saved) == 1
    if memory_fails:
        assert "memory service unavailable" in caplog.text
    assert saved[0]["content_parts"] == [
        {"type": "status", "content": "压缩完成", "contextCompaction": True, "loading": False},
        {"type": "text", "content": "继续回答"},
    ]


@pytest.mark.parametrize("pending", [False, True])
def test_lifespan_finishes_memory_tasks_before_closing_storage(monkeypatch, pending):
    from app import main

    events = []
    app = SimpleNamespace(state=SimpleNamespace())
    original_wait = asyncio.wait

    @asynccontextmanager
    async def checkpointer():
        try:
            yield object()
        finally:
            events.append("checkpoint-closed")

    @asynccontextmanager
    async def mcp_session():
        yield

    async def close_db():
        events.append("database-closed")

    async def wait_for_tasks(tasks, *, timeout):
        assert timeout == 10.0
        return await original_wait(tasks, timeout=0 if pending else timeout)

    monkeypatch.setattr(main, "sync_builtin_skills", lambda: {"copied": 0, "skipped": 0, "invalid": 0})
    monkeypatch.setattr(main, "init_db", AsyncMock())
    monkeypatch.setattr(main, "close_db", close_db)
    monkeypatch.setattr(main, "open_checkpointer", checkpointer)
    monkeypatch.setattr(main.mcp_server.mcp.session_manager, "run", mcp_session)
    monkeypatch.setattr(main.mcp_runtime, "set_ready", Mock())
    monkeypatch.setattr(main.asyncio, "wait", wait_for_tasks)

    async def memory():
        try:
            if pending:
                await asyncio.Event().wait()
            else:
                await asyncio.sleep(0)
        finally:
            events.append("memory-finished")

    async def run():
        async with main.lifespan(app):
            task = asyncio.create_task(memory())
            app.state.memory_tasks.add(task)
            task.add_done_callback(app.state.memory_tasks.discard)
        assert task.done()
        assert task.cancelled() is pending
        assert not app.state.memory_tasks

    asyncio.run(run())
    assert events == ["memory-finished", "checkpoint-closed", "database-closed"]
    assert [call.args[0] for call in main.mcp_runtime.set_ready.call_args_list] == [True, False]


def test_single_agent_large_image_is_not_saved_in_checkpoint_input(monkeypatch) -> None:
    captured_inputs: list[dict] = []

    class FakeGraph:
        def stream(self, **kwargs):
            captured_inputs.append(kwargs["input"])
            yield "messages", (AIMessage(content="已收到图片路径"), {"langgraph_node": "model"})

    async def fake_load_mcp_tools():
        return [], [], []

    def fail_if_base64_is_read(_file_id):
        raise AssertionError("大图片不应读取为 Base64")

    monkeypatch.setattr(single_agent, "resolve_model", lambda *_args, **_kwargs: "fake-model")
    monkeypatch.setattr(single_agent, "init_chat_model_with_reasoning", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(single_agent, "load_mcp_tools", fake_load_mcp_tools)
    monkeypatch.setattr(single_agent, "get_base_tools_for_mode", lambda _mode: [])
    monkeypatch.setattr(single_agent, "build_skills_prompt", lambda: "")
    monkeypatch.setattr(single_agent, "build_agent_middleware", lambda **_kwargs: [])
    monkeypatch.setattr(single_agent, "create_agent", lambda **_kwargs: FakeGraph())

    from app.api.routes import files
    from app.services import llm_client, memory

    monkeypatch.setattr(files, "read_file_as_base64", fail_if_base64_is_read)
    monkeypatch.setattr(memory, "is_long_term_memory_enabled", lambda: False)
    monkeypatch.setattr(llm_client, "get_custom_prompt", lambda: "")

    async def collect() -> None:
        async for _chunk in single_agent.process_writing_request_stream(
            message="分析图片",
            model="fake-model",
            attached_files=[
                {
                    "file_id": "large-image",
                    "filename": "large.png",
                    "content_type": "image/png",
                    "is_image": True,
                    "size": single_agent.MAX_CHECKPOINT_IMAGE_BYTES + 1,
                    "project_path": "uploads/large-image",
                }
            ],
        ):
            pass

    asyncio.run(collect())
    human_message = captured_inputs[0]["messages"][-1]
    assert isinstance(human_message.content, str)
    assert "uploads/large-image" in human_message.content
    assert "data:image/png;base64" not in human_message.content
