import asyncio
import json
from types import SimpleNamespace

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
            self.app = SimpleNamespace(state=SimpleNamespace(checkpointer=checkpointer))

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
            "checkpointer": object(),
            "session_id": 61,
            "chat_id": "chat-61",
            "message": "继续",
            "document_range": None,
            "document_meta": None,
            "model": "fake",
            "provider": "fake",
            "mode": "agent",
            "attached_files": [],
            "enable_thinking": False,
        }
        assert [chunk async for chunk in chat._single_agent_stream_with_state(**arguments)]

    asyncio.run(run())
    assert len(received_calls) == 1
    assert "bootstrap_messages" not in received_calls[0]


def test_single_agent_summary_tokens_not_forwarded(monkeypatch) -> None:
    class FakeGraph:
        def stream(self, **_kwargs):
            yield (
                "messages",
                (
                    AIMessageChunk(content="内部摘要，不应显示"),
                    {"langgraph_node": "NotifyingSummarizationMiddleware.before_model", "lc_source": "summarization"},
                ),
            )
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
    monkeypatch.setattr(single_agent, "supports_thinking", lambda _model: False)
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
                enable_thinking=False,
            )
        ]

    output = asyncio.run(collect())
    rendered = "".join(output)
    assert "内部摘要，不应显示" not in rendered
    assert "用户可见回答" in rendered


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
    monkeypatch.setattr(single_agent, "supports_thinking", lambda _model: False)
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
            enable_thinking=False,
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
