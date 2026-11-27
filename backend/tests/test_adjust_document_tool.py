import json

import pytest
from pydantic import ValidationError

from app.services.agent.tools import AGENT_BASE_TOOLS, ASK_BASE_TOOLS, adjust_document
from app.services.tools import document_tools


def test_adjust_document_waits_for_its_correlated_response(monkeypatch):
    events = []
    margins = {"top": 2.5, "bottom": 2.5, "left": 3, "right": 2}

    def wait_for_response(request_id):
        assert request_id == events[0]["requestId"]
        assert events[0]["type"] == "adjust_document"
        assert events[0]["docId"] == 42
        assert events[0]["pageMarginsCm"] == {"left": 3}
        return {"type": "adjust_document_response", "success": True, "docId": 42, "pageMarginsCm": margins}

    monkeypatch.setattr(document_tools, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr(document_tools, "_wait_for_frontend_mutation", wait_for_response)
    token = document_tools._current_chat_id.set("page-margins-test")
    try:
        result = adjust_document.invoke({"docId": "42", "pageMarginsCm": {"left": 3}})
    finally:
        document_tools._current_chat_id.reset(token)
    assert result == {"success": True, "docId": 42, "pageMarginsCm": margins}
    assert adjust_document in AGENT_BASE_TOOLS
    assert adjust_document not in ASK_BASE_TOOLS


@pytest.mark.parametrize("margins", [{}, {"top": -1}, {"left": "3"}, {"left": float("inf")}, {"inside": 2}])
def test_invalid_page_margins_are_rejected_before_dispatch(margins):
    with pytest.raises(ValidationError):
        adjust_document.invoke({"docId": 0, "pageMarginsCm": margins})


def test_compact_document_keeps_page_margins(monkeypatch):
    monkeypatch.setattr(document_tools, "_MAX_DOC_JSON_CHARS", 1)
    meta = {"pageMarginsCm": {"top": 2.5, "bottom": 2.5, "left": None, "right": 2}}
    result = json.loads(document_tools._compact_doc_json({"paragraphs": [], "meta": meta}))
    assert result["_compacted"] is True
    assert result["meta"] == meta
