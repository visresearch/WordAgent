import json
import unittest
from unittest.mock import patch

from app.services.tools import document_tools


class CompactDocumentPageRangeTests(unittest.TestCase):
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
