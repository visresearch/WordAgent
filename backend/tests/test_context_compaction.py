import unittest
from types import SimpleNamespace

from app.services.agent.prompts import get_compaction_summary_prompt
from app.services.context import HEAVY_COMPACT_MAX_OUTPUT, _extract_structured_summary, _format_history_for_summary


class RecordingLLM:
    def __init__(self):
        self.messages = None
        self.kwargs = None

    def invoke(self, messages, **kwargs):
        self.messages = messages
        self.kwargs = kwargs
        return SimpleNamespace(content="## Durable Task State\n\n### User Goal\nContinue the task.")


class ContextCompactionTests(unittest.TestCase):
    def test_prompt_contains_required_durable_state_fields(self):
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
            with self.subTest(field=field):
                self.assertIn(field, prompt)

        self.assertIn("Do not include hidden reasoning", prompt)
        self.assertIn("never exceed 4,000 tokens", prompt)

    def test_summary_call_uses_bounded_output_and_formatted_history(self):
        llm = RecordingLLM()
        summary = _extract_structured_summary(
            [{"role": "user", "content": "Preserve /tmp/task-state and continue."}],
            llm,
            current_task="Run the remaining verification.",
        )

        self.assertTrue(summary.startswith("## Durable Task State"))
        self.assertLessEqual(HEAVY_COMPACT_MAX_OUTPUT, 4000)
        self.assertEqual(llm.kwargs["max_tokens"], HEAVY_COMPACT_MAX_OUTPUT)
        rendered_prompt = llm.messages[0].content
        self.assertIn("Preserve /tmp/task-state and continue.", rendered_prompt)
        self.assertIn("CURRENT TASK: Run the remaining verification.", rendered_prompt)
        self.assertNotIn("{history_text}", rendered_prompt)

    def test_long_history_preserves_initial_goal_and_recent_state(self):
        history = [{"role": "user", "content": "INITIAL_GOAL"}]
        history.extend(
            {"role": "assistant", "content": f"middle-{index}: " + ("x" * 2500)}
            for index in range(30)
        )
        history.append({"role": "user", "content": "LATEST_UNRESOLVED_STATE"})

        formatted = _format_history_for_summary(history)

        self.assertIn("INITIAL_GOAL", formatted)
        self.assertIn("LATEST_UNRESOLVED_STATE", formatted)
        self.assertLessEqual(len(formatted), 41000)
        self.assertIn("[...截断，原 2510 字符]", formatted)


if __name__ == "__main__":
    unittest.main()
