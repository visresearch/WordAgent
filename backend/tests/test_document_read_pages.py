import json
import unittest
from unittest.mock import patch

from app.services.tools import document_tools


class CompactDocumentPageRangeTests(unittest.TestCase):
    def test_places_read_table_between_paragraphs_by_verified_para_index(self) -> None:
        document = {
            "paragraphs": [
                {"paraIndex": 4, "paraID": 1, "runs": [{"text": "before"}]},
                {"paraIndex": 8, "paraID": 2, "runs": [{"text": "after"}]},
            ],
            "tables": [
                {
                    "paraIndex": 6,
                    "endParaIndex": 7,
                    "rows": 1,
                    "columns": 1,
                    "cells": [[{"text": "cell"}]],
                }
            ],
        }

        ordered = document_tools._order_document_blocks(document)

        self.assertNotIn("tables", ordered)
        self.assertEqual(ordered["paragraphs"][0]["runs"][0]["text"], "before")
        self.assertEqual(ordered["paragraphs"][1]["tables"][0]["cells"][0][0]["text"], "cell")
        self.assertEqual(ordered["paragraphs"][2]["runs"][0]["text"], "after")

    def test_compaction_keeps_table_in_ordered_paragraph_stream(self) -> None:
        document = {
            "paragraphs": [
                {"paraIndex": 1, "paraID": 1, "runs": [{"text": "before"}]},
                {"paraIndex": 3, "paraID": 2, "runs": [{"text": "after"}]},
            ],
            "tables": [{"paraIndex": 2, "endParaIndex": 2, "cells": [[{"text": "cell"}]]}],
        }

        with patch.object(document_tools, "_MAX_DOC_JSON_CHARS", 1):
            compact = json.loads(document_tools._compact_doc_json(document))

        self.assertNotIn("tables", compact)
        self.assertEqual(compact["paragraphs"][1]["tables"][0]["cellTexts"], [["cell"]])

    def test_preserves_new_client_ordered_table_blocks(self) -> None:
        document = {
            "paragraphs": [
                {"paraIndex": 1, "paraID": 1, "runs": [{"text": "before"}]},
                {"tables": [{"paraIndex": 2, "endParaIndex": 2, "cells": [[{"text": "cell"}]]}]},
                {"paraIndex": 3, "paraID": 2, "runs": [{"text": "after"}]},
            ],
            "styles": {"rS_1": ["Arial", 12, False, False, 0, "#000000", "#000000", 0, False, False, False]},
        }

        ordered = document_tools._order_document_blocks(document)

        self.assertNotIn("tables", ordered)
        self.assertEqual(ordered["paragraphs"], document["paragraphs"])

    def test_compaction_preserves_complete_page_range(self) -> None:
        document = {
            "paragraphs": [
                {
                    "paraIndex": 4,
                    "paraID": 123,
                    "pageStart": 2,
                    "pageEnd": 3,
                    "runs": [{"text": "paragraph", "rStyle": "rS_1"}],
                }
            ],
            "styles": {"rS_1": ["Arial", 12, False, False, 0, "#000000", "#000000", 0, False, False, False]},
        }

        with patch.object(document_tools, "_MAX_DOC_JSON_CHARS", 1):
            compact = json.loads(document_tools._compact_doc_json(document))

        self.assertEqual(compact["paragraphs"][0]["pageStart"], 2)
        self.assertEqual(compact["paragraphs"][0]["pageEnd"], 3)

    def test_compaction_omits_partial_page_range(self) -> None:
        document = {
            "paragraphs": [
                {
                    "paraIndex": 0,
                    "paraID": 1,
                    "pageStart": 1,
                    "runs": [{"text": "paragraph", "rStyle": "rS_1"}],
                }
            ]
        }

        with patch.object(document_tools, "_MAX_DOC_JSON_CHARS", 1):
            compact = json.loads(document_tools._compact_doc_json(document))

        self.assertNotIn("pageStart", compact["paragraphs"][0])
        self.assertNotIn("pageEnd", compact["paragraphs"][0])


if __name__ == "__main__":
    unittest.main()
