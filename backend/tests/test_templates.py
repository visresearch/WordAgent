import io
import json
from pathlib import Path
from uuid import uuid4

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.templates import router
from app.services import templates
from app.services.tools import template_tools


def test_archives_docx_full_json_and_instructions_then_makes_independent_copies(tmp_path, monkeypatch):
    monkeypatch.setattr(templates, "get_wence_project_dir", lambda: tmp_path)
    cache = tmp_path / "temp"
    cache.mkdir()
    diagram = cache / "diagram.png"
    diagram.write_bytes(b"preview bytes")

    document = Document()
    document.add_heading("项目报告", 0)
    document.sections[0].header.paragraphs[0].text = "固定页眉"
    source = io.BytesIO()
    document.save(source)
    source_bytes = source.getvalue()

    doc_json = {
        "paragraphs": [
            {"pStyle": "pS_1", "pageStart": 1, "runs": [{"text": "项目"}, {"text": "报告"}, {"url": str(diagram)}]},
            {"pageStart": 2, "runs": [{"text": "第二页正文"}]},
        ],
        "styles": {"pS_1": [1, 0, 0, 0, 0, 0, 0, "Title"]},
    }
    template_id = str(uuid4())
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        assert client.get("/templates").json() == []
        fields = {"template_id": template_id, "name": "项目报告", "instructions": "# 使用说明\n编辑封面标题"}
        files = {
            "original": ("报告.docx", source_bytes),
            "document_json": ("document.json", json.dumps(doc_json)),
        }
        response = client.post("/templates", data=fields, files=files)
        assert response.status_code == 200, response.text
        entry = response.json()
        assert entry["coverLines"] == [{"text": "项目报告", "heading": True, "centered": True}]
        assert client.post("/templates", data=fields, files=files).json() == entry
        assert client.get("/templates").json() == [entry]
        assert client.get(f"/templates/{template_id}").json()["instructions"] == fields["instructions"] + "\n"
        assert client.get(f"/templates/{template_id}/file").content == source_bytes

        archived = tmp_path / "template" / template_id
        saved_json = json.loads((archived / "document.json").read_text(encoding="utf-8"))
        assert len(saved_json["paragraphs"]) == 2
        assert saved_json["styles"] == doc_json["styles"]
        diagram.unlink()
        assert (tmp_path / saved_json["paragraphs"][0]["runs"][-1]["url"]).read_bytes() == b"preview bytes"

        first = Path(client.post(f"/templates/{template_id}/copy").json()["path"])
        second = Path(client.post(f"/templates/{template_id}/copy").json()["path"])
        assert first != second
        assert first.read_bytes() == second.read_bytes() == source_bytes
        assert Document(first).sections[0].header.paragraphs[0].text == "固定页眉"
        first.write_bytes(b"edited independently")
        assert (archived / "original.docx").read_bytes() == source_bytes

        response = client.post("/templates", data={**fields, "template_id": str(uuid4())}, files={
            **files, "original": ("invalid.docx", b"invalid document"),
        })
        assert response.status_code == 400
        assert list((tmp_path / "template").iterdir()) == [archived]


def test_archive_tool_requests_original_and_waits_for_matching_confirmation(monkeypatch):
    events = []
    monkeypatch.setattr(template_tools, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr(template_tools, "is_stop_requested", lambda chat_id: False)

    def confirm(request_id, timeout):
        assert request_id == events[0]["requestId"]
        assert events[0]["docId"] == 31
        return {"success": True}

    monkeypatch.setattr(template_tools, "_wait_for_frontend_mutation", confirm)
    turn = template_tools._current_chat_id.set("test-chat")
    try:
        result = template_tools.save_document_template.invoke({
            "docId": "31", "name": "年度报告", "instructions": "# 格式要求",
        })
    finally:
        template_tools._current_chat_id.reset(turn)
    assert result["instructionsPath"] == f"template/{events[0]['requestId']}/instructions.md"
    assert result["success"]
