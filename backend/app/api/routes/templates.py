"""Local template gallery endpoints."""

from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services import templates

router = APIRouter(prefix="/templates")


@router.get("")
def list_templates():
    return templates.list_templates()


@router.post("")
def save_template(
    template_id: UUID = Form(),
    name: str = Form(max_length=120),
    instructions: str = Form(max_length=templates.MAX_INSTRUCTIONS_LENGTH),
    original: UploadFile = File(),
    document_json: UploadFile = File(),
):
    try:
        return templates.save_template(
            template_id, name, instructions, original.filename or "",
            original.file.read(templates.MAX_TEMPLATE_BYTES + 1),
            document_json.file.read(templates.MAX_TEMPLATE_BYTES + 1),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{template_id}")
def get_template(template_id: UUID):
    try:
        return templates.get_template(template_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{template_id}/cover")
def get_cover(template_id: UUID):
    try:
        return FileResponse(templates.get_template_cover(template_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{template_id}/file")
def download_original(template_id: UUID):
    try:
        original = templates.get_template_original(template_id)
        return FileResponse(original, filename=templates.get_template(template_id)["originalName"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{template_id}/copy")
def create_copy(template_id: UUID):
    try:
        return {"path": str(templates.create_template_copy(template_id))}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
