"""Capture a document template through the current Word or WPS add-in."""

from typing import Annotated
from uuid import uuid4

from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from pydantic import Field

from app.services.templates import MAX_INSTRUCTIONS_LENGTH

from .callback import _current_chat_id, is_stop_requested
from .document_tools import RequiredDocIdInput, _normalize_required_doc_id, _wait_for_frontend_mutation


@tool
def save_document_template(
    docId: RequiredDocIdInput,
    name: Annotated[str, Field(min_length=1, max_length=120)],
    instructions: Annotated[str, Field(min_length=1, max_length=MAX_INSTRUCTIONS_LENGTH)],
) -> dict:
    """Archive an open Word document as a reusable gallery template.

    Use after analyzing a reference with the document-format-replication Skill.
    docId must identify the reference document. Provide a short human-readable
    name and Markdown instructions covering document structure, formatting,
    fixed text, editable fields, and verification. The tool captures the original
    document file and the full DocxJSON from the add-in without editing the reference.
    """
    chat_id = _current_chat_id.get()
    if not chat_id or is_stop_requested(chat_id):
        return {"success": False, "error": "An active Word or WPS chat is required"}
    request_id = str(uuid4())
    get_stream_writer()({
        "type": "save_document_template",
        "requestId": request_id,
        "docId": _normalize_required_doc_id(docId),
        "name": name,
        "instructions": instructions,
    })
    response = _wait_for_frontend_mutation(request_id, timeout=120)
    if not response or not response.get("success"):
        return {"success": False, "error": (response or {}).get("error") or "The add-in did not confirm the archive"}
    return {
        "success": True,
        "name": name,
        "id": request_id,
        "instructionsPath": f"template/{request_id}/instructions.md",
    }
