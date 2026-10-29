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

        result = _delete_document_impl(101, "202", 9)

        request = writer.call_args_list[0].args[0]
        self.assertEqual(request["type"], "delete_document")
        self.assertEqual(request["startParaID"], 101)
        self.assertEqual(request["endParaID"], 202)
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

        result = _delete_document_impl(101, 303, 0)

        self.assertFalse(result["success"])
        self.assertEqual(result["deletedCount"], 1)
        self.assertEqual(result["missingParaIDs"], [202])
        self.assertEqual(result["failedParaIDs"], [303])
        self.assertEqual(result["error"], "部分 paraID 未找到")

    @patch("app.services.tools.document_tools.get_stream_writer")
    def test_rejects_empty_para_ids_without_contacting_frontend(self, get_writer):
        result = _delete_document_impl(None, "not-an-id", 0)

        self.assertFalse(result["success"])
        self.assertEqual(result["requestedCount"], 0)
        get_writer.assert_not_called()


if __name__ == "__main__":
    unittest.main()


def test_unknown_delete_result_is_not_reported_as_zero_deletions():
    with (
        patch("app.services.tools.document_tools.get_stream_writer", return_value=Mock()),
        patch(
            "app.services.tools.document_tools._wait_for_frontend_mutation",
            return_value={
                "success": False,
                "requiresRead": True,
                "deletedCount": None,
                "error": "删除结果未确认",
            },
        ),
    ):
        result = _delete_document_impl(101, None, 9)
    assert result["deletedCount"] is None
    assert result["requiresRead"] is True


def test_range_schema_has_explicit_endpoints_and_no_independent_id_list():
    from app.services.tools.document_tools import build_delete_document
    tool = build_delete_document("Delete a range")
    schema = tool.args_schema.model_json_schema()
    assert "startParaID" in schema["required"]
    assert "endParaID" in schema["properties"]
    assert "paraIDs" not in schema["properties"]


def test_table_count_and_actual_ids_are_forwarded_without_confusing_endpoints_with_count():
    with (
        patch("app.services.tools.document_tools.get_stream_writer", return_value=Mock()),
        patch("app.services.tools.document_tools._wait_for_frontend_mutation", return_value={
            "success": True, "requestedCount": 5, "deletedCount": 5, "deletedTableCount": 1,
            "deletedParaIDs": [900, 10, 500, -30, 200], "replacementInsertParaID": 0,
        }),
    ):
        result = _delete_document_impl(900, 200, 9)
    assert result["startParaID"] == 900
    assert result["endParaID"] == 200
    assert result["requestedCount"] == 5
    assert result["deletedTableCount"] == 1
    assert result["deletedParaIDs"] == [900, 10, 500, -30, 200]
