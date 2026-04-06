"""Document tools for the agent (read, search, generate, delete)."""

import asyncio
import concurrent.futures
import json
from datetime import datetime

from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from .callback import _current_chat_id, _pending_loops, _pending_tool_requests, is_stop_requested
from .schemas import DocumentOutput, DocumentQuery
from app.services.agent.prompts import get_tool_description
from app.core.config import get_wence_data_dir

# 返回给 LLM 的文档 JSON 最大字符数（超过则进入精简模式）
_MAX_DOC_JSON_CHARS = 80_000


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

    # 精简模式：只保留段落文本和索引
    compact = {"paragraphs": [], "_compacted": True}
    for p in doc_json.get("paragraphs", []):
        text = "".join(r.get("text", "") if isinstance(r, dict) else str(r) for r in p.get("runs", []))
        compact["paragraphs"].append({"paraIndex": p.get("paraIndex"), "text": text})

    # 保留表格文本信息
    if doc_json.get("tables"):
        compact["tables"] = []
        for t in doc_json["tables"]:
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
                        writer({"type": "status", "content": f"⚠️ 读取文档失败: {err_msg}"})
                        return ""
                    doc_json = result.get("documentJson", {})
                    has_content = doc_json and (doc_json.get("paragraphs") or doc_json.get("tables"))
                    if has_content:
                        para_count = len(doc_json.get("paragraphs", []))
                        table_count = len(doc_json.get("tables", []))
                        print(f"[read_document] ✅ 收到文档，段落数: {para_count}，表格数: {table_count}")
                        writer(
                            {
                                "type": "read_complete",
                                "content": f"✅ 文档读取完成（段落 {startParaIndex} - {endParaIndex}）",
                            }
                        )
                        return _compact_doc_json(doc_json)
                    print(
                        "[read_document] ⚠️ 收到空文档 "
                        f"(documentJson keys={list(doc_json.keys()) if isinstance(doc_json, dict) else type(doc_json).__name__})"
                    )
                    writer({"type": "status", "content": "⚠️ 文档为空"})
                    return ""
                except (TimeoutError, concurrent.futures.TimeoutError):
                    print("[read_document] ⏰ 等待文档超时")
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
    writer = get_stream_writer()
    doc_dict = document.model_dump()
    para_count = len(doc_dict.get("paragraphs", []))
    saved_path = _save_generated_document_json(doc_dict)

    if saved_path:
        writer(
            {
                "type": "status",
                "content": f"💾 生成 JSON 已保存: {saved_path}",
            }
        )
    writer({"type": "generate_complete", "content": f"✅ 文档已生成，共 {para_count} 个段落"})
    return doc_dict


@tool(description=get_tool_description("search_document"))
def search_documnet(query: DocumentQuery) -> str:
    """Search document content — search for matching content in the frontend document by text or style criteria."""
    writer = get_stream_writer()

    query_dict = query.model_dump(exclude_none=True)
    query_type = query_dict.get("type", "run")
    filters = query_dict.get("filters", {})
    filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items())
    writer(
        {
            "type": "search_documnet",
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
