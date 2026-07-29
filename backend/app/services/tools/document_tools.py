from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import importlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from app.core.config import get_temp_dir, get_wence_data_dir, get_wence_project_dir
from app.core.logging import get_logger

from .callback import (
    _current_chat_id,
    _pending_loops,
    _pending_tool_requests,
    is_stop_requested,
    wait_for_tool_response,
)
from .schemas import DocumentOutput, DocumentQuery

logger = get_logger(__name__)


# 返回给 LLM 的文档 JSON 最大字符数（超过则进入精简模式）
_MAX_DOC_JSON_CHARS = 100_000


DocIdInput = int | str | None
ParaIdInput = int | str | None
RequiredParaIdInput = int | str
BreakType = Literal["wdLineBreak", "wdPageBreak", "wdSectionBreakNextPage"]


def _parse_int_like(value: object) -> int | None:
    """Parse int-like values from int/str (supports signed numbers)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if re.fullmatch(r"[+-]?\d+", text):
            try:
                return int(text)
            except Exception:
                return None
    return None


def _normalize_doc_id(doc_id: DocIdInput) -> int:
    """Normalize docId to integer, fallback to 0 (active document)."""
    parsed = _parse_int_like(doc_id)
    return parsed if parsed is not None else 0


def _normalize_para_id(para_id: ParaIdInput) -> int | None:
    """Normalize paraID to integer; invalid values return None."""
    return _parse_int_like(para_id)


def _format_generated_document_message(
    para_count: int,
    table_count: int,
    image_count: int,
) -> str:
    """Build a generation summary without displaying zero-value item types."""
    generated_counts = []
    if para_count > 0:
        generated_counts.append(f"{para_count} 个段落")
    if table_count > 0:
        generated_counts.append(f"{table_count} 个表格")
    if image_count > 0:
        generated_counts.append(f"{image_count} 张图片")

    message = "📝 文档已生成"
    if generated_counts:
        message += f"，共 {'，'.join(generated_counts)}"
    return message


def _wait_for_frontend_mutation(request_id: str, timeout: float = 60) -> dict | None:
    """Wait synchronously for a requestId-correlated frontend mutation result."""
    chat_id = _current_chat_id.get(None)
    if not chat_id or is_stop_requested(chat_id):
        return None
    loop = _pending_loops.get(chat_id)
    if not loop:
        return None
    future = asyncio.run_coroutine_threadsafe(
        wait_for_tool_response(chat_id, request_id, timeout=timeout),
        loop,
    )
    try:
        return future.result(timeout=timeout + 5)
    except (TimeoutError, concurrent.futures.TimeoutError):
        logger.warning("[DocumentTool] ⏰ 等待前端操作结果超时 requestId=%s", request_id)
        return None
    except Exception as exc:
        logger.error("[DocumentTool] ❌ 等待前端操作结果失败 requestId=%s: %s", request_id, exc)
        return None


def _normalize_frontend_paragraph_location(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    para_id = _parse_int_like(value.get("paraID"))
    para_index = _parse_int_like(value.get("paraIndex"))
    if para_id is None or para_index is None:
        return None
    page_start = _parse_int_like(value.get("pageStart"))
    page_end = _parse_int_like(value.get("pageEnd"))
    return {
        "paraID": para_id,
        "paraIndex": para_index,
        "pageStart": page_start,
        "pageEnd": page_end,
    }


# region 图片 / 文档辅助


def _download_remote_image(url: str) -> str | None:
    """Download remote image URL to local wence_data/project/temp and return local path."""
    try:
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}:
            ext = ".png"

        temp_dir = get_temp_dir()
        filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
        file_path = temp_dir / filename

        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=20) as resp:
            file_path.write_bytes(resp.read())
        return str(file_path)
    except Exception as e:
        logger.error(f"[generate_document] ⚠️ 下载图片失败: {e}")
        return None


def _save_data_image(data_url: str) -> str | None:
    """Decode data:image URL to local file path."""
    try:
        match = re.match(r"^data:image/([a-zA-Z0-9.+-]+);base64,(.+)$", data_url, flags=re.DOTALL)
        if not match:
            return None

        ext_map = {
            "jpeg": ".jpg",
            "jpg": ".jpg",
            "png": ".png",
            "gif": ".gif",
            "svg+xml": ".svg",
            "webp": ".webp",
            "bmp": ".bmp",
        }
        ext = ext_map.get(match.group(1).lower(), ".png")

        temp_dir = get_temp_dir()
        filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
        file_path = temp_dir / filename

        raw = base64.b64decode(match.group(2), validate=False)
        file_path.write_bytes(raw)
        return str(file_path)
    except Exception as e:
        logger.error(f"[generate_document] ⚠️ 保存 base64 图片失败: {e}")
        return None


def _resolve_local_image_path(path_or_url: str) -> str | None:
    """Resolve local image path from raw path / file:// URL / project-relative path."""
    raw = str(path_or_url or "").strip()
    if not raw:
        return None

    try:
        candidate_str = raw
        if raw.lower().startswith("file://"):
            parsed = urlparse(raw)
            decoded_path = unquote(parsed.path or "")
            if parsed.netloc:
                # UNC path, e.g. file://server/share/a.png
                decoded_path = f"//{parsed.netloc}{decoded_path}"
            # Windows drive path in file URL can become /C:/...
            if re.match(r"^/[a-zA-Z]:/", decoded_path):
                decoded_path = decoded_path[1:]
            candidate_str = decoded_path or ""

        if not candidate_str:
            return None

        candidate = Path(candidate_str).expanduser()
        if not candidate.is_absolute():
            candidate = get_wence_project_dir() / candidate
        candidate = candidate.resolve(strict=False)
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    except Exception:
        return None

    return None


def _to_positive_float(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
        if number > 0:
            return number
    except Exception:
        pass
    return None


def _read_image_size(path: str) -> tuple[float, float] | None:
    """Read image intrinsic width/height by Pillow when available."""
    try:
        pil_image_module = importlib.import_module("PIL.Image")
        open_image = getattr(pil_image_module, "open", None)
        if open_image is None:
            return None
        with open_image(path) as image:
            width, height = image.size
            if width > 0 and height > 0:
                return float(width), float(height)
    except Exception:
        return None
    return None


def _ensure_image_payload_shape(doc_dict: dict) -> None:
    """Normalize image runs to a single `url` field and resolve local paths when possible."""
    paragraphs = doc_dict.get("paragraphs")
    if not isinstance(paragraphs, list):
        return

    for para in paragraphs:
        if not isinstance(para, dict):
            continue
        runs = para.get("runs")
        if not isinstance(runs, list):
            continue

        for run in runs:
            if not isinstance(run, dict):
                continue
            # 跳过文本 run
            if run.get("text") is not None:
                continue

            # 这里是图片 run（无 text 字段）
            run.setdefault("type", "inline")
            raw_url = str(run.get("url") or "").strip()

            normalized_url = raw_url
            if raw_url.startswith("data:image/"):
                local_path = _save_data_image(raw_url)
                if local_path:
                    normalized_url = local_path
            elif raw_url.startswith("http://") or raw_url.startswith("https://"):
                local_path = _download_remote_image(raw_url)
                if local_path:
                    normalized_url = local_path
            elif raw_url:
                local_path = _resolve_local_image_path(raw_url)
                if local_path:
                    normalized_url = local_path

            if normalized_url:
                run["url"] = normalized_url
            else:
                run.pop("url", None)

            if run.get("url") and _resolve_local_image_path(str(run.get("url") or "")) is None:
                logger.error(f"[generate_document] ⚠️ 图片未获取到本地路径，可能插入失败: url={run.get('url')}")

            # 若宽高缺失，则按原图尺寸/比例补齐，避免拉伸变形
            width_value = _to_positive_float(run.get("width"))
            height_value = _to_positive_float(run.get("height"))
            has_width = width_value is not None
            has_height = height_value is not None
            if has_width and has_height:
                continue
            local_image_path = _resolve_local_image_path(str(run.get("url") or ""))
            if not local_image_path:
                continue
            image_size = _read_image_size(local_image_path)
            if not image_size:
                continue
            native_width, native_height = image_size
            if native_width <= 0 or native_height <= 0:
                continue

            # 两边都缺失：使用图片原始尺寸
            if not has_width and not has_height:
                run["width"] = native_width
                run["height"] = native_height
                continue

            # 仅缺一边：按原图比例推导另一边，避免破坏长宽比
            if has_width and not has_height and width_value is not None:
                run["height"] = width_value * native_height / native_width
                continue
            if has_height and not has_width and height_value is not None:
                run["width"] = height_value * native_width / native_height


def _save_generated_document_json(doc_dict: dict) -> str | None:
    """将生成的文档 JSON 持久化到 wence_data/json 目录。"""
    try:
        json_dir = get_wence_data_dir() / "json"
        json_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3]
        filename = f"document_{timestamp}.json"
        file_path = json_dir / filename

        json_str = json.dumps(doc_dict, ensure_ascii=False, indent=2)
        file_path.write_text(json_str, encoding="utf-8")
        return str(file_path)
    except Exception as e:
        logger.error(f"[generate_document] ⚠️ 保存 JSON 文件失败: {e}")
        return None


def _order_document_blocks(doc_json: dict) -> dict:
    """Normalize read_document output to one verified ordered paragraph/table block stream.

    New clients already return ordered table blocks inside ``paragraphs``. The
    legacy top-level ``tables`` conversion remains here for compatibility with
    older clients and in-flight sessions.
    """
    paragraphs = doc_json.get("paragraphs", [])
    tables = doc_json.get("tables", [])
    if not isinstance(paragraphs, list) or not isinstance(tables, list) or not tables:
        result = dict(doc_json)
        result.pop("tables", None)
        result["paragraphs"] = paragraphs if isinstance(paragraphs, list) else []
        return result

    positioned: list[tuple[int, int, dict]] = []
    unpositioned_tables: list[dict] = []
    sequence = 0
    table_ranges: list[tuple[int, int]] = []
    for table in tables:
        if not isinstance(table, dict):
            continue
        start = _parse_int_like(table.get("paraIndex"))
        end = _parse_int_like(table.get("endParaIndex"))
        if start is not None and start >= 0:
            table_ranges.append((start, end if end is not None and end >= start else start))

    for paragraph in paragraphs:
        if not isinstance(paragraph, dict):
            continue
        para_index = _parse_int_like(paragraph.get("paraIndex"))
        if paragraph.get("inTable") is True or (
            para_index is not None and any(start <= para_index <= end for start, end in table_ranges)
        ):
            # The table block already represents these physical cell paragraphs.
            continue
        if para_index is None:
            # Paragraphs already arrive in document order. Use their sequence only when
            # the frontend omitted paraIndex; this never determines a table position.
            para_index = sequence
        positioned.append((para_index, 1, paragraph))
        sequence += 1

    for table in tables:
        if not isinstance(table, dict):
            continue
        para_index = _parse_int_like(table.get("paraIndex"))
        if para_index is None or para_index < 0:
            unpositioned_tables.append(table)
            continue
        positioned.append((para_index, 0, {"tables": [table]}))

    positioned.sort(key=lambda item: (item[0], item[1]))
    ordered_blocks = [item[2] for item in positioned]
    if unpositioned_tables:
        logger.warning(
            "[read_document] %s 个表格缺少有效 paraIndex，无法确定其段落位置，已附加到有序流末尾",
            len(unpositioned_tables),
        )
        ordered_blocks.extend({"tables": [table]} for table in unpositioned_tables)

    result = dict(doc_json)
    result.pop("tables", None)
    result["paragraphs"] = ordered_blocks
    return result


def _compact_doc_json(doc_json: dict) -> str:
    """Compact document JSON while preserving the ordered paragraph/table block stream."""
    ordered_doc = _order_document_blocks(doc_json)
    full = json.dumps(ordered_doc, ensure_ascii=False)
    if len(full) <= _MAX_DOC_JSON_CHARS:
        return full

    compact = {"paragraphs": [], "_compacted": True}
    for block in ordered_doc.get("paragraphs", []):
        if not isinstance(block, dict):
            continue
        if isinstance(block.get("tables"), list):
            compact_tables = []
            for table in block["tables"]:
                if not isinstance(table, dict):
                    continue
                table_compact = {
                    "paraIndex": table.get("paraIndex"),
                    "endParaIndex": table.get("endParaIndex"),
                }
                rows = []
                for row in table.get("cells", []):
                    cells = []
                    for cell in row:
                        if isinstance(cell, dict):
                            cell_text = cell.get("text", "")
                            if not cell_text and cell.get("paragraphs"):
                                cell_text = "".join(
                                    "".join(
                                        run.get("text", "") if isinstance(run, dict) else str(run)
                                        for run in paragraph.get("runs", [])
                                    )
                                    for paragraph in cell.get("paragraphs", [])
                                )
                            cells.append(cell_text)
                        else:
                            cells.append(str(cell))
                    rows.append(cells)
                table_compact["cellTexts"] = rows
                compact_tables.append(table_compact)
            if compact_tables:
                compact["paragraphs"].append({"tables": compact_tables})
            continue

        para_compact = {"paraIndex": block.get("paraIndex"), "paraID": block.get("paraID"), "runs": []}
        if block.get("pageStart") is not None and block.get("pageEnd") is not None:
            para_compact["pageStart"] = block["pageStart"]
            para_compact["pageEnd"] = block["pageEnd"]
        for r in block.get("runs", []):
            if isinstance(r, dict):
                if r.get("text") is not None:
                    para_compact["runs"].append({"text": r.get("text", ""), "rStyle": r.get("rStyle")})
                else:
                    img_info = {
                        k: v
                        for k, v in r.items()
                        if k
                        in (
                            "url",
                            "width",
                            "height",
                            "left",
                            "top",
                            "wrapType",
                            "altText",
                        )
                        and v is not None
                    }
                    if img_info:
                        para_compact["runs"].append(img_info)
        compact["paragraphs"].append(para_compact)

    for key in ("styles", "fields", "hasTOC", "tocFieldCode"):
        if key in ordered_doc and key != "styles":
            compact[key] = ordered_doc[key]

    result = json.dumps(compact, ensure_ascii=False)
    logger.info(f"[read_document] 📦 文档过大 ({len(full)} chars)，已精简为 {len(result)} chars（纯文本模式）")
    return result


# endregion


# region 工具实现（裸函数 + 工厂）


def _read_document_impl(
    startParaIndex: int | None,
    endParaIndex: int | None,
    startParaID: ParaIdInput,
    endParaID: ParaIdInput,
    docId: DocIdInput,
    mode: str = "full",
) -> str:
    """read_document 的核心逻辑，被工厂函数包裹后变成 LangChain @tool。"""
    resolved_doc_id = _normalize_doc_id(docId)
    read_mode = "lightweight" if mode == "lightweight" else "full"
    startParaID = _normalize_para_id(startParaID)
    endParaID = _normalize_para_id(endParaID)
    use_para_id_mode = startParaID is not None
    if use_para_id_mode and endParaID is None:
        endParaID = startParaID
    if not use_para_id_mode:
        if startParaIndex is None:
            startParaIndex = 0
        if endParaIndex is None:
            endParaIndex = startParaIndex

    if use_para_id_mode:
        range_desc = f"段落ID {startParaID} - {endParaID}"
    else:
        range_desc = f"段落索引 {startParaIndex} - {endParaIndex}"

    writer = get_stream_writer()
    if writer:
        writer(
            {
                "type": "read_document",
                "content": f"📑 正在读取文档（{range_desc}）",
                "startParaIndex": startParaIndex,
                "endParaIndex": endParaIndex,
                "startParaID": startParaID,
                "endParaID": endParaID,
                "docId": resolved_doc_id,
                "mode": read_mode,
            }
        )
    logger.info(
        "[read_document] 请求前端发送文档 "
        f"(startParaIndex={startParaIndex}, endParaIndex={endParaIndex}, "
        f"startParaID={startParaID}, endParaID={endParaID}, docId={resolved_doc_id}, mode={read_mode})"
    )

    chat_id = _current_chat_id.get(None)
    if is_stop_requested(chat_id):
        logger.info("[read_document] ⛔ 检测到停止请求，终止读取")
        return ""

    if chat_id:
        q = _pending_tool_requests.get(chat_id)
        if q:
            logger.debug(
                f"[read_document] WebSocket 模式，等待前端回传文档 (session={chat_id}, 队列现有 {q.qsize()} 条)"
            )
            loop = _pending_loops.get(chat_id)
            if loop:
                future = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(q.get(), timeout=60),
                    loop,
                )
                try:
                    result = future.result(timeout=65)
                    result_type = result.get("type", "?")
                    logger.debug(f"[read_document] 收到回传: type={result_type}, keys={list(result.keys())}")
                    if result_type == "stop" or result.get("error") == "stopped_by_user":
                        logger.info("[read_document] ⛔ 用户已停止，终止读取")
                        return ""
                    if result.get("error"):
                        err_msg = result.get("error")
                        logger.error(f"[read_document] ⚠️ 前端读取失败: {err_msg}")
                        if writer:
                            writer({"type": "status", "content": f"⚠️ 读取文档失败: {err_msg}"})
                        return ""
                    doc_json = result.get("documentJson", {})

                    def count_inline_images(doc):
                        count = 0
                        for p in doc.get("paragraphs", []):
                            for r in p.get("runs", []):
                                if isinstance(r, dict) and r.get("text") is None:
                                    count += 1
                        return count

                    image_count = count_inline_images(doc_json)
                    has_content = doc_json and (doc_json.get("paragraphs") or doc_json.get("tables"))
                    if has_content:
                        content_blocks = doc_json.get("paragraphs", [])
                        para_count = sum(
                            1
                            for block in content_blocks
                            if isinstance(block, dict) and not isinstance(block.get("tables"), list)
                        )
                        table_count = len(doc_json.get("tables", [])) + sum(
                            len(block.get("tables", []))
                            for block in content_blocks
                            if isinstance(block, dict) and isinstance(block.get("tables"), list)
                        )
                        logger.info(
                            f"[read_document] ✅ 收到文档，段落数: {para_count}，表格数: {table_count}，图片数: {image_count}"
                        )
                        if writer:
                            writer(
                                {
                                    "type": "read_complete",
                                    "content": f"📑 文档读取完成（{range_desc}）",
                                    "docId": resolved_doc_id,
                                }
                            )
                        return _compact_doc_json(doc_json)
                    logger.warning(
                        "[read_document] ⚠️ 收到空文档 "
                        f"(documentJson keys={list(doc_json.keys()) if isinstance(doc_json, dict) else type(doc_json).__name__})"
                    )
                    if writer:
                        writer({"type": "status", "content": "⚠️ 文档为空"})
                    return ""
                except (TimeoutError, concurrent.futures.TimeoutError):
                    logger.warning("[read_document] ⏰ 等待文档超时")
                    if writer:
                        writer({"type": "status", "content": "⏰ 等待文档超时"})
                    return ""
                except Exception as e:
                    logger.error(f"[read_document] ❌ 等待文档出错: {repr(e)}")
                    return ""
            else:
                logger.warning(f"[read_document] ⚠️ 找不到事件循环 (session={chat_id})")
        else:
            logger.warning(f"[read_document] ⚠️ 找不到等待队列 (session={chat_id})")

    logger.warning(f"[read_document] ⚠️ 非 WebSocket 模式，无法请求文档 (chat_id={chat_id})")
    return ""


def _generate_document_impl(document: DocumentOutput, docId: DocIdInput, insertParaID: RequiredParaIdInput) -> dict:
    """generate_document 的核心逻辑。"""
    resolved_doc_id = _normalize_doc_id(docId)
    normalized_insert_para_id = _normalize_para_id(insertParaID)
    if normalized_insert_para_id is None:
        raise ValueError(
            "generate_document requires insertParaID. Use 0 to insert at the document start, or use a real paraID from read_document/search_document to insert after that paragraph."
        )

    doc_dict = document.model_dump()
    _ensure_image_payload_shape(doc_dict)
    ordered_blocks = doc_dict.get("paragraphs", [])
    paragraph_blocks = [block for block in ordered_blocks if isinstance(block, dict) and "runs" in block]
    table_blocks = [block for block in ordered_blocks if isinstance(block, dict) and "tables" in block]
    para_count = len(paragraph_blocks)
    table_count = sum(len(block.get("tables", [])) for block in table_blocks)
    image_count = 0
    for p in paragraph_blocks:
        for r in p.get("runs", []):
            if isinstance(r, dict) and r.get("text") is None:
                image_count += 1

    generated_message = _format_generated_document_message(para_count, table_count, image_count)

    doc_dict["insertParaID"] = normalized_insert_para_id
    doc_dict["docId"] = resolved_doc_id

    writer = get_stream_writer()
    request_id = str(uuid.uuid4())
    frontend_result = None
    if writer:
        writer(
            {
                "type": "json",
                "content": doc_dict,
                "docId": resolved_doc_id,
                "requestId": request_id,
            }
        )
        frontend_result = _wait_for_frontend_mutation(request_id)

    stopped = bool(frontend_result) and (
        frontend_result.get("type") == "stop" or frontend_result.get("error") == "stopped_by_user"
    )
    frontend_error = frontend_result.get("error") if isinstance(frontend_result, dict) else None
    frontend_success = frontend_result.get("success") if isinstance(frontend_result, dict) else None
    last_paragraph = _normalize_frontend_paragraph_location(
        frontend_result.get("lastParagraph") if isinstance(frontend_result, dict) else None
    )

    result = {
        "success": False
        if stopped or frontend_success is False or frontend_error
        else (True if frontend_success is True else None),
        "docId": resolved_doc_id,
        "insertParaID": normalized_insert_para_id,
        "generated": {
            "paragraphCount": para_count,
            "tableCount": table_count,
            "imageCount": image_count,
        },
        "lastParagraph": last_paragraph,
        "requestId": request_id,
    }
    if stopped:
        result["error"] = "stopped_by_user"
    elif frontend_error:
        result["error"] = str(frontend_error)
    elif frontend_result is None:
        result["warning"] = (
            "Frontend response timed out or is unavailable. Do not repeat generate_document because the content may already be inserted; "
            "use read_document to locate the actual ending paragraph."
        )
    elif last_paragraph:
        result["meaning"] = (
            "lastParagraph is the final physical paragraph created by this generate_document call. "
            "Use lastParagraph.paraID as the next insertParaID when appending immediately after this generated block."
        )

    if writer:
        writer(
            {
                "type": "generate_complete",
                "content": generated_message,
                "docId": resolved_doc_id,
                "insertParaID": normalized_insert_para_id,
                "requestId": request_id,
            }
        )
    return result


def _search_document_impl(query: DocumentQuery, docId: DocIdInput) -> str:
    """search_document 的核心逻辑。"""
    resolved_doc_id = _normalize_doc_id(docId)

    query_dict = query.model_dump(exclude_none=True)
    query_type = query_dict.get("type", "run")
    filters = query_dict.get("filters", {})
    filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items())
    writer = get_stream_writer()
    if writer:
        writer(
            {
                "type": "search_document",
                "content": f"🔍 正在搜索文档: {filter_desc}",
                "query": query_dict,
                "docId": resolved_doc_id,
            }
        )
    logger.info(f"[search_document] 请求前端搜索文档 (type={query_type}, filters={filters}, docId={resolved_doc_id})")

    chat_id = _current_chat_id.get(None)
    if is_stop_requested(chat_id):
        logger.info("[search_document] ⛔ 检测到停止请求，终止搜索")
        return '{"matches": [], "matchCount": 0, "error": "stopped_by_user"}'

    if chat_id:
        q = _pending_tool_requests.get(chat_id)
        if q:
            logger.debug(f"[search_document] WebSocket 模式，等待前端回传查询结果 (session={chat_id})")
            loop = _pending_loops.get(chat_id)
            if loop:
                future = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(q.get(), timeout=30),
                    loop,
                )
                try:
                    result = future.result(timeout=35)
                    if result.get("type") == "stop" or result.get("error") == "stopped_by_user":
                        logger.info("[search_document] ⛔ 用户已停止，终止搜索")
                        return '{"matches": [], "matchCount": 0, "error": "stopped_by_user"}'
                    matches = result.get("matches", [])
                    match_count = result.get("matchCount", 0)

                    matched_para_indices: list[int] = []
                    matched_para_ids: list[int] = []
                    for m in matches:
                        if not isinstance(m, dict):
                            continue
                        para_idx = m.get("paragraphIndex")
                        para_id = m.get("paragraphId")
                        if isinstance(para_idx, int):
                            matched_para_indices.append(para_idx)
                        if isinstance(para_id, int):
                            matched_para_ids.append(para_id)
                    matched_para_indices = sorted(set(matched_para_indices))
                    if isinstance(result.get("matchedParaIDs"), list):
                        matched_para_ids.extend([pid for pid in result.get("matchedParaIDs") if isinstance(pid, int)])
                    matched_para_ids = sorted(set(matched_para_ids))

                    suggested_read_ranges: list[dict[str, int]] = []
                    seen_range_keys: set[tuple[str, int]] = set()
                    for m in matches:
                        if not isinstance(m, dict):
                            continue
                        para_id = m.get("paragraphId")
                        para_idx = m.get("paragraphIndex")
                        if isinstance(para_id, int):
                            key = ("id", para_id)
                            if key not in seen_range_keys:
                                suggested_read_ranges.append({"startParaID": para_id, "endParaID": para_id})
                                seen_range_keys.add(key)
                        elif isinstance(para_idx, int):
                            key = ("idx", para_idx)
                            if key not in seen_range_keys:
                                suggested_read_ranges.append({"startParaIndex": para_idx, "endParaIndex": para_idx})
                                seen_range_keys.add(key)
                        if len(suggested_read_ranges) >= 20:
                            break

                    if match_count > 0:
                        logger.info(
                            f"[search_document] ✅ 查询完成，匹配 {match_count} 项，"
                            f"涉及段落索引 {matched_para_indices}，段落ID {matched_para_ids}"
                        )
                        if writer:
                            writer(
                                {
                                    "type": "query_complete",
                                    "content": (f"✅ 搜索完成，找到 {match_count} 处匹配"),
                                    "docId": resolved_doc_id,
                                }
                            )
                        return json.dumps(
                            {
                                "matches": matches,
                                "matchCount": match_count,
                                "matchedParaIndices": matched_para_indices,
                                "matchedParaIDs": matched_para_ids,
                                "suggestedReadRanges": suggested_read_ranges,
                                "coverageAdvice": "When multiple candidates are found, read nearby context around each candidate in paragraph-index order, and stop early once evidence is sufficient.",
                            },
                            ensure_ascii=False,
                        )

                    logger.warning("[search_document] ⚠️ 未找到匹配项")
                    if writer:
                        writer(
                            {
                                "type": "query_complete",
                                "content": "⚠️ 未找到匹配内容，建议更换关键词重试",
                                "docId": resolved_doc_id,
                            }
                        )
                    return json.dumps(
                        {
                            "matches": [],
                            "matchCount": 0,
                            "matchedParaIndices": [],
                            "matchedParaIDs": [],
                            "suggestedReadRanges": [],
                            "triedQuery": query_dict,
                            "retryAdvice": "Try alternative keywords (synonyms, abbreviations, section names, core terms).",
                        },
                        ensure_ascii=False,
                    )
                except (TimeoutError, concurrent.futures.TimeoutError):
                    logger.warning("[search_document] ⏰ 等待查询结果超时")
                    if writer:
                        writer({"type": "status", "content": "⏰ 搜索超时", "docId": resolved_doc_id})
                    return '{"matches": [], "matchCount": 0, "error": "timeout"}'
                except Exception as e:
                    logger.error(f"[search_document] ❌ 等待查询结果出错: {e}")
                    return '{"matches": [], "matchCount": 0, "error": "' + str(e) + '"}'

    logger.warning("[search_document] ⚠️ 非 WebSocket 模式，无法执行查询")
    return '{"matches": [], "matchCount": 0, "error": "non-websocket"}'


def _delete_document_impl(paraIDs: list[int | str], docId: DocIdInput) -> dict:
    """delete_document 的核心逻辑。"""
    resolved_doc_id = _normalize_doc_id(docId)
    normalized_para_ids = [_normalize_para_id(pid) for pid in paraIDs]
    normalized_para_ids = [pid for pid in normalized_para_ids if pid is not None]
    deduped_para_ids = list(dict.fromkeys(normalized_para_ids))
    if not deduped_para_ids:
        return {
            "success": False,
            "requestedCount": 0,
            "deletedCount": 0,
            "error": "No valid paraIDs provided for deletion",
        }

    writer = get_stream_writer()
    request_id = str(uuid.uuid4())
    frontend_result = None
    if writer:
        writer(
            {
                "type": "delete_document",
                "content": f"🗑️ 正在删除 {len(deduped_para_ids)} 个段落",
                "paraIDs": deduped_para_ids,
                "docId": resolved_doc_id,
                "requestId": request_id,
            }
        )
        frontend_result = _wait_for_frontend_mutation(request_id)

    logger.info(f"[delete_document] 请求前端删除文档段落 (paraIDs={deduped_para_ids}, docId={resolved_doc_id})")
    stopped = bool(frontend_result) and (
        frontend_result.get("type") == "stop" or frontend_result.get("error") == "stopped_by_user"
    )
    frontend_error = frontend_result.get("error") if isinstance(frontend_result, dict) else None
    frontend_success = frontend_result.get("success") if isinstance(frontend_result, dict) else None
    deleted_count = _parse_int_like(frontend_result.get("deletedCount") if isinstance(frontend_result, dict) else None)
    missing_para_ids = frontend_result.get("missingParaIDs", []) if isinstance(frontend_result, dict) else []
    if not isinstance(missing_para_ids, list):
        missing_para_ids = []
    failed_para_ids = frontend_result.get("failedParaIDs", []) if isinstance(frontend_result, dict) else []
    if not isinstance(failed_para_ids, list):
        failed_para_ids = []
    replacement_insert_para_id = _normalize_para_id(
        frontend_result.get("replacementInsertParaID") if isinstance(frontend_result, dict) else None
    )

    result = {
        "success": False
        if stopped or frontend_success is False or frontend_error
        else (True if frontend_success is True else None),
        "docId": resolved_doc_id,
        "paraIDs": deduped_para_ids,
        "requestedCount": len(deduped_para_ids),
        "deletedCount": max(0, deleted_count or 0),
        "missingParaIDs": missing_para_ids,
        "failedParaIDs": failed_para_ids,
        "replacementInsertParaID": replacement_insert_para_id,
        "requestId": request_id,
    }
    if stopped:
        result["error"] = "stopped_by_user"
    elif frontend_error:
        result["error"] = str(frontend_error)
    elif frontend_result is None:
        result["warning"] = (
            "Frontend response timed out or is unavailable. Do not repeat the same delete blindly; "
            "read the document and retry only paragraph IDs that still exist."
        )

    if writer:
        if result["success"] is True:
            content = f"🗑️ 已删除 {result['deletedCount']} 个段落"
        elif result.get("error"):
            content = f"⚠️ 删除段落失败: {result['error']}"
        else:
            content = "⚠️ 删除结果未确认，请重新读取文档核对"
        writer(
            {
                "type": "delete_complete",
                "content": content,
                "docId": resolved_doc_id,
                "requestId": request_id,
                "deletedCount": result["deletedCount"],
            }
        )
    return result


_BREAK_TYPES = {
    "wdLineBreak": "仅换行（Shift+Enter）",
    "wdPageBreak": "分页，下一页继续且保持页面设置",
    "wdSectionBreakNextPage": "下一页分节，可独立设置页眉、页脚、页码和纸张方向",
}


def _insert_break_impl(paraID: RequiredParaIdInput, breakType: BreakType | str) -> dict:
    """在指定段落后插入换行、分页或下一页分节符。"""
    normalized_para_id = _normalize_para_id(paraID)
    if normalized_para_id is None:
        raise ValueError("insert_break requires a valid integer paraID")

    normalized_break_type = str(breakType or "").strip()
    if normalized_break_type not in _BREAK_TYPES:
        allowed = ", ".join(_BREAK_TYPES)
        raise ValueError(f"insert_break breakType must be one of: {allowed}")

    writer = get_stream_writer()
    request_id = str(uuid.uuid4())
    frontend_result = None
    if writer:
        writer(
            {
                "type": "insert_break",
                "paraID": normalized_para_id,
                "breakType": normalized_break_type,
                "content": f"↩️ 已在段落 {normalized_para_id} 后插入{_BREAK_TYPES[normalized_break_type]}",
                "requestId": request_id,
            }
        )
        frontend_result = _wait_for_frontend_mutation(request_id)
    logger.info(
        "[insert_break] 请求前端插入断行 (paraID=%s, breakType=%s)",
        normalized_para_id,
        normalized_break_type,
    )
    stopped = bool(frontend_result) and (
        frontend_result.get("type") == "stop" or frontend_result.get("error") == "stopped_by_user"
    )
    frontend_error = frontend_result.get("error") if isinstance(frontend_result, dict) else None
    frontend_success = frontend_result.get("success") if isinstance(frontend_result, dict) else None
    paragraph_after_break = _normalize_frontend_paragraph_location(
        frontend_result.get("paragraphAfterBreak") if isinstance(frontend_result, dict) else None
    )
    result = {
        "success": False
        if stopped or frontend_success is False or frontend_error
        else (True if frontend_success is True else None),
        "breakType": normalized_break_type,
        "sourceParaID": normalized_para_id,
        "paragraphAfterBreak": paragraph_after_break,
        "requestId": request_id,
    }
    if stopped:
        result["error"] = "stopped_by_user"
    elif frontend_error:
        result["error"] = str(frontend_error)
    elif frontend_result is None:
        result["warning"] = (
            "Frontend response timed out or is unavailable. Do not repeat insert_break because the break may already exist; "
            "use read_document to locate the paragraph after the break."
        )
    elif paragraph_after_break:
        result["newPage"] = paragraph_after_break.get("pageStart")
        result["meaning"] = (
            "paragraphAfterBreak identifies the paragraph immediately after the inserted break. "
            "Use paragraphAfterBreak.paraID as the insertion anchor for content that must continue after the break."
        )
    return result


def _create_document_impl() -> str:
    """请求前端创建并打开一个新的空白 DOCX 文档。"""
    writer = get_stream_writer()
    if writer:
        writer(
            {
                "type": "create_document",
                "format": "docx",
                "content": "📄 正在创建新的空白 DOCX 文档",
            }
        )
    logger.info("[create_document] 请求前端创建并打开新的空白 DOCX 文档")

    # 创建文档是异步的：如果后续紧接着调用 generate_document，必须等新文档
    # 真正打开后再继续，否则内容可能误写入原活动文档。
    chat_id = _current_chat_id.get(None)
    if chat_id:
        q = _pending_tool_requests.get(chat_id)
        loop = _pending_loops.get(chat_id)
        if q and loop:
            future = asyncio.run_coroutine_threadsafe(
                asyncio.wait_for(q.get(), timeout=60),
                loop,
            )
            try:
                result = future.result(timeout=65)
                if result.get("type") == "stop" or result.get("error") == "stopped_by_user":
                    return "Create document stopped by user"
                if result.get("success") is False or result.get("error"):
                    return (
                        f"Failed to create a new blank DOCX document: {result.get('error') or 'unknown frontend error'}"
                    )
                document_id = result.get("documentId")
                suffix = f" (documentId={document_id})" if document_id is not None else ""
                return f"New blank DOCX document created and opened{suffix}"
            except (TimeoutError, concurrent.futures.TimeoutError):
                logger.warning("[create_document] ⏰ 等待前端创建新文档超时")
                return "Frontend was notified to create a new blank DOCX document, but the frontend response timed out"
            except Exception as e:
                logger.error("[create_document] ❌ 等待前端创建结果失败: %s", e)

    return "Frontend notified to create and open a new blank DOCX document"


# endregion


# region 工厂函数：用 description 装配出 @tool


def build_read_document(description: str):
    """根据传入的 description 构造 read_document 工具实例。"""

    @tool(description=description)
    def read_document(
        startParaIndex: int | None = None,
        endParaIndex: int | None = None,
        startParaID: ParaIdInput = None,
        endParaID: ParaIdInput = None,
        docId: DocIdInput = 0,
        mode: str = "full",
    ) -> str:
        """Read document content. Requests the frontend to parse and return the specified paragraph range via WebSocket.

        Args:
            startParaIndex: Starting paragraph index (0-based), used in index mode.
            endParaIndex: Ending paragraph index (inclusive), used in index mode.
            startParaID: Starting paragraph ID (int-like, supports signed numeric strings), used in paraID mode.
            endParaID: Ending paragraph ID (int-like), used in paraID mode. Defaults to startParaID.
            docId: Document ID (int-like). Positive/negative are both allowed. 0 means current active document.
            mode: Read mode. "lightweight" reads paragraph text and IDs only. "full" reads text, styles, tables, images, and client-provided paragraph page ranges.
        """
        return _read_document_impl(startParaIndex, endParaIndex, startParaID, endParaID, docId, mode)

    return read_document


def build_generate_document(description: str):
    """根据传入的 description 构造 generate_document 工具实例。"""

    @tool(description=description)
    def generate_document(
        document: DocumentOutput,
        insertParaID: RequiredParaIdInput,
        docId: DocIdInput = 0,
    ) -> dict:
        """Generate a formatted document JSON for insertion into the Word document.

        Args:
            document: The document content to generate.
            insertParaID: Required insertion anchor. Use 0 to insert at the document start;
                a nonzero value inserts after the paragraph whose paraID equals that value.
            docId: Document ID (int-like). Positive/negative are both allowed. 0 means current active document.
        """
        return _generate_document_impl(document, docId, insertParaID)

    return generate_document


def build_search_document(description: str):
    """根据传入的 description 构造 search_document 工具实例。

    注意：工具名拼写为 search_document（历史遗留，与 LLM 提示一致，不修正）。
    """

    @tool(description=description)
    def search_document(query: DocumentQuery, docId: DocIdInput = 0) -> str:
        """Search document content. Requests the frontend to search for matching content by text or style criteria.

        Args:
            query: The search query with filters.
            docId: Document ID (int-like). Positive/negative are both allowed. 0 means current active document.
        """
        return _search_document_impl(query, docId)

    return search_document


def build_delete_document(description: str):
    """根据传入的 description 构造 delete_document 工具实例。"""

    @tool(description=description)
    def delete_document(paraIDs: list[int | str], docId: DocIdInput = 0) -> dict:
        """Delete specified paragraphs from the document by paraID list.

        Args:
            paraIDs: Paragraph IDs to delete (int-like list). Each paraID is deleted independently (not a range).
            docId: Document ID (int-like). Positive/negative are both allowed. 0 means current active document.
        """
        return _delete_document_impl(paraIDs, docId)

    return delete_document


def build_insert_break(description: str):
    """根据传入的 description 构造 insert_break 工具实例。"""

    @tool(description=description)
    def insert_break(paraID: RequiredParaIdInput, breakType: BreakType) -> str:
        """Insert a line, page, or next-page section break after a paragraph."""
        return _insert_break_impl(paraID, breakType)

    return insert_break


def build_create_document(description: str):
    """根据传入的 description 构造 create_document 工具实例。"""

    @tool(description=description)
    def create_document() -> str:
        """Create and open a new blank DOCX document in the active Word/WPS application."""
        return _create_document_impl()

    return create_document


# endregion


__all__ = [
    "build_read_document",
    "build_generate_document",
    "build_search_document",
    "build_delete_document",
    "build_insert_break",
    "build_create_document",
    # 内部实现也导出，便于子智能体或测试直接复用
    "_read_document_impl",
    "_generate_document_impl",
    "_search_document_impl",
    "_delete_document_impl",
    "_insert_break_impl",
    "_create_document_impl",
    "_compact_doc_json",
    "_order_document_blocks",
    "_ensure_image_payload_shape",
]
