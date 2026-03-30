"""单智能体文档相关工具（读、查、编）。"""

import asyncio
import concurrent.futures
import json

from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from .callback import _current_chat_id, _pending_loops, _pending_tool_requests, is_stop_requested
from .schemas import DocumentOutput, DocumentQuery

# 返回给 LLM 的文档 JSON 最大字符数（超过则精简样式信息，仅保留文本）
_MAX_DOC_JSON_CHARS = 80_000


def _compact_doc_json(doc_json: dict) -> str:
    """将文档 JSON 压缩到 LLM 可处理的大小。"""
    full = json.dumps(doc_json, ensure_ascii=False, separators=(",", ":"))
    if len(full) <= _MAX_DOC_JSON_CHARS:
        return full

    # 精简模式：只保留段落文本和索引
    compact = {"paragraphs": [], "_compacted": True}
    for p in doc_json.get("paragraphs", []):
        text = "".join(r.get("text", "") if isinstance(r, dict) else str(r) for r in p.get("runs", []))
        compact["paragraphs"].append({"paraIndex": p.get("paraIndex"), "text": text})

    # 保留表格的文本信息
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

    result = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    print(f"[read_document] 📦 文档过大({len(full)} chars)，已精简为 {len(result)} chars（纯文本模式）")
    return result


@tool
def read_document(startParaIndex: int = 0, endParaIndex: int = 49) -> str:
    """读取文档内容。通过 WebSocket 请求前端解析指定范围的文档并返回。"""
    writer = get_stream_writer()
    writer(
        {
            "type": "read_document",
            "content": f"📑 正在读取文档(段落 {startParaIndex} - {endParaIndex})",
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
                                "content": f"✅ 文档读取完成(段落 {startParaIndex} - {endParaIndex})",
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


@tool
def edit_document(
    document: DocumentOutput | None = None,
    startParaIndex: int | None = None,
    endParaIndex: int | None = None,
    deleteRanges: list[dict] | None = None,
) -> dict | str:
    """编辑文档：支持离散删除区间、按 paraIndex 插入内容，或先删后插（同一次调用）。"""
    writer = get_stream_writer()

    has_insert = document is not None

    normalized_delete_ranges: list[dict[str, int]] = []

    if deleteRanges:
        if not isinstance(deleteRanges, list):
            return "错误: deleteRanges 必须是数组，元素形如 {startParaIndex, endParaIndex}"
        for idx, r in enumerate(deleteRanges):
            if not isinstance(r, dict):
                return f"错误: deleteRanges[{idx}] 必须是对象"
            s = r.get("startParaIndex")
            e = r.get("endParaIndex", s)
            if not isinstance(s, int) or not isinstance(e, int):
                return f"错误: deleteRanges[{idx}] 的 startParaIndex/endParaIndex 必须是整数"
            normalized_delete_ranges.append({"startParaIndex": s, "endParaIndex": e})

    if startParaIndex is not None or endParaIndex is not None:
        if startParaIndex is None:
            return "错误: 使用 startParaIndex/endParaIndex 时必须提供 startParaIndex"
        final_end = endParaIndex if endParaIndex is not None else startParaIndex
        if not isinstance(final_end, int):
            return "错误: endParaIndex 必须是整数"
        normalized_delete_ranges.append({"startParaIndex": startParaIndex, "endParaIndex": final_end})

    has_delete = len(normalized_delete_ranges) > 0

    if not has_insert and not has_delete:
        return "错误: edit_document 至少需要提供 document 或删除参数(startParaIndex/endParaIndex/deleteRanges)"

    delete_start = normalized_delete_ranges[0]["startParaIndex"] if has_delete else None
    delete_end = normalized_delete_ranges[0]["endParaIndex"] if has_delete else None

    status_payload = {
        "type": "edit_document",
        "hasDelete": bool(has_delete),
        "hasInsert": bool(has_insert),
    }
    if has_delete:
        status_payload["deleteRanges"] = normalized_delete_ranges
        status_payload.update(
            {
                "content": (
                    f"✏️ 正在编辑文档（删除 {len(normalized_delete_ranges)} 个区间）"
                    if len(normalized_delete_ranges) > 1
                    else f"✏️ 正在编辑文档（删除段落 {delete_start} - {delete_end}）"
                ),
                "startParaIndex": delete_start,
                "endParaIndex": delete_end,
            }
        )
    else:
        status_payload["content"] = "✏️ 正在编辑文档（插入新内容）"
    writer(status_payload)

    if not has_insert:
        writer({"type": "edit_complete", "content": "✅ 已标记待删除段落，等待用户确认"})
        print(f"[edit_document] 请求前端删除文档段落区间: {normalized_delete_ranges}")
        return {
            "action": "delete_only",
            "deleteRanges": normalized_delete_ranges,
            "startParaIndex": delete_start,
            "endParaIndex": delete_end,
            "message": (
                f"已通知前端标记删除 {len(normalized_delete_ranges)} 个区间，等待用户确认"
                if len(normalized_delete_ranges) > 1
                else f"已通知前端标记删除段落 {delete_start} - {delete_end}，等待用户确认"
            ),
        }

    doc_dict = document.model_dump()
    paragraphs = doc_dict.get("paragraphs", [])
    missing_para_index = [i for i, p in enumerate(paragraphs) if not isinstance(p.get("paraIndex"), int)]
    if missing_para_index:
        preview = ", ".join(str(i) for i in missing_para_index[:10])
        return f"错误: edit_document 插入内容时每个段落都必须提供 paraIndex。缺失 paraIndex 的段落序号: {preview}"

    para_count = len(paragraphs)
    doc_dict["paragraphs"] = sorted(paragraphs, key=lambda p: p.get("paraIndex", -1))
    # insertParaIndex 为兼容字段，paraIndex 模式下不再使用
    doc_dict.pop("insertParaIndex", None)

    if has_delete:
        print(
            "[edit_document] 请求前端执行删改 "
            f"(deleteRanges={normalized_delete_ranges}, paraIndices={[p.get('paraIndex') for p in doc_dict.get('paragraphs', [])]})"
        )
    else:
        print(
            f"[edit_document] 请求前端插入文档 (paraIndices={[p.get('paraIndex') for p in doc_dict.get('paragraphs', [])]})"
        )
    writer({"type": "json", "content": doc_dict})
    writer({"type": "edit_complete", "content": f"✅ 文档编辑完成，共 {para_count} 个段落"})
    return doc_dict


@tool
def search_documnet(query: DocumentQuery) -> str:
    """搜索文档内容 - 在前端文档中按文本或样式条件搜索匹配内容。"""
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
                                "coverageAdvice": "若命中多处候选，按段落索引顺序逐个读取候选段落附近内容；证据充分即可停止",
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
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
                            "retryAdvice": "请更换关键词重试（同义词/简称/章节名/核心词）",
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
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
