import unittest
from unittest.mock import patch

from app.services.tools import document_tools
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


def test_copy_document_passes_explicit_source_range_and_target_anchor(monkeypatch):
    events = []
    monkeypatch.setattr(document_tools, "get_stream_writer", lambda: events.append)

    def finish_copy(request_id, timeout):
        assert events[-1] == {
            "type": "copy_document",
            "sourceDocID": -9,
            "start_paraID": 31,
            "end_paraID": 14,
            "targetDocID": 17,
            "insertID": 0,
            "requestId": request_id,
        }
        return {
            "success": True,
            "documentId": 17,
            "documentName": "Target.docx",
            "lastParagraph": {"paraID": 23, "paraIndex": 1},
            "revisionCount": 1,
        }

    monkeypatch.setattr(document_tools, "_wait_for_frontend_mutation", finish_copy)
    token = document_tools._current_chat_id.set("copy-range-test")
    try:
        result = document_tools.copy_document.invoke({
            "sourceDocID": "-9", "start_paraID": 31, "end_paraID": 14,
            "targetDocID": 17, "insertID": 0,
        })
    finally:
        document_tools._current_chat_id.reset(token)

    assert result["success"] is True
    assert result["targetDocID"] == 17
    assert result["lastParagraph"] == {"paraID": 23, "paraIndex": 1}
    assert list(document_tools.copy_document.args) == [
        "sourceDocID", "start_paraID", "end_paraID", "targetDocID", "insertID",
    ]


def test_copy_document_rejects_unconfirmed_target(monkeypatch):
    monkeypatch.setattr(document_tools, "get_stream_writer", lambda: lambda event: None)
    monkeypatch.setattr(document_tools, "_wait_for_frontend_mutation",
                        lambda *args, **kwargs: {"success": True, "documentId": 10})
    token = document_tools._current_chat_id.set("verify-copy-target")
    try:
        result = document_tools.copy_document.invoke({
            "sourceDocID": 10, "start_paraID": 1, "end_paraID": 1,
            "targetDocID": 20, "insertID": 8,
        })
    finally:
        document_tools._current_chat_id.reset(token)

    assert result["success"] is None
    assert result["requiresRead"] is True
