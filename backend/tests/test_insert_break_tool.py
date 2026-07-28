import unittest
from unittest.mock import patch

from app.services.tools.document_tools import _insert_break_impl, build_insert_break


class InsertBreakToolTests(unittest.TestCase):
    def test_emits_normalized_break_event_for_each_type(self):
        for break_type in ("wdLineBreak", "wdPageBreak", "wdSectionBreakNextPage"):
            events = []
            with patch("app.services.tools.document_tools.get_stream_writer", return_value=events.append):
                result = _insert_break_impl("+42", break_type)

            self.assertEqual(result["breakType"], break_type)
            self.assertIsNone(result["success"])
            self.assertEqual(len(events), 1)
            self.assertEqual(
                {key: events[0][key] for key in ("type", "paraID", "breakType")},
                {"type": "insert_break", "paraID": 42, "breakType": break_type},
            )
            self.assertTrue(events[0]["requestId"])

    def test_rejects_invalid_arguments(self):
        with self.assertRaises(ValueError):
            _insert_break_impl("not-an-id", "wdLineBreak")
        with self.assertRaises(ValueError):
            _insert_break_impl(1, "page")

    def test_returns_frontend_paragraph_after_break(self):
        frontend_response = {
            "type": "insert_break_response",
            "success": True,
            "paragraphAfterBreak": {
                "paraID": 99,
                "paraIndex": 4,
                "pageStart": 5,
                "pageEnd": 5,
            },
        }
        with (
            patch("app.services.tools.document_tools.get_stream_writer", return_value=lambda _: None),
            patch("app.services.tools.document_tools._wait_for_frontend_mutation", return_value=frontend_response),
        ):
            result = _insert_break_impl(42, "wdPageBreak")

        self.assertTrue(result["success"])
        self.assertEqual(result["newPage"], 5)
        self.assertEqual(result["paragraphAfterBreak"]["paraID"], 99)

    def test_tool_schema_exposes_only_two_parameters(self):
        tool = build_insert_break("Insert a break")
        schema = tool.args_schema.model_json_schema()

        self.assertEqual(set(schema["properties"]), {"paraID", "breakType"})
        self.assertEqual(
            schema["properties"]["breakType"]["enum"],
            ["wdLineBreak", "wdPageBreak", "wdSectionBreakNextPage"],
        )


if __name__ == "__main__":
    unittest.main()
