"""Helpers for document context injected into model prompts."""

from __future__ import annotations

from typing import Any


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_document_meta(document_meta: list | dict | None) -> list[dict]:
    """Return prompt-safe document metadata.

    Invalid/unavailable fields are omitted instead of being injected as
    sentinel values such as pageCount=0.
    """

    if not document_meta:
        return []

    raw_items = document_meta if isinstance(document_meta, list) else [document_meta]
    normalized: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue

        cleaned = dict(item)

        document_name = str(cleaned.get("documentName") or "").strip()
        if document_name:
            cleaned["documentName"] = document_name
        else:
            cleaned.pop("documentName", None)

        page_count = _to_int(cleaned.get("pageCount"))
        if page_count and page_count > 0:
            cleaned["pageCount"] = page_count
        else:
            cleaned.pop("pageCount", None)

        normalized.append(cleaned)

    return normalized


def build_document_name_by_id(meta_list: list[dict]) -> dict[int, str]:
    names: dict[int, str] = {}
    for meta in meta_list:
        name = str(meta.get("documentName") or "").strip()
        if not name:
            continue
        doc_id = _to_int(meta.get("documentId", meta.get("docId")))
        if doc_id is not None:
            names[doc_id] = name

    if len(meta_list) == 1:
        name = str(meta_list[0].get("documentName") or "").strip()
        if name:
            names.setdefault(0, name)

    return names


def format_document_range_line(
    range_item: dict,
    document_name_by_id: dict[int, str] | None = None,
    *,
    brackets: tuple[str, str] = ("《", "》"),
) -> str:
    doc_id = _to_int(range_item.get("docId")) or 0
    start = range_item.get("startParaIndex", 0)
    end = range_item.get("endParaIndex", -1)
    start_id = _to_int(range_item.get("startParaID"))
    end_id = _to_int(range_item.get("endParaID"))
    doc_name = str(range_item.get("docName") or "").strip()
    if not doc_name and document_name_by_id:
        doc_name = document_name_by_id.get(doc_id, "")

    prefix = f"{brackets[0]}{doc_name}{brackets[1]}" if doc_name else ""
    if start_id is not None:
        end_id = start_id if end_id is None else end_id
        return (
            f"{prefix}docId={doc_id}, selected paragraphIndex {start} to {end}, selected paraID {start_id} to {end_id}"
        )
    return f"{prefix}docId={doc_id}, selected paragraphIndex {start} to {end}"
