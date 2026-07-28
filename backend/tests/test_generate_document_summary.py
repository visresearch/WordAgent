import unittest
from unittest.mock import patch

from app.services.tools.document_tools import _format_generated_document_message, _generate_document_impl
from app.services.tools.schemas import DocumentOutput


class GenerateDocumentSummaryTests(unittest.TestCase):
    def test_omits_zero_paragraphs_when_tables_exist(self):
        self.assertEqual(
            _format_generated_document_message(0, 1, 0),
            "📝 文档已生成，共 1 个表格",
        )

    def test_omits_zero_tables_when_paragraphs_exist(self):
        self.assertEqual(
            _format_generated_document_message(2, 0, 0),
            "📝 文档已生成，共 2 个段落",
        )

    def test_lists_only_positive_counts(self):
        self.assertEqual(
            _format_generated_document_message(2, 1, 3),
            "📝 文档已生成，共 2 个段落，1 个表格，3 张图片",
        )

    def test_omits_count_suffix_when_everything_is_empty(self):
        self.assertEqual(
            _format_generated_document_message(0, 0, 0),
            "📝 文档已生成",
        )

    def test_returns_frontend_last_paragraph_location_to_agent(self):
        events = []
        frontend_response = {
            "type": "generate_document_response",
            "success": True,
            "lastParagraph": {
                "paraID": 2468,
                "paraIndex": 7,
                "pageStart": 2,
                "pageEnd": 3,
            },
        }
        document = DocumentOutput(paragraphs=[], tables=[], styles={})
        with (
            patch("app.services.tools.document_tools.get_stream_writer", return_value=events.append),
            patch("app.services.tools.document_tools._wait_for_frontend_mutation", return_value=frontend_response),
        ):
            result = _generate_document_impl(document, 9, 0)

        self.assertTrue(result["success"])
        self.assertEqual(
            result["lastParagraph"],
            {"paraID": 2468, "paraIndex": 7, "pageStart": 2, "pageEnd": 3},
        )
        self.assertEqual(events[0]["requestId"], events[1]["requestId"])
        self.assertEqual(events[1]["content"], "📝 文档已生成")


if __name__ == "__main__":
    unittest.main()
