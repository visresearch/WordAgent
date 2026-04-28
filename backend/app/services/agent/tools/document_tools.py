"""Document tools for the agent (read, search, generate, delete)."""

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
from typing import Any

from .callback import _current_chat_id, _pending_loops, _pending_tool_requests, is_stop_requested
from .schemas import DocumentOutput, DocumentQuery
from app.services.agent.prompts import get_tool_description
from app.core.config import get_wence_data_dir

# 返回给 LLM 的文档 JSON 最大字符数（超过则进入精简模式）
_MAX_DOC_JSON_CHARS = 100_000


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

        temp_dir = get_wence_data_dir() / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
        file_path = temp_dir / filename

        raw = base64.b64decode(match.group(2), validate=False)
        file_path.write_bytes(raw)
        return str(file_path)
    except Exception as e:
        print(f"[generate_document] ⚠️ 保存 base64 图片失败: {e}")
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
            # Skip text runs
            if run.get("text") is not None:
                continue

            # This is an image run (no text field)
            run.setdefault("type", "inline")

            # Download remote images or decode data images
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
                print(f"[generate_document] ⚠️ 图片未获取到本地路径，可能插入失败: url={run.get('url')}")


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


def _compact_doc_json(doc_json: dict) -> str:
    """Compact document JSON to a size the LLM can handle."""
    full = json.dumps(doc_json, ensure_ascii=False)
    if len(full) <= _MAX_DOC_JSON_CHARS:
        return full

    # 精简模式：保留段落文本和图片信息（inline image runs）
    compact = {"paragraphs": [], "_compacted": True}
    for p in doc_json.get("paragraphs", []):
        if not isinstance(p, dict):
            continue
        para_compact = {"paraIndex": p.get("paraIndex"), "runs": []}
        for r in p.get("runs", []):
            if isinstance(r, dict):
                # 文本 run: 只保留核心文本
                if r.get("text") is not None:
                    para_compact["runs"].append({"text": r.get("text", ""), "rStyle": r.get("rStyle")})
                # 图片 run: 保留完整信息
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

    # 保留表格文本信息
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


@tool(description=get_tool_description("read_document"))
def read_document(startParaIndex: int = 0, endParaIndex: int = 49) -> str:
    """Read document content. Requests the frontend to parse and return the specified paragraph range via WebSocket."""
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
    print(f"[read_document] 请求前端发送文档 (startParaIndex={startParaIndex}, endParaIndex={endParaIndex})")

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
                    result_keys = list(result.keys())
                    print(f"[read_document] 收到回传: type={result_type}, keys={result_keys}")
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

                    # 统计 inline image runs（图片在 paragraphs[].runs[] 中，没有 text 字段的 run）
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


@tool(description=get_tool_description("generate_document"))
def generate_document(document: DocumentOutput) -> dict:
    """Generate a formatted document JSON for insertion into the Word document."""
    doc_dict = document.model_dump()
    _ensure_image_payload_shape(doc_dict)
    para_count = len(doc_dict.get("paragraphs", []))
    # 统计 inline image runs
    image_count = 0
    for p in doc_dict.get("paragraphs", []):
        for r in p.get("runs", []):
            if isinstance(r, dict) and r.get("text") is None:
                image_count += 1

    writer = get_stream_writer()
    if writer:
        writer(
            {
                "type": "generate_complete",
                "content": f"📝 文档已生成，共 {para_count} 个段落{f'，{image_count} 张图片' if image_count else ''}",
            }
        )
    return doc_dict


@tool(description=get_tool_description("search_document"))
def search_documnet(query: DocumentQuery) -> str:
    """Search document content. Requests the frontend to search for matching content by text or style criteria."""
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
                        writer({"type": "query_complete", "content": "⚠️ 未找到匹配内容，建议更换关键词重试"})
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
                        writer({"type": "status", "content": "⏰ 搜索超时"})
                    return '{"matches": [], "matchCount": 0, "error": "timeout"}'
                except Exception as e:
                    print(f"[search_documnet] ❌ 等待查询结果出错: {e}")
                    return '{"matches": [], "matchCount": 0, "error": "' + str(e) + '"}'

    print("[search_documnet] ⚠️ 非 WebSocket 模式，无法执行查询")
    return '{"matches": [], "matchCount": 0, "error": "non-websocket"}'


@tool(description=get_tool_description("delete_document"))
def delete_document(startParaIndex: int = 0, endParaIndex: int = -1) -> str:
    """Delete a specified range of paragraphs from the document."""
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
    print(f"[delete_document] 请求前端删除文档段落 (startParaIndex={startParaIndex}, endParaIndex={endParaIndex})")
    return f"Frontend notified to mark paragraphs {startParaIndex} - {endParaIndex} for deletion, awaiting user confirmation"
