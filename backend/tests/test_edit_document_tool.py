import unittest
from unittest.mock import Mock, patch

from app.services.tools.document_tools import _edit_document_impl
from app.services.tools.schemas import Run


class EditDocumentToolTests(unittest.TestCase):
    @patch("app.services.tools.document_tools._wait_for_frontend_mutation")
    @patch("app.services.tools.document_tools.get_stream_writer")
    def test_sends_runs_and_waits_for_correlated_frontend_result(self, get_writer, wait_for_result):
        writer = Mock()
        get_writer.return_value = writer
        wait_for_result.return_value = {
            "type": "edit_document_response",
            "success": True,
            "paraID": 101,
        }

        result = _edit_document_impl(101, [Run(text="新内容")], 9)

        request = writer.call_args_list[0].args[0]
        self.assertEqual(request["type"], "edit_document")
        self.assertEqual(request["paraID"], 101)
        self.assertEqual(request["runs"], [{"text": "新内容"}])
        self.assertEqual(request["docId"], 9)
        wait_for_result.assert_called_once_with(request["requestId"])
        self.assertTrue(result["success"])
        self.assertEqual(writer.call_args_list[-1].args[0]["type"], "edit_complete")

    @patch("app.services.tools.document_tools.get_stream_writer")
    def test_rejects_invalid_para_id_before_contacting_frontend(self, get_writer):
        result = _edit_document_impl("not-an-id", [Run(text="text")], 0)

        self.assertFalse(result["success"])
        get_writer.assert_not_called()

    @patch("app.services.tools.document_tools.get_stream_writer")
    def test_rejects_newlines_before_contacting_frontend(self, get_writer):
        result = _edit_document_impl(101, [Run(text="第一段\n第二段")], 0)

        self.assertFalse(result["success"])
        get_writer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
