import unittest
from unittest.mock import patch

from app.services.tools.document_tools import _insert_break_impl, build_insert_break


class InsertBreakToolTests(unittest.TestCase):
    def test_emits_normalized_break_event_for_each_type(self):
        for break_type in ("wdLineBreak", "wdPageBreak", "wdSectionBreakNextPage"):
            events = []
            with patch("app.services.tools.document_tools.get_stream_writer", return_value=events.append):
                result = _insert_break_impl("+42", break_type)

            self.assertIn(break_type, result)
            self.assertEqual(len(events), 1)
            self.assertEqual(
                {key: events[0][key] for key in ("type", "paraID", "breakType")},
                {"type": "insert_break", "paraID": 42, "breakType": break_type},
            )

    def test_rejects_invalid_arguments(self):
        with self.assertRaises(ValueError):
            _insert_break_impl("not-an-id", "wdLineBreak")
        with self.assertRaises(ValueError):
            _insert_break_impl(1, "page")

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
