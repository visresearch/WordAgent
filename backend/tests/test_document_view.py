import asyncio
import io
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from PIL import Image

from app.api.routes import files
from app.services import document_view
from app.services.middleware.document_view import DocumentViewMiddleware
from app.services.middleware.image_paths import ImagePathMiddleware
from app.services.tools import document_tools


@pytest.fixture
def pdf_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(document_view, "get_temp_dir", lambda: tmp_path)
    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        for size, color in [((8, 5), "blue"), ((6, 8), "red"), ((8, 5), "green")]:
            pdf.savefig(Figure(figsize=size, facecolor=color))
    return buffer.getvalue()


def test_document_view_endpoint_renders_inclusive_range_at_fixed_dpi(pdf_bytes, tmp_path):
    app = FastAPI()
    app.include_router(files.router, prefix="/api/chat")

    def render(client, request_id, start, end, mode):
        return client.post(
            f"/api/chat/document-view/{request_id}",
            params={"page_start": start, "page_end": end, "mode": mode},
            files={"file": ("editor.pdf", pdf_bytes, "application/pdf")},
        )

    with TestClient(app) as client:
        single_id = uuid4()
        response = render(client, single_id, 2, 3, "single")
        assert response.is_success, response.text
        _, page_2 = document_view.view_images(single_id, 2, 2, "single")[0]
        _, page_3 = document_view.view_images(single_id, 3, 3, "single")[0]
        with Image.open(page_2) as portrait, Image.open(page_3) as landscape:
            assert portrait.size == (720, 960)
            assert landscape.size == (960, 600)
            assert portrait.info["dpi"][0] == pytest.approx(120, abs=0.02)

        combined_id = uuid4()
        assert render(client, combined_id, 2, 3, "combine").is_success
        _, combined = document_view.view_images(combined_id, 2, 3, "combine")[0]
        with Image.open(combined) as image:
            assert image.size == (960, 1560)
            assert image.getpixel((0, 0)) == (255, 255, 255)
            assert image.getpixel((480, 0)) == (255, 0, 0)
            assert image.getpixel((480, 960)) == (0, 128, 0)
        assert len(list(combined.parent.iterdir())) == 1

        invalid_id = uuid4()
        assert render(client, invalid_id, 3, 2, "combine").status_code == 400
        missing = render(client, invalid_id, 2, 4, "single")
        assert missing.status_code == 400
        assert "3 pages" in missing.json()["detail"]
        assert not list(tmp_path.rglob("*.pdf"))
        assert not (tmp_path / "view_document" / str(invalid_id)).exists()


@pytest.mark.parametrize(("async_model", "doc_id"), [(False, None), (True, 83)])
def test_view_document_sends_image_and_saved_path_only_to_next_model_request(pdf_bytes, monkeypatch, async_model, doc_id):
    events = []
    received = []
    monkeypatch.setattr(document_tools, "get_stream_writer", lambda: events.append)

    def finish_render(request_id, timeout):
        pending = events[-1]
        assert pending["type"] == "view_document"
        assert pending["requestId"] == request_id
        assert pending["docId"] == (doc_id or 0)
        document_view.render_document_view(
            pdf_bytes, UUID(request_id), pending["page_start"], pending["page_end"], pending["mode"],
        )
        return {"success": True, "documentId": 83, "documentName": "Copy.docx"}

    monkeypatch.setattr(document_tools, "_wait_for_frontend_mutation", finish_render)

    class VisionRecorder(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            received.append(messages)
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    args = {"page_start": 2, "page_end": 3, "mode": "combine"}
    if doc_id is not None:
        args["docId"] = doc_id
    graph = create_agent(
        VisionRecorder(responses=[
            AIMessage(content="", tool_calls=[{
                "name": "view_document", "id": "view-call",
                "args": args,
            }]),
            AIMessage(content="Viewed the page images."),
        ]),
        tools=[document_tools.view_document],
        middleware=[ImagePathMiddleware(), DocumentViewMiddleware()],
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "document-view"}}
    conversation = {"messages": [HumanMessage(content="Show pages 2 and 3.")]}
    chat_token = document_tools._current_chat_id.set("document-view-chat")
    try:
        if async_model:
            asyncio.run(graph.ainvoke(conversation, config))
        else:
            graph.invoke(conversation, config)
    finally:
        document_tools._current_chat_id.reset(chat_token)

    visible_message = received[1][-1]
    assert isinstance(visible_message, HumanMessage)
    png = document_view.view_images(UUID(events[-1]["requestId"]), 2, 3, "combine")[0][1]
    assert str(png) in visible_message.content[1]["text"]
    assert visible_message.content[2]["type"] == "image"
    assert visible_message.content[2]["base64"]
    history = graph.get_state(config).values["messages"]
    tool_result = next(message for message in history if isinstance(message, ToolMessage))
    assert str(png) in tool_result.content
    assert "Copy.docx (documentId=83)" in tool_result.content
    assert visible_message not in history
    assert all("base64" not in str(message.content) for message in history)


def test_view_document_rejects_render_from_a_different_document(monkeypatch):
    monkeypatch.setattr(document_tools, "get_stream_writer", lambda: lambda event: None)
    monkeypatch.setattr(document_tools, "_wait_for_frontend_mutation",
                         lambda *args, **kwargs: {"success": True, "documentId": 14})
    token = document_tools._current_chat_id.set("verify-render-target")
    try:
        result = document_tools.view_document.invoke({
            "name": "view_document", "id": "render-call", "type": "tool_call",
            "args": {"page_start": 1, "page_end": 1, "mode": "single", "docId": -10},
        })
    finally:
        document_tools._current_chat_id.reset(token)
    assert "did not confirm the requested document" in result.content
    assert result.artifact is None
