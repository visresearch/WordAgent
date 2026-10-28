import pytest

from app.services.agent.tools import read_document
from app.services.tools import document_tools


@pytest.mark.parametrize(
    ("range_args", "expected_range"),
    [
        ({"startParaIndex": 0, "endParaIndex": -1}, (0, -1, None, None)),
        ({"startParaIndex": 0, "endParaIndex": 0}, (0, 0, None, None)),
        ({"startParaIndex": 3, "endParaIndex": -1}, (3, -1, None, None)),
        ({"startParaIndex": 3}, (3, 3, None, None)),
        ({}, (0, 0, None, None)),
        ({"startParaID": -123}, (None, None, -123, -123)),
    ],
)
def test_read_range_is_preserved_in_frontend_request(monkeypatch, range_args, expected_range) -> None:
    events = []
    monkeypatch.setattr(document_tools, "get_stream_writer", lambda: events.append)
    token = document_tools._current_chat_id.set(None)
    try:
        read_document.invoke({"docId": 0, "mode": "lightweight", **range_args})
    finally:
        document_tools._current_chat_id.reset(token)

    request = next(event for event in events if event["type"] == "read_document")
    assert tuple(request[key] for key in ("startParaIndex", "endParaIndex", "startParaID", "endParaID")) == expected_range
    assert request["mode"] == "lightweight"
