"""Document tools for multi-agent (read, search, generate, delete)."""

import asyncio
import base64
import concurrent.futures
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from app.services.multi_agent.prompts import get_tool_description
from app.core.config import get_wence_data_dir
from .callback import _current_chat_id, _pending_loops, _pending_tool_requests, is_stop_requested
from .schemas import DocumentOutput, DocumentQuery


_MAX_DOC_JSON_CHARS = 100_000


def _parse_document_arg(document: str | dict | DocumentOutput) -> dict:
    """Parse the document argument into a dict, handling strings, dicts, and DocumentOutput instances."""
    if isinstance(document, DocumentOutput):
        doc_dict = document.model_dump()
    elif isinstance(document, dict):
        doc_dict = dict(document)
    elif isinstance(document, str):
        doc_raw = document.strip()
        if doc_raw.startswith("```"):
            lines = doc_raw.splitlines()
            if len(lines) >= 2:
                doc_raw = "\n".join(lines[1:-1]).strip()

        try:
            parsed = json.loads(doc_raw)
            if isinstance(parsed, dict):
                doc_dict = parsed
            else:
                raise ValueError(f"Expected dict, got {type(parsed).__name__}")
        except json.JSONDecodeError:
            try:
                import ast

                literal_val = ast.literal_eval(doc_raw)
                if isinstance(literal_val, dict):
                    doc_dict = literal_val
                else:
                    raise ValueError(f"Expected dict, got {type(literal_val).__name__}")
            except Exception:
                raise ValueError(f"Cannot parse document string as JSON: {doc_raw[:200]}")
    else:
        raise ValueError(f"document must be dict or string, got {type(document).__name__}")

    return DocumentOutput.model_validate(doc_dict).model_dump()


def _download_remote_image(url: str) -> str | None:
    """Download remote image URL to local wence_data/temp and return local path."""
    try:
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}:
            ext = ".png"

        temp_dir = get_wence_data_dir() / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
        file_path = temp_dir / filename

        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=20) as resp:
            file_path.write_bytes(resp.read())
        return str(file_path)
    except Exception as e:
        print(f"[generate_document] Image download failed: {e}")
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

        temp_dir = get_wence_data_dir() / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
        file_path = temp_dir / filename

        raw = base64.b64decode(match.group(2), validate=False)
        file_path.write_bytes(raw)
        return str(file_path)
    except Exception as e:
        print(f"[generate_document] Base64 image save failed: {e}")
        return None


def _ensure_image_payload_shape(doc_dict: dict) -> None:
    """Normalize inline image runs in paragraphs."""
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
            if run.get("text") is not None:
                continue

            run.setdefault("type", "inline")

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

            if not (run.get("tempPath") or run.get("sourcePath")) and run.get("url"):
                print(f"[generate_document] Image may fail to insert: url={run.get('url')}")


def _compact_doc_json(doc_json: dict) -> str:
    """Compact document JSON to LLM-handleable size."""
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
                        in ("url", "tempPath", "sourcePath", "width", "height", "left", "top", "wrapType", "altText")
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
    print(f"[read_document] Document too large ({len(full)} chars), compacted to {len(result)} chars")
    return result


@tool(description=get_tool_description("read_document"))
def read_document(startParaIndex: int = 0, endParaIndex: int = 49) -> str:
    """Read document content. Requests frontend to parse and return specified paragraph range via WebSocket."""
    writer = get_stream_writer()
    if writer:
        writer(
            {
                "type": "read_document",
                "content": f"📑 正在读取文档（段落 {startParaIndex} - {endParaIndex}）",
                "startParaIndex": startParaIndex,
                "endParaIndex": endParaIndex,
            }
        )
    print(
        f"[read_document] Requesting document from frontend (startParaIndex={startParaIndex}, endParaIndex={endParaIndex})"
    )

    chat_id = _current_chat_id.get(None)
    if is_stop_requested(chat_id):
        print("[read_document] ⛔ 检测到停止请求，终止读取")
        return ""

    if chat_id:
        q = _pending_tool_requests.get(chat_id)
        if q:
            print(f"[read_document] WebSocket 模式，等待前端回传文档 (session={chat_id})")

            loop = _pending_loops.get(chat_id)
            if loop:
                future = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(q.get(), timeout=60),
                    loop,
                )
                try:
                    result = future.result(timeout=65)
                    result_type = result.get("type", "?")
                    print(f"[read_document] 收到回传: type={result_type}")

                    if result_type == "stop" or result.get("error") == "stopped_by_user":
                        print("[read_document] ⛔ 用户已停止，终止读取")
                        return ""
                    if result.get("error"):
                        err_msg = result.get("error")
                        print(f"[read_document] 前端错误: {err_msg}")
                        if writer:
                            writer({"type": "status", "content": f"文档读取失败: {err_msg}"})
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
                        print(f"[read_document] ✅ 收到文档: {para_count} 段落, {table_count} 表格, {image_count} 图片")
                        if writer:
                            writer(
                                {
                                    "type": "read_complete",
                                    "content": f"📑 文档读取完成（段落 {startParaIndex} - {endParaIndex}）",
                                }
                            )
                        return _compact_doc_json(doc_json)

                    print(f"[read_document] ⚠️ 收到空文档")
                    if writer:
                        writer({"type": "status", "content": "⚠️ 文档为空"})
                    return ""

                except (TimeoutError, concurrent.futures.TimeoutError):
                    print("[read_document] ⏰ 等待文档超时")
                    if writer:
                        writer({"type": "status", "content": "⏰ 文档读取超时"})
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


@tool(description=get_tool_description("generate_document"))
def generate_document(document: str | dict) -> dict:
    """Generate formatted document JSON for Word insertion. Also sends json event via stream writer."""
    doc_dict = _parse_document_arg(document)
    _ensure_image_payload_shape(doc_dict)
    para_count = len(doc_dict.get("paragraphs", []))
    image_count = sum(
        1
        for p in doc_dict.get("paragraphs", [])
        for r in p.get("runs", [])
        if isinstance(r, dict) and r.get("text") is None
    )

    writer = get_stream_writer()
    if writer:
        writer(
            {
                "type": "json",
                "content": doc_dict,
            }
        )
        writer(
            {
                "type": "generate_complete",
                "content": f"文档已生成，共 {para_count} 个段落{f'，{image_count} 张图片' if image_count else ''}",
            }
        )
    return doc_dict


@tool(description=get_tool_description("search_document"))
def search_documnet(query: DocumentQuery) -> str:
    """Search document content by text or style conditions."""
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
            }
        )
    print(f"[search_documnet] 请求前端搜索文档 (type={query_type}, filters={filters})")

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

                    matched_para_indices = sorted(
                        set(
                            m.get("paragraphIndex")
                            for m in matches
                            if isinstance(m, dict) and isinstance(m.get("paragraphIndex"), int)
                        )
                    )
                    suggested_read_ranges = [
                        {"startParaIndex": idx, "endParaIndex": idx} for idx in matched_para_indices[:20]
                    ]

                    if match_count > 0:
                        print(
                            f"[search_documnet] ✅ 查询完成: {match_count} 匹配，涉及 {len(matched_para_indices)} 段落"
                        )
                        if writer:
                            writer(
                                {
                                    "type": "query_complete",
                                    "content": f"✅ 搜索完成，找到 {match_count} 处匹配",
                                }
                            )
                        return json.dumps(
                            {
                                "matches": matches,
                                "matchCount": match_count,
                                "matchedParaIndices": matched_para_indices,
                                "suggestedReadRanges": suggested_read_ranges,
                                "coverageAdvice": "命中多处候选时，按段落索引顺序读取附近内容，证据充分即可停止",
                            },
                            ensure_ascii=False,
                        )

                    print("[search_documnet] ⚠️ 未找到匹配项")
                    if writer:
                        writer({"type": "query_complete", "content": "⚠️ 未找到匹配内容，建议更换关键词"})
                    return json.dumps(
                        {
                            "matches": [],
                            "matchCount": 0,
                            "matchedParaIndices": [],
                            "suggestedReadRanges": [],
                            "triedQuery": query_dict,
                            "retryAdvice": "请更换关键词重试（同义词/简称/章节名/核心词）",
                        },
                        ensure_ascii=False,
                    )

                except (TimeoutError, concurrent.futures.TimeoutError):
                    print("[search_documnet] ⏰ 等待查询结果超时")
                    if writer:
                        writer({"type": "status", "content": "⏰ 搜索超时"})
                    return '{"matches": [], "matchCount": 0, "error": "timeout"}'
                except Exception as e:
                    print(f"[search_documnet] ❌ 等待查询结果出错: {e}")
                    return '{"matches": [], "matchCount": 0, "error": "' + str(e) + '"}'

    print("[search_documnet] ⚠️ 非 WebSocket 模式，无法执行查询")
    return '{"matches": [], "matchCount": 0, "error": "non-websocket"}'


@tool(description=get_tool_description("delete_document"))
def delete_document(startParaIndex: int = 0, endParaIndex: int = -1) -> str:
    """Mark document paragraphs for deletion (non-blocking, frontend handles confirmation)."""
    writer = get_stream_writer()
    if writer:
        writer(
            {
                "type": "delete_document",
                "content": f"🗑️ 准备删除文档段落（{startParaIndex} - {endParaIndex}）",
                "startParaIndex": startParaIndex,
                "endParaIndex": endParaIndex,
            }
        )
    print(f"[delete_document] 请求前端标记删除段落 (startParaIndex={startParaIndex}, endParaIndex={endParaIndex})")
    return f"已通知前端标记删除段落 {startParaIndex} - {endParaIndex}，等待用户确认"
