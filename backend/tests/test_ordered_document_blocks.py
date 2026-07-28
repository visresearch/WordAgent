import unittest

from pydantic import ValidationError

from app.services.tools.schemas import DocumentOutput, Paragraph, TableBlock


class OrderedDocumentBlockSchemaTests(unittest.TestCase):
    def setUp(self):
        self.styles = {
            "pS_1": ["left", 0, 0, 0, 0, 0, 0, "正文", 1],
            "rS_1": ["宋体", 12, False, False, 0, "#000000", "#000000", 0, False, False, False],
            "cS_1": [1, 1, "center", "center"],
            "tS_1": [1],
        }
        self.table = {
            "rows": 1,
            "columns": 1,
            "cells": [[{"text": "单元格", "rStyle": "rS_1", "cStyle": "cS_1"}]],
            "tStyle": "tS_1",
        }

    def test_preserves_table_block_between_paragraphs(self):
        document = DocumentOutput(
            paragraphs=[
                {"pStyle": "pS_1", "runs": [{"text": "表格前", "rStyle": "rS_1"}]},
                {"tables": [self.table]},
                {"pStyle": "pS_1", "runs": [{"text": "表格后", "rStyle": "rS_1"}]},
            ],
            styles=self.styles,
        )

        self.assertIsInstance(document.paragraphs[0], Paragraph)
        self.assertIsInstance(document.paragraphs[1], TableBlock)
        self.assertIsInstance(document.paragraphs[2], Paragraph)
        self.assertEqual(document.model_dump()["paragraphs"][1]["tables"][0]["cells"][0][0]["text"], "单元格")

    def test_rejects_legacy_top_level_tables(self):
        with self.assertRaisesRegex(ValidationError, "Top-level"):
            DocumentOutput(paragraphs=[], tables=[self.table], styles=self.styles)


if __name__ == "__main__":
    unittest.main()
