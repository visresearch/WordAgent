import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage

from app.services import middleware as middleware_module
from app.services.agent.prompts import get_compaction_summary_prompt, get_summarization_middleware_prompt
from app.services.middleware import NotifyingSummarizationMiddleware


def test_compaction_prompt_contains_required_durable_state_fields() -> None:
    prompt = get_compaction_summary_prompt()
    required_fields = (
        "### User Goal",
        "### Constraints",
        "### Confirmed Decisions",
        "### Verified Facts",
        "### Completed Actions",
        "### Unresolved Issues",
        "### Next Action",
        "### Required Identifiers",
    )

    for field in required_fields:
        assert field in prompt

    assert "Do not include hidden reasoning" in prompt
    assert "never exceed 4,000 tokens" in prompt


def test_middleware_prompt_uses_official_messages_placeholder() -> None:
    prompt = get_summarization_middleware_prompt()

    assert "{messages}" in prompt
    assert "{history_text}" not in prompt
    assert "{current_task}" not in prompt
    assert "## Durable Task State" in prompt


def _notifying_middleware() -> NotifyingSummarizationMiddleware:
    model = FakeMessagesListChatModel(responses=[AIMessage(content="压缩摘要")])
    return NotifyingSummarizationMiddleware(
        model=model,
        trigger=("tokens", 100),
        keep=("tokens", 10),
        system_prompt="S" * 400,
        max_context_tokens=200,
    )


def test_full_context_overhead_triggers_summary_and_reports_new_tokens(monkeypatch) -> None:
    events: list[dict] = []
    monkeypatch.setattr(middleware_module, "get_stream_writer", lambda: events.append)
    middleware = _notifying_middleware()
    messages = [HumanMessage(content="A" * 80), AIMessage(content="B" * 80)]

    update = middleware.before_model({"messages": messages}, None)

    assert update is not None
    assert [event["status"] for event in events] == ["started", "completed"]
    assert events[-1]["current_tokens"] > 0
    assert events[-1]["max_tokens"] == 200


def test_failed_summary_never_reports_completed(monkeypatch) -> None:
    events: list[dict] = []
    monkeypatch.setattr(middleware_module, "get_stream_writer", lambda: events.append)
    middleware = _notifying_middleware()

    def fail_summary(_messages):
        raise RuntimeError("summary provider failed")

    monkeypatch.setattr(middleware, "_create_summary", fail_summary)
    messages = [HumanMessage(content="A" * 80), AIMessage(content="B" * 80)]

    with pytest.raises(RuntimeError, match="summary provider failed"):
        middleware.before_model({"messages": messages}, None)

    assert [event["status"] for event in events] == ["started", "failed"]
