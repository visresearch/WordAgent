import asyncio
import json
import unittest
from unittest.mock import Mock, patch

import pytest
from langchain.agents.middleware import ToolCallRequest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.services.middleware import ToolNormalizationAndLoggingMiddleware
from app.services.tools.document_tools import _document_character_styles, _edit_document_impl, build_edit_document
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


def test_unknown_style_fails_before_document_mutation():
    with patch("app.services.tools.document_tools.get_stream_writer") as writer:
        result = _edit_document_impl(101, [Run(text="新内容", rStyle="rS_missing")], 9)
    assert result["success"] is False
    assert result["errorCode"] == "unresolved_character_style"
    writer.assert_not_called()


STYLE = ["Times New Roman", 12, False, False, 0, "#000000", "#000000", 0, False, False, False]


def _add_tool_result(messages, name, args, result, status="success"):
    call = {"name": name, "args": args, "id": str(len(messages)), "type": "tool_call"}
    messages.extend(
        [
            AIMessage(content="", tool_calls=[call]),
            ToolMessage(content=json.dumps(result), name=name, tool_call_id=call["id"], status=status),
        ]
    )


def test_character_styles_use_latest_matching_document_read():
    messages = [HumanMessage(content="edit")]
    _add_tool_result(messages, "read_document", {"docId": 9}, {"styles": {"rS_1": STYLE}})
    _add_tool_result(messages, "read_document", {"docId": 10}, {"styles": {"rS_1": ["other document"]}})
    state = {"messages": messages, "request_context": {"document_meta": [{"documentId": 9}]}}
    assert _document_character_styles(state, 0) == {"rS_1": STYLE}
    _add_tool_result(messages, "read_document", {"docId": 9}, {"styles": {"rS_2": STYLE}})
    assert _document_character_styles(state, 9) == {"rS_2": STYLE}


def test_active_document_style_references_do_not_cross_user_turns():
    messages = [HumanMessage(content="old document")]
    _add_tool_result(messages, "read_document", {"docId": 0}, {"styles": {"rS_1": STYLE}})
    messages.append(HumanMessage(content="different document"))
    state = {"messages": messages, "request_context": {"document_meta": {"documentId": 10}}}
    assert _document_character_styles(state, 0) == {}


def test_successful_generation_can_supply_character_styles():
    messages = [HumanMessage(content="generate then edit")]
    _add_tool_result(
        messages, "generate_document", {"docId": 9, "document": {"styles": {"rS_1": STYLE}}}, {"success": True}
    )
    assert _document_character_styles({"messages": messages}, 9) == {"rS_1": STYLE}


@pytest.mark.parametrize("asynchronous", [False, True])
def test_tool_runtime_resolves_styles_without_exposing_runtime_to_model(asynchronous):
    messages = [HumanMessage(content="edit character format")]
    _add_tool_result(messages, "read_document", {"docId": 9}, {"styles": {"rS_1": STYLE}})
    messages.append(
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "edit_document",
                    "id": "edit",
                    "type": "tool_call",
                    "args": {"docId": 9, "paraID": 101, "runs": [{"text": "English", "rStyle": "rS_1"}]},
                }
            ],
        )
    )
    tool = build_edit_document("Edit paragraph")
    schema = tool.tool_call_schema.model_json_schema()
    assert set(schema["properties"]) == {"paraID", "runs", "docId"}
    assert "rStyle" in schema["$defs"]["Run"]["properties"]
    writer = Mock()
    with (
        patch("app.services.tools.document_tools.get_stream_writer", return_value=writer),
        patch("app.services.tools.document_tools._wait_for_frontend_mutation", return_value={"success": True}),
    ):
        builder = StateGraph(MessagesState)
        builder.add_node("tools", ToolNode([tool]))
        builder.add_edge(START, "tools")
        builder.add_edge("tools", END)
        graph = builder.compile()
        result = (
            asyncio.run(graph.ainvoke({"messages": messages})) if asynchronous else graph.invoke({"messages": messages})
        )
    assert json.loads(result["messages"][-1].content)["success"] is True
    event = writer.call_args_list[0].args[0]
    assert event["runs"] == [{"text": "English", "rStyle": STYLE}]
    assert "pStyle" not in event


@pytest.mark.parametrize("status", ["success", "error"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_normalization_does_not_block_later_edits_based_on_previous_attempts(status, asynchronous):
    args = {"docId": 9, "paraID": 101, "runs": [{"text": "same text"}]}
    messages = [HumanMessage(content="edit")]
    for _ in range(3):
        _add_tool_result(messages, "edit_document", args, {"success": status == "success"}, status)
    request = ToolCallRequest(
        tool_call={"name": "edit_document", "args": args, "id": "next", "type": "tool_call"},
        tool=None,
        state={"messages": messages},
        runtime=None,
    )
    handler = Mock(return_value=ToolMessage(content='{"success":true}', tool_call_id="next"))
    middleware = ToolNormalizationAndLoggingMiddleware()
    with patch("app.services.middleware.tool_normalization_and_logging._record_result"):
        if asynchronous:

            async def async_handler(req):
                return handler(req)

            result = asyncio.run(middleware.awrap_tool_call(request, async_handler))
        else:
            result = middleware.wrap_tool_call(request, handler)
    assert json.loads(result.content)["success"] is True
    handler.assert_called_once()
