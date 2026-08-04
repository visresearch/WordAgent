from app.services.agent.prompts import get_compaction_summary_prompt, get_summarization_middleware_prompt


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
