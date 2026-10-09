import asyncio
import json
from unittest.mock import Mock, patch

import pytest
from langchain.agents.middleware import ToolCallRequest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.services.document_edit_policy import edit_style_context, prepare_document_call
from app.services.middleware import TOOL_RETRY_MIDDLEWARE, ToolNormalizationAndLoggingMiddleware
from app.services.tools.document_tools import build_edit_document

STYLE = ["Times New Roman", 12, False, False, 0, "#000000", "#000000", 0, False, False, False]


def add(messages, name, args, result, status="success"):
    call = {"name": name, "args": args, "id": str(len(messages)), "type": "tool_call"}
    messages.extend(
        [
            AIMessage(content="", tool_calls=[call]),
            ToolMessage(content=json.dumps(result), name=name, tool_call_id=call["id"], status=status),
        ]
    )


def call(name="edit_document", **args):
    return {"name": name, "id": "next", "args": {"docId": 9, "paraID": 101, **args}, "type": "tool_call"}


def state(messages):
    return {"messages": messages, "request_context": {"document_meta": [{"documentId": 9}]}}


def test_style_context_is_per_document_and_uses_latest_read():
    messages = [HumanMessage(content="修改")]
    add(messages, "read_document", {"docId": 9}, {"styles": {"rS_1": STYLE}, "paragraphs": []})
    add(messages, "read_document", {"docId": 10}, {"styles": {"rS_1": ["wrong"]}, "paragraphs": []})
    assert prepare_document_call(call(docId=0), state(messages))[0] == {"rS_1": STYLE}
    add(messages, "read_document", {"docId": 9}, {"styles": {"rS_2": STYLE}, "paragraphs": []})
    assert prepare_document_call(call(), state(messages))[0] == {"rS_2": STYLE}


@pytest.mark.parametrize("asynchronous", [False, True])
def test_actual_tool_schema_keeps_reference_but_frontend_receives_character_array(asynchronous):
    messages = [HumanMessage(content="只改字符样式")]
    add(messages, "read_document", {"docId": 9}, {"styles": {"rS_1": STYLE}, "paragraphs": []})
    tool = build_edit_document("Edit paragraph")
    request = ToolCallRequest(
        tool_call=call(runs=[{"text": "English", "rStyle": "rS_1"}]), tool=tool, state=state(messages), runtime=None
    )
    middleware = ToolNormalizationAndLoggingMiddleware()
    writer = Mock()
    with (
        patch("app.services.middleware.tool_normalization_and_logging._record_result"),
        patch("app.services.tools.document_tools.get_stream_writer", return_value=writer),
        patch("app.services.tools.document_tools._wait_for_frontend_mutation", return_value={"success": True}),
    ):
        if asynchronous:

            async def handler(req):
                return await tool.ainvoke(req.tool_call)

            result = asyncio.run(middleware.awrap_tool_call(request, handler))
        else:
            result = middleware.wrap_tool_call(request, lambda req: tool.invoke(req.tool_call))
    assert json.loads(result.content)["success"] is True
    event = writer.call_args_list[0].args[0]
    assert event["runs"] == [{"text": "English", "rStyle": STYLE}]
    assert "pStyle" not in event
    assert edit_style_context.get() is None


def test_failed_delete_requires_fresh_target_read_before_edit_or_rebuild():
    messages = [HumanMessage(content="修改")]
    add(messages, "delete_document", {"docId": 9, "paraIDs": [101]}, {"success": False, "rollbackVerified": False})
    assert prepare_document_call(call(), state(messages))[1]["requiresRead"]
    add(messages, "read_document", {"docId": 9}, {"paragraphs": [{"paraID": 88}]})
    assert prepare_document_call(call(), state(messages))[1]["requiresRead"]
    assert prepare_document_call(call("generate_document", insertParaID=88), state(messages))[1] is None
    add(messages, "read_document", {"docId": 9}, {"paragraphs": [{"paraID": 101}]})
    assert prepare_document_call(call(), state(messages))[1] is None


def test_same_text_allows_one_correction_then_blocks_edit_and_delete():
    messages = [HumanMessage(content="修改")]
    args = {"docId": 9, "paraID": 101, "runs": [{"text": "正文", "rStyle": "rS_1"}]}
    add(messages, "edit_document", args, {"success": True})
    assert prepare_document_call(call(**args), state(messages))[1] is None
    add(messages, "read_document", {"docId": 9}, {"paragraphs": [{"paraID": 101}]})
    add(messages, "edit_document", args, {"success": True})
    assert prepare_document_call(call(**args), state(messages))[1]["errorCode"] == "no_progress"
    assert (
        prepare_document_call(call("delete_document", paraIDs=[101]), state(messages))[1]["errorCode"] == "no_progress"
    )
    assert prepare_document_call(call(runs=[{"text": "新的实质内容"}]), state(messages))[1] is None
    messages.append(HumanMessage(content="我现在要求再次修改"))
    assert prepare_document_call(call(**args), state(messages))[1] is None


@pytest.mark.parametrize("asynchronous", [False, True])
def test_mutation_exception_is_never_replayed(asynchronous):
    request = ToolCallRequest(tool_call=call(), tool=None, state=state([]), runtime=None)
    attempts = []

    def handler(req):
        attempts.append(req)
        raise RuntimeError("connection lost after write")

    if asynchronous:

        async def async_handler(req):
            return handler(req)

        result = asyncio.run(TOOL_RETRY_MIDDLEWARE.awrap_tool_call(request, async_handler))
    else:
        result = TOOL_RETRY_MIDDLEWARE.wrap_tool_call(request, handler)
    assert len(attempts) == 1
    assert json.loads(result.content)["requiresRead"] is True
    assert json.loads(result.content)["success"] is None


def test_old_active_document_styles_are_not_reused_after_switch():
    messages = [HumanMessage(content="旧文档")]
    add(messages, "read_document", {"docId": 0}, {"styles": {"rS_1": STYLE}, "paragraphs": []})
    messages.append(HumanMessage(content="换了文档"))
    assert prepare_document_call(call(docId=0), state(messages))[0] == {}


def test_two_uncertain_deletions_stop_even_after_a_read():
    messages = [HumanMessage(content="删除")]
    for _ in range(2):
        add(messages, "delete_document", {"docId": 9, "paraIDs": [101]}, {"success": None})
        add(messages, "read_document", {"docId": 9}, {"paragraphs": [{"paraID": 101}]})
    assert (
        prepare_document_call(call("delete_document", paraIDs=[101]), state(messages))[1]["errorCode"] == "no_progress"
    )
