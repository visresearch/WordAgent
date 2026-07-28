import unittest
from unittest.mock import patch

from app.services.tools.document_tools import _create_document_impl, build_create_document


class CreateDocumentToolTests(unittest.TestCase):
    def test_emits_create_document_event(self):
        events = []
        with patch("app.services.tools.document_tools.get_stream_writer", return_value=events.append):
            result = _create_document_impl()

        self.assertIn("new blank DOCX", result)
        self.assertEqual(
            events,
            [
                {
                    "type": "create_document",
                    "format": "docx",
                    "content": "📄 正在创建新的空白 DOCX 文档",
                }
            ],
        )

    def test_tool_takes_no_parameters(self):
        tool = build_create_document("Create a document")
        schema = tool.args_schema.model_json_schema()
        self.assertEqual(schema.get("properties", {}), {})


if __name__ == "__main__":
    unittest.main()
