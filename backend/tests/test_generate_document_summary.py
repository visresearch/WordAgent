import json
import unittest
from unittest.mock import patch

from app.services.tools.document_tools import _compact_doc_json, _format_generated_document_message, _generate_document_impl
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
        document = DocumentOutput(paragraphs=[], styles={})
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

    def test_omits_unavailable_page_fields_from_agent_result(self):
        frontend_response = {
            "type": "generate_document_response",
            "success": True,
            "lastParagraph": {
                "paraID": 2468,
                "paraIndex": 7,
                "pageStart": None,
                "pageEnd": None,
            },
        }
        document = DocumentOutput(paragraphs=[], styles={})
        with (
            patch("app.services.tools.document_tools.get_stream_writer", return_value=lambda _: None),
            patch("app.services.tools.document_tools._wait_for_frontend_mutation", return_value=frontend_response),
        ):
            result = _generate_document_impl(document, 9, 0)

        self.assertEqual(result["lastParagraph"], {"paraID": 2468, "paraIndex": 7})

    def test_formula_run_is_forwarded_without_counting_it_as_an_image(self):
        events = []
        latex = r"\sqrt{x}"
        document = DocumentOutput.model_validate({
            "paragraphs": [{"pStyle": "pS_1", "runs": [{"formula": latex}]}],
            "styles": {"pS_1": ["left", 0, 0, 0, 0, 0, 0, "", 0]},
        })
        with (
            patch("app.services.tools.document_tools.get_stream_writer", return_value=events.append),
            patch("app.services.tools.document_tools._wait_for_frontend_mutation", return_value={"success": True}),
        ):
            _generate_document_impl(document, 9, 0)

        run = events[0]["content"]["paragraphs"][0]["runs"][0]
        self.assertEqual(run["formula"], latex)
        self.assertIsNone(run["url"])
        self.assertEqual(events[-1]["content"], "📝 文档已生成，共 1 个段落")

    def test_long_read_preserves_formula_runs_in_body_and_table(self):
        body_formula = {"formula": r"\frac{a}{b}"}
        cell_formula = {"formula": "x^{2}"}
        doc = {"paragraphs": [
            {"paraID": 1, "runs": [{"text": "before"}, body_formula]},
            {"tables": [{"cells": [[{"paragraphs": [{"paraID": 2, "runs": [cell_formula]}]}]]}]},
        ]}
        with patch("app.services.tools.document_tools._MAX_DOC_JSON_CHARS", 1):
            result = json.loads(_compact_doc_json(doc))

        self.assertEqual(result["paragraphs"][0]["runs"][1], body_formula)
        cell = result["paragraphs"][1]["tables"][0]["cells"][0][0]
        self.assertEqual(cell["paragraphs"], [{"paraID": 2, "runs": [cell_formula]}])


if __name__ == "__main__":
    unittest.main()
