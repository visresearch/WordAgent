"""共享文档工具实现（read / search / generate / delete）。

这里只放纯逻辑函数 + "工厂函数"。每个 agent 模式（agent / multi_agent）
通过传入自己的 `description` 字符串拿到一份装好 `@tool` 的副本，从而复用
所有实现，但又能让 LLM 看到不同模式下定制的 prompt 描述。
"""

from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import importlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from app.core.config import get_temp_dir, get_wence_data_dir, get_wence_project_dir

from .callback import (
    _current_chat_id,
    _current_request_context,
    _pending_loops,
    _pending_tool_requests,
    is_stop_requested,
)
from .schemas import DocumentOutput, DocumentQuery


# 返回给 LLM 的文档 JSON 最大字符数（超过则进入精简模式）
_MAX_DOC_JSON_CHARS = 100_000
DocIdInput = str | int | None


def _normalize_doc_id(doc_id: DocIdInput) -> str | None:
    """Normalize docId from tool input / frontend metadata to string form."""
    if doc_id is None:
        return None
    if isinstance(doc_id, str):
        cleaned = doc_id.strip()
        return cleaned or None
    return str(doc_id)


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
        print(f"[generate_document] ⚠️ 下载图片失败: {e}")
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
        print(f"[generate_document] ⚠️ 保存 base64 图片失败: {e}")
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
    """Normalize inline image runs in paragraphs: download URLs, resolve data images."""
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

            # 优先标准化已有本地路径（兼容 sourcePath/tempPath 传相对路径）
            raw_temp_path = str(run.get("tempPath") or "").strip()
            raw_source_path = str(run.get("sourcePath") or "").strip()
            existing_temp = _resolve_local_image_path(raw_temp_path)
            existing_source = _resolve_local_image_path(raw_source_path)
            if existing_temp:
                run["tempPath"] = existing_temp
            elif raw_temp_path:
                run.pop("tempPath", None)
            if existing_source:
                run["sourcePath"] = existing_source
                # 如果只有 sourcePath，补一个 tempPath 让前端优先拿绝对本地路径
                run.setdefault("tempPath", existing_source)
            elif raw_source_path:
                run.pop("sourcePath", None)

            # 下载远程图片、解码 data: 图片，或解析本地路径图片
            if not (run.get("tempPath") or run.get("sourcePath")):
                url = str(run.get("url") or "").strip()
                if url.startswith("data:image/"):
                    local_path = _save_data_image(url)
                    if local_path:
                        run["tempPath"] = local_path
                elif url.startswith("http://") or url.startswith("https://"):
                    local_path = _download_remote_image(url)
                    if local_path:
                        run["tempPath"] = local_path
                elif url:
                    local_path = _resolve_local_image_path(url)
                    if local_path:
                        run["tempPath"] = local_path

            if not (run.get("tempPath") or run.get("sourcePath")) and run.get("url"):
                print(f"[generate_document] ⚠️ 图片未获取到本地路径，可能插入失败: url={run.get('url')}")

            # 若宽高缺失，则按原图尺寸/比例补齐，避免拉伸变形
            width_value = _to_positive_float(run.get("width"))
            height_value = _to_positive_float(run.get("height"))
            has_width = width_value is not None
            has_height = height_value is not None
            if has_width and has_height:
                continue
            local_image_path = (
                _resolve_local_image_path(str(run.get("tempPath") or ""))
                or _resolve_local_image_path(str(run.get("sourcePath") or ""))
                or _resolve_local_image_path(str(run.get("url") or ""))
            )
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
        print(f"[generate_document] ⚠️ 保存 JSON 文件失败: {e}")
        return None


def _get_active_doc_id() -> str | None:
    """从请求上下文中获取当前活动文档的 documentId。"""
    ctx = _current_request_context.get(None)
    if not ctx:
        return None
    document_meta = ctx.get("document_meta")
    if not document_meta:
        return None
    if isinstance(document_meta, list):
        if document_meta:
            if isinstance(document_meta[0], dict):
                return _normalize_doc_id(document_meta[0].get("documentId"))
            return None
    elif isinstance(document_meta, dict):
        return _normalize_doc_id(document_meta.get("documentId"))
    return None


def _compact_doc_json(doc_json: dict) -> str:
    """Compact document JSON to a size the LLM can handle."""
    full = json.dumps(doc_json, ensure_ascii=False)
    if len(full) <= _MAX_DOC_JSON_CHARS:
        return full

    compact = {"paragraphs": [], "_compacted": True}
    for p in doc_json.get("paragraphs", []):
        if not isinstance(p, dict):
            continue
        para_compact = {"paraIndex": p.get("paraIndex"), "runs": []}
        for r in p.get("runs", []):
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
                            "tempPath",
                            "sourcePath",
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

    if doc_json.get("tables"):
        compact["tables"] = []
        for t in doc_json.get("tables", []):
            if not isinstance(t, dict):
                continue
            table_compact = {
                "paraIndex": t.get("paraIndex"),
                "endParaIndex": t.get("endParaIndex"),
            }
            rows = []
            for row in t.get("cells", []):
                cells = []
                for cell in row:
                    if isinstance(cell, dict):
                        cell_text = cell.get("text", "")
                        if not cell_text and cell.get("paragraphs"):
                            cell_text = "".join(
                                "".join(
                                    r.get("text", "") if isinstance(r, dict) else str(r) for r in cp.get("runs", [])
                                )
                                for cp in cell.get("paragraphs", [])
                            )
                        cells.append(cell_text)
                    else:
                        cells.append(str(cell))
                rows.append(cells)
            table_compact["cellTexts"] = rows
            compact["tables"].append(table_compact)

    result = json.dumps(compact, ensure_ascii=False)
    print(f"[read_document] 📦 文档过大 ({len(full)} chars)，已精简为 {len(result)} chars（纯文本模式）")
    return result


# endregion


# region 工具实现（裸函数 + 工厂）


def _read_document_impl(startParaIndex: int, endParaIndex: int, docId: DocIdInput) -> str:
    """read_document 的核心逻辑，被工厂函数包裹后变成 LangChain @tool。"""
    resolved_doc_id = _normalize_doc_id(docId)
    if resolved_doc_id is None:
        resolved_doc_id = _get_active_doc_id()

    writer = get_stream_writer()
    if writer:
        writer(
            {
                "type": "read_document",
                "content": f"📑 正在读取文档（段落 {startParaIndex} - {endParaIndex}）",
                "startParaIndex": startParaIndex,
                "endParaIndex": endParaIndex,
                "docId": resolved_doc_id,
            }
        )
    print(
        f"[read_document] 请求前端发送文档 (startParaIndex={startParaIndex}, endParaIndex={endParaIndex}, docId={resolved_doc_id})"
    )

    chat_id = _current_chat_id.get(None)
    if is_stop_requested(chat_id):
        print("[read_document] ⛔ 检测到停止请求，终止读取")
        return ""

    if chat_id:
        q = _pending_tool_requests.get(chat_id)
        if q:
            print(f"[read_document] WebSocket 模式，等待前端回传文档 (session={chat_id}, 队列现有 {q.qsize()} 条)")
            loop = _pending_loops.get(chat_id)
            if loop:
                future = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(q.get(), timeout=60),
                    loop,
                )
                try:
                    result = future.result(timeout=65)
                    result_type = result.get("type", "?")
                    print(f"[read_document] 收到回传: type={result_type}, keys={list(result.keys())}")
                    if result_type == "stop" or result.get("error") == "stopped_by_user":
                        print("[read_document] ⛔ 用户已停止，终止读取")
                        return ""
                    if result.get("error"):
                        err_msg = result.get("error")
                        print(f"[read_document] ⚠️ 前端读取失败: {err_msg}")
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
                        para_count = len(doc_json.get("paragraphs", []))
                        table_count = len(doc_json.get("tables", []))
                        print(
                            f"[read_document] ✅ 收到文档，段落数: {para_count}，表格数: {table_count}，图片数: {image_count}"
                        )
                        if writer:
                            writer(
                                {
                                    "type": "read_complete",
                                    "content": f"📑 文档读取完成（段落 {startParaIndex} - {endParaIndex}）",
                                    "docId": resolved_doc_id,
                                }
                            )
                        return _compact_doc_json(doc_json)
                    print(
                        "[read_document] ⚠️ 收到空文档 "
                        f"(documentJson keys={list(doc_json.keys()) if isinstance(doc_json, dict) else type(doc_json).__name__})"
                    )
                    if writer:
                        writer({"type": "status", "content": "⚠️ 文档为空"})
                    return ""
                except (TimeoutError, concurrent.futures.TimeoutError):
                    print("[read_document] ⏰ 等待文档超时")
                    if writer:
                        writer({"type": "status", "content": "⏰ 等待文档超时"})
                    return ""
                except Exception as e:
                    print(f"[read_document] ❌ 等待文档出错: {repr(e)}")
                    return ""
            else:
                print(f"[read_document] ⚠️ 找不到事件循环 (session={chat_id})")
        else:
            print(f"[read_document] ⚠️ 找不到等待队列 (session={chat_id})")

    print(f"[read_document] ⚠️ 非 WebSocket 模式，无法请求文档 (chat_id={chat_id})")
    return ""


def _generate_document_impl(document: DocumentOutput, docId: DocIdInput, insertParaIndex: int) -> dict:
    """generate_document 的核心逻辑。"""
    resolved_doc_id = _normalize_doc_id(docId)
    if resolved_doc_id is None:
        resolved_doc_id = _get_active_doc_id()

    doc_dict = document.model_dump()
    _ensure_image_payload_shape(doc_dict)
    para_count = len(doc_dict.get("paragraphs", []))
    image_count = 0
    for p in doc_dict.get("paragraphs", []):
        for r in p.get("runs", []):
            if isinstance(r, dict) and r.get("text") is None:
                image_count += 1

    doc_dict["insertParaIndex"] = insertParaIndex
    doc_dict["docId"] = resolved_doc_id

    writer = get_stream_writer()
    if writer:
        writer(
            {
                "type": "json",
                "content": doc_dict,
                "docId": resolved_doc_id,
            }
        )
        writer(
            {
                "type": "generate_complete",
                "content": f"📝 文档已生成，共 {para_count} 个段落{f'，{image_count} 张图片' if image_count else ''}",
                "docId": resolved_doc_id,
            }
        )
    return doc_dict


def _search_document_impl(query: DocumentQuery, docId: DocIdInput) -> str:
    """search_documnet 的核心逻辑。"""
    resolved_doc_id = _normalize_doc_id(docId)
    if resolved_doc_id is None:
        resolved_doc_id = _get_active_doc_id()

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
    print(f"[search_documnet] 请求前端搜索文档 (type={query_type}, filters={filters}, docId={resolved_doc_id})")

    chat_id = _current_chat_id.get(None)
    if is_stop_requested(chat_id):
        print("[search_documnet] ⛔ 检测到停止请求，终止搜索")
        return '{"matches": [], "matchCount": 0, "error": "stopped_by_user"}'

    if chat_id:
        q = _pending_tool_requests.get(chat_id)
        if q:
            print(f"[search_documnet] WebSocket 模式，等待前端回传查询结果 (session={chat_id})")
            loop = _pending_loops.get(chat_id)
            if loop:
                future = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(q.get(), timeout=30),
                    loop,
                )
                try:
                    result = future.result(timeout=35)
                    if result.get("type") == "stop" or result.get("error") == "stopped_by_user":
                        print("[search_documnet] ⛔ 用户已停止，终止搜索")
                        return '{"matches": [], "matchCount": 0, "error": "stopped_by_user"}'
                    matches = result.get("matches", [])
                    match_count = result.get("matchCount", 0)

                    matched_para_indices: list[int] = []
                    for m in matches:
                        if not isinstance(m, dict):
                            continue
                        para_idx = m.get("paragraphIndex")
                        if isinstance(para_idx, int):
                            matched_para_indices.append(para_idx)
                    matched_para_indices = sorted(set(matched_para_indices))
                    suggested_read_ranges = [
                        {"startParaIndex": idx, "endParaIndex": idx} for idx in matched_para_indices[:20]
                    ]

                    if match_count > 0:
                        print(f"[search_documnet] ✅ 查询完成，匹配 {match_count} 项，涉及段落 {matched_para_indices}")
                        if writer:
                            writer(
                                {
                                    "type": "query_complete",
                                    "content": f"✅ 搜索完成，找到 {match_count} 处匹配（涉及 {len(matched_para_indices)} 个段落）",
                                    "docId": resolved_doc_id,
                                }
                            )
                        return json.dumps(
                            {
                                "matches": matches,
                                "matchCount": match_count,
                                "matchedParaIndices": matched_para_indices,
                                "suggestedReadRanges": suggested_read_ranges,
                                "coverageAdvice": "When multiple candidates are found, read nearby context around each candidate in paragraph-index order, and stop early once evidence is sufficient.",
                            },
                            ensure_ascii=False,
                        )

                    print("[search_documnet] ⚠️ 未找到匹配项")
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
                            "suggestedReadRanges": [],
                            "triedQuery": query_dict,
                            "retryAdvice": "Try alternative keywords (synonyms, abbreviations, section names, core terms).",
                        },
                        ensure_ascii=False,
                    )
                except (TimeoutError, concurrent.futures.TimeoutError):
                    print("[search_documnet] ⏰ 等待查询结果超时")
                    if writer:
                        writer({"type": "status", "content": "⏰ 搜索超时", "docId": resolved_doc_id})
                    return '{"matches": [], "matchCount": 0, "error": "timeout"}'
                except Exception as e:
                    print(f"[search_documnet] ❌ 等待查询结果出错: {e}")
                    return '{"matches": [], "matchCount": 0, "error": "' + str(e) + '"}'

    print("[search_documnet] ⚠️ 非 WebSocket 模式，无法执行查询")
    return '{"matches": [], "matchCount": 0, "error": "non-websocket"}'


def _delete_document_impl(startParaIndex: int, endParaIndex: int, docId: DocIdInput) -> str:
    """delete_document 的核心逻辑。"""
    resolved_doc_id = _normalize_doc_id(docId)
    if resolved_doc_id is None:
        resolved_doc_id = _get_active_doc_id()

    writer = get_stream_writer()
    if writer:
        writer(
            {
                "type": "delete_document",
                "content": f"🗑️ 准备删除文档段落（{startParaIndex} - {endParaIndex}）",
                "startParaIndex": startParaIndex,
                "endParaIndex": endParaIndex,
                "docId": resolved_doc_id,
            }
        )
    print(
        f"[delete_document] 请求前端删除文档段落 (startParaIndex={startParaIndex}, endParaIndex={endParaIndex}, docId={resolved_doc_id})"
    )
    return f"Frontend notified to mark paragraphs {startParaIndex} - {endParaIndex} for deletion, awaiting user confirmation"


# endregion


# region 工厂函数：用 description 装配出 @tool


def build_read_document(description: str):
    """根据传入的 description 构造 read_document 工具实例。"""

    @tool(description=description)
    def read_document(startParaIndex: int = 0, endParaIndex: int = 49, docId: str | int | None = None) -> str:
        """Read document content. Requests the frontend to parse and return the specified paragraph range via WebSocket.

        Args:
            startParaIndex: Starting paragraph index (0-based).
            endParaIndex: Ending paragraph index (inclusive).
            docId: Document ID (string or integer). If None, reads the active document.
        """
        return _read_document_impl(startParaIndex, endParaIndex, docId)

    return read_document


def build_generate_document(description: str):
    """根据传入的 description 构造 generate_document 工具实例。"""

    @tool(description=description)
    def generate_document(
        document: DocumentOutput,
        docId: str | int | None = None,
        insertParaIndex: int = -1,
    ) -> dict:
        """Generate a formatted document JSON for insertion into the Word document.

        Args:
            document: The document content to generate.
            docId: Document ID (string or integer) to insert into. If None, uses the active document.
            insertParaIndex: 0-based paragraph index where content will be inserted before.
                Use -1 for end of document, 0 for beginning.
        """
        return _generate_document_impl(document, docId, insertParaIndex)

    return generate_document


def build_search_document(description: str):
    """根据传入的 description 构造 search_documnet 工具实例。

    注意：工具名拼写为 search_documnet（历史遗留，与 LLM 提示一致，不修正）。
    """

    @tool(description=description)
    def search_documnet(query: DocumentQuery, docId: str | int | None = None) -> str:
        """Search document content. Requests the frontend to search for matching content by text or style criteria.

        Args:
            query: The search query with filters.
            docId: Document ID (string or integer) to search in. If None, uses the active document.
        """
        return _search_document_impl(query, docId)

    return search_documnet


def build_delete_document(description: str):
    """根据传入的 description 构造 delete_document 工具实例。"""

    @tool(description=description)
    def delete_document(startParaIndex: int = 0, endParaIndex: int = -1, docId: str | int | None = None) -> str:
        """Delete a specified range of paragraphs from the document.

        Args:
            startParaIndex: Starting paragraph index (0-based).
            endParaIndex: Ending paragraph index (inclusive), -1 for the last paragraph.
            docId: Document ID (string or integer) to delete from. If None, uses the active document.
        """
        return _delete_document_impl(startParaIndex, endParaIndex, docId)

    return delete_document


# endregion


__all__ = [
    "build_read_document",
    "build_generate_document",
    "build_search_document",
    "build_delete_document",
    # 内部实现也导出，便于子智能体或测试直接复用
    "_read_document_impl",
    "_generate_document_impl",
    "_search_document_impl",
    "_delete_document_impl",
    "_get_active_doc_id",
    "_compact_doc_json",
    "_ensure_image_payload_shape",
]
