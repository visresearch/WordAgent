import unittest
from unittest.mock import Mock, patch

from app.services.tools.document_tools import _delete_document_impl


class DeleteDocumentToolTests(unittest.TestCase):
    @patch("app.services.tools.document_tools._wait_for_frontend_mutation")
    @patch("app.services.tools.document_tools.get_stream_writer")
    def test_waits_for_correlated_frontend_result(self, get_writer, wait_for_result):
        writer = Mock()
        get_writer.return_value = writer
        wait_for_result.return_value = {
            "type": "delete_response",
            "success": True,
            "deletedCount": 2,
            "missingParaIDs": [],
            "replacementInsertParaID": 88,
        }

        result = _delete_document_impl([101, "202", 101], 9)

        request = writer.call_args_list[0].args[0]
        self.assertEqual(request["type"], "delete_document")
        self.assertEqual(request["paraIDs"], [101, 202])
        self.assertEqual(request["docId"], 9)
        self.assertTrue(request["requestId"])
        wait_for_result.assert_called_once_with(request["requestId"])
        self.assertTrue(result["success"])
        self.assertEqual(result["deletedCount"], 2)
        self.assertEqual(result["replacementInsertParaID"], 88)
        self.assertEqual(result["requestId"], request["requestId"])
        self.assertEqual(writer.call_args_list[-1].args[0]["type"], "delete_complete")

    @patch("app.services.tools.document_tools._wait_for_frontend_mutation")
    @patch("app.services.tools.document_tools.get_stream_writer")
    def test_surfaces_partial_delete_instead_of_claiming_notification(self, get_writer, wait_for_result):
        get_writer.return_value = Mock()
        wait_for_result.return_value = {
            "type": "delete_response",
            "success": False,
            "deletedCount": 1,
            "missingParaIDs": [202],
            "failedParaIDs": [303],
            "error": "部分 paraID 未找到",
        }

        result = _delete_document_impl([101, 202, 303], 0)

        self.assertFalse(result["success"])
        self.assertEqual(result["deletedCount"], 1)
        self.assertEqual(result["missingParaIDs"], [202])
        self.assertEqual(result["failedParaIDs"], [303])
        self.assertEqual(result["error"], "部分 paraID 未找到")

    @patch("app.services.tools.document_tools.get_stream_writer")
    def test_rejects_empty_para_ids_without_contacting_frontend(self, get_writer):
        result = _delete_document_impl([None, "", "not-an-id"], 0)

        self.assertFalse(result["success"])
        self.assertEqual(result["requestedCount"], 0)
        get_writer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
