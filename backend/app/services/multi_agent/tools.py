"""
工具定义 - Agent 可调用的工具、文档 Schema 和工具回调等待机制
"""

import asyncio
import concurrent.futures
import contextvars
import json

from typing import Literal

from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field, model_validator

# ============== 工具回调等待机制 ==============
# 用于 WebSocket 模式下，agent 调用 tool 后等待前端回传结果

# 存储每个会话的等待队列：{chat_id: asyncio.Queue}
_pending_tool_requests: dict[str, asyncio.Queue] = {}
# 存储每个会话的事件循环引用（供 tool 在同步线程中回到异步）
_pending_loops: dict[str, asyncio.AbstractEventLoop] = {}
# 存储每个会话的停止状态（用户点击停止后置为 True）
_stop_requested_sessions: set[str] = set()
# 当前线程使用的 chat_id（通过 contextvars 传递到 tool 函数中）
_current_chat_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("_current_chat_id", default=None)


def create_tool_request(chat_id: str) -> asyncio.Queue:
    """为一个会话创建等待队列"""
    q = asyncio.Queue()
    _pending_tool_requests[chat_id] = q
    _stop_requested_sessions.discard(chat_id)
    return q


def register_loop(chat_id: str, loop: asyncio.AbstractEventLoop):
    """注册会话使用的事件循环（供 tool 函数中跨线程调用）"""
    _pending_loops[chat_id] = loop


def cleanup_tool_request(chat_id: str):
    """清理会话的等待队列"""
    _pending_tool_requests.pop(chat_id, None)
    _pending_loops.pop(chat_id, None)
    _stop_requested_sessions.discard(chat_id)


def request_stop(chat_id: str):
    """标记会话停止，并唤醒可能正在等待前端回传的工具调用。"""
    _stop_requested_sessions.add(chat_id)
    q = _pending_tool_requests.get(chat_id)
    loop = _pending_loops.get(chat_id)
    if q and loop:
        try:
            asyncio.run_coroutine_threadsafe(q.put({"type": "stop", "error": "stopped_by_user"}), loop)
        except Exception:
            pass


def clear_stop(chat_id: str):
    """清除会话停止标记（用于下一次新请求）。"""
    _stop_requested_sessions.discard(chat_id)


def is_stop_requested(chat_id: str | None) -> bool:
    """判断会话是否收到停止请求。"""
    return bool(chat_id) and chat_id in _stop_requested_sessions


async def submit_tool_response(chat_id: str, data: dict):
    """前端通过 WebSocket 回传工具结果时调用"""
    if is_stop_requested(chat_id):
        # 停止后忽略迟到的工具回包，避免再次唤醒 agent 流程
        print(f"[ToolCallback] ⛔ 忽略回传（已停止）session={chat_id}")
        return
    q = _pending_tool_requests.get(chat_id)
    if q:
        data_type = data.get("type", "?") if isinstance(data, dict) else type(data).__name__
        print(f"[ToolCallback] ✅ 放入队列 session={chat_id}, type={data_type}, 队列大小={q.qsize() + 1}")
        await q.put(data)
    else:
        print(f"[ToolCallback] ⚠️ 找不到 session {chat_id} 的等待队列")


# region Tools Schema

# 样式数组索引常量（与前端 docxJsonConverter.js 保持一致）
# pStyle: [alignment, lineSpacing(磅), indentLeft(磅), indentRight(磅), indentFirstLine(磅), spaceBefore(磅), spaceAfter(磅), styleName, lineSpacingRule]
# rStyle: [fontName, fontSize, bold, italic, underline, underlineColor, color, highlight, strikethrough, superscript, subscript]
# cStyle: [rowSpan, colSpan, alignment, verticalAlignment]
# tStyle: [tableAlignment]
#
# 新版 JSON 仅支持样式引用写法：
# - pStyle/rStyle/cStyle/tStyle 必须为字符串引用（如 "pS_1"、"rS_1"）
# - 顶层 styles 字典必须提供对应样式数组定义


class Run(BaseModel):
    """格式块 - 一段具有相同格式的文字"""

    text: str = Field(description="文字内容")
    rStyle: str = Field(description='字符样式引用ID，如 "rS_1"，对应 document.styles["rS_1"]')


class Paragraph(BaseModel):
    """段落 - 每行内容独立为一个段落，禁止在 text 中使用 \\n 换行。runs 为空数组时表示空段落"""

    pStyle: str = Field(
        description='段落样式引用ID，如 "pS_1"，对应 document.styles["pS_1"]。空段落时可省略', default=""
    )
    runs: list[Run] = Field(
        description="格式块数组。一个段落可包含多个 run（不同格式的文字拆为不同 run）。"
        "禁止在 text 中使用 \\n 换行，换行必须新建段落。空段落时为空数组。",
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_empty_paragraph_shape(self):
        """runs 为空时视为空段落，空段落要求 pStyle 为空字符串。"""
        if not self.runs and self.pStyle != "":
            raise ValueError("空段落（runs 为空数组）要求 pStyle 为空字符串")
        return self


class Cell(BaseModel):
    """表格单元格"""

    text: str = Field(description="单元格文本")
    cStyle: str = Field(description='单元格样式引用ID，如 "cS_1"，对应 document.styles["cS_1"]')


class Table(BaseModel):
    """表格"""

    rows: int = Field(description="行数")
    columns: int = Field(description="列数")
    cells: list[list[Cell]] = Field(description="单元格二维数组")
    tStyle: str = Field(description='表格样式引用ID，如 "tS_1"，对应 document.styles["tS_1"]')


class DocumentOutput(BaseModel):
    """文档输出结构。paragraphs 和 tables 是两个独立的顶级字段，不要混合。"""

    paragraphs: list[Paragraph] = Field(description="段落数组，每个元素必须是 Paragraph 对象，不要放字符串")
    tables: list[Table] = Field(default_factory=list, description="表格数组，每个元素必须是 Table 对象")
    styles: dict[str, list] = Field(
        description="样式字典（必填）。key 为引用ID（如 pS_1、rS_1、cS_1、tS_1），value 为样式数组。"
        "必须包含所有 pStyle/rStyle/cStyle/tStyle 引用到的样式定义。\n"
        "pStyle 数组格式: [对齐, 行距, 左缩进, 右缩进, 首行缩进, 段前, 段后, 样式名, 行距规则]。"
        "对齐: left/center/right/justify; "
        "行距: 磅值(points)，仅在行距规则=3/4/5时生效(规则0/1/2为预设档位，WPS忽略此字段)，以12pt字号为例：单倍=12,1.5倍=18,双倍=24; "
        "左缩进/右缩进/首行缩进: 磅值，每个中文字符≈12磅，2字符缩进=24，0=无缩进; "
        "段前/段后: 磅值，如12=约1行，0=无间距; "
        "样式名: 如'正文','标题 1','标题 2'等; "
        "行距规则(WPS常量): 0=单倍行距,1=1.5倍行距,2=双倍行距,3=至少,4=固定值,5=多倍行距。"
        "注意：规则0/1/2为预设档位(WPS自动计算行距，忽略行距字段)；规则3/4/5使用行距字段的磅值；普通文档推荐用行距规则=3(至少)配合明确的磅值。\n"
        "rStyle 数组格式: [字体, 字号, 粗体, 斜体, 下划线, 下划线颜色, 颜色, 高亮, 删除线, 上标, 下标]。"
        "字体: 如'宋体','Times New Roman'; 字号: 磅值; 粗体/斜体: bool; "
        "下划线: 0=无,1=单线,3=双线,4=虚线,6=粗线,11=波浪线; "
        "下划线颜色/颜色: #RRGGBB格式; "
        "高亮: 0=无,1=黑,2=蓝,3=青绿,4=鲜绿,5=粉红,6=红,7=黄,9=深蓝,10=青,11=绿,12=紫罗兰,13=深红,14=深黄,15=深灰,16=浅灰; "
        "删除线/上标/下标: bool。\n"
        "cStyle 数组格式: [rowSpan, colSpan, alignment, verticalAlignment]。"
        "rowSpan/colSpan: 合并行/列数; alignment: 同pStyle; verticalAlignment: 0=顶端,1=居中,2=底端。\n"
        "tStyle 数组格式: [tableAlignment]。tableAlignment: 0=左对齐,1=居中,2=右对齐。"
    )
    insertParaIndex: int = Field(
        default=-1,
        description="插入位置（段落索引，0-based），前端会在该段落之前插入生成的内容。"
        "如果用户选中了文档范围，应设为该范围的 startParaIndex；"
        "如果是新建内容无特定位置，设为 -1（文档末尾）或 0（文档开头）。",
    )

    @model_validator(mode="before")
    @classmethod
    def filter_invalid_paragraphs(cls, data):
        """过滤 paragraphs 中的非法项。"""
        if isinstance(data, dict) and "paragraphs" in data:
            cleaned = []
            for p in data["paragraphs"]:
                if isinstance(p, Paragraph):
                    cleaned.append(p)
                elif isinstance(p, dict):
                    # 跳过没有 runs 的非法段落
                    if "runs" not in p:
                        continue
                    cleaned.append(p)
                # 跳过字符串等非法类型
            data["paragraphs"] = cleaned
        return data

    @model_validator(mode="after")
    def validate_style_references(self):
        """校验样式引用必须存在于 styles 字典中。"""
        style_keys = set(self.styles.keys())
        missing: set[str] = set()

        for para in self.paragraphs:
            if not para.runs:
                continue
            if para.pStyle not in style_keys:
                missing.add(para.pStyle)
            for run in para.runs:
                if run.rStyle not in style_keys:
                    missing.add(run.rStyle)

        for table in self.tables:
            if table.tStyle not in style_keys:
                missing.add(table.tStyle)
            for row in table.cells:
                for cell in row:
                    if cell.cStyle not in style_keys:
                        missing.add(cell.cStyle)

        if missing:
            refs = ", ".join(sorted(missing))
            raise ValueError(f"styles 缺少引用定义: {refs}")
        return self


class RangeFilter(BaseModel):
    """数值范围筛选，用于 fontSize、lineSpacing 等字段"""

    gt: float | None = Field(default=None, description="大于")
    lt: float | None = Field(default=None, description="小于")
    gte: float | None = Field(default=None, description="大于等于")
    lte: float | None = Field(default=None, description="小于等于")


class QueryFilter(BaseModel):
    """查询筛选条件，所有字段为 AND 关系。只需填写需要筛选的字段，其余留空。"""

    # 文本匹配
    text: str | None = Field(
        default=None, description="文本包含匹配（run 级别匹配 run.text；paragraph 级别拼接所有 runs 的 text）"
    )

    # Run 级别样式（type=run 时直接匹配；type=paragraph 时检查段落中是否存在匹配的 run）
    fontName: str | None = Field(default=None, description="字体名，精确匹配，如 '宋体'、'楷体'、'Times New Roman'")
    fontSize: float | RangeFilter | None = Field(
        default=None, description="字号。精确值如 14；或范围如 {gt: 14}、{gte: 14, lte: 18}"
    )
    bold: bool | None = Field(default=None, description="粗体")
    italic: bool | None = Field(default=None, description="斜体")
    underline: int | None = Field(default=None, description="下划线: 0=无, 1=单线, 3=双线, 4=虚线, 6=粗线, 11=波浪线")
    color: str | None = Field(default=None, description="字体颜色 #RRGGBB 格式，如 '#FF0000' 为红色")
    highlight: int | None = Field(
        default=None, description="高亮色: 0=无, 1=黑, 2=蓝, 3=青绿, 4=鲜绿, 5=粉红, 6=红, 7=黄"
    )
    strikethrough: bool | None = Field(default=None, description="删除线")
    superscript: bool | None = Field(default=None, description="上标")
    subscript: bool | None = Field(default=None, description="下标")

    # Paragraph 级别样式（仅 type=paragraph 时有效）
    alignment: str | None = Field(default=None, description="段落对齐: left/center/right/justify")
    styleName: str | None = Field(
        default=None, description="段落样式名，包含匹配（如 '标题' 可匹配 '标题 1'、'标题 2'）"
    )
    lineSpacing: float | RangeFilter | None = Field(
        default=None, description="行距（磅值）。单倍=12, 1.5倍=18, 双倍=24；精确值如 18；或范围如 {gt: 18}"
    )


class DocumentQuery(BaseModel):
    """文档查询 DSL"""

    type: Literal["run", "paragraph"] = Field(
        default="run",
        description="搜索粒度：run=格式块级别（精确到同一格式的文字片段），paragraph=段落级别",
    )
    filters: QueryFilter = Field(description="筛选条件，所有字段为 AND 关系，只填需要的字段")


# ============== 文档大小限制 ==============
# 返回给 LLM 的文档 JSON 最大字符数（超过则精简样式信息，仅保留文本）
_MAX_DOC_JSON_CHARS = 80_000


def _compact_doc_json(doc_json: dict) -> str:
    """将文档 JSON 压缩到 LLM 可处理的大小。
    如果完整 JSON 超出限制，去掉样式数组只保留文本内容和段落索引。"""
    full = json.dumps(doc_json, ensure_ascii=False)
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
            rows = []
            for row in t.get("rows", []):
                cells = []
                for cell in row.get("cells", []):
                    cell_text = "".join(
                        "".join(r.get("text", "") if isinstance(r, dict) else str(r) for r in cp.get("runs", []))
                        for cp in cell.get("paragraphs", [])
                    )
                    cells.append(cell_text)
                rows.append(cells)
            compact["tables"].append({"tableIndex": t.get("tableIndex"), "rows": rows})
    result = json.dumps(compact, ensure_ascii=False)
    print(f"[read_document] 📦 文档过大({len(full)} chars)，已精简为 {len(result)} chars（纯文本模式）")
    return result


# region Tools 定义


@tool
def read_document(startParaIndex: int = 0, endParaIndex: int = 49) -> str:
    """
    读取文档内容。通过 WebSocket 请求前端解析指定范围的文档并返回。

    Args:
        startParaIndex: 起始段落索引（0-based）。0 表示从文档开头开始。
        endParaIndex: 结束段落索引（0-based）。-1 表示到文档结尾。

    ❗❗ 重要：禁止使用 endParaIndex=-1 一次性读取全文！文档可能有几百个段落，一次读取会超出上下文限制。
    必须分段读取，每次最多 50 个段落：
    - 第1次: read_document(0, 49)
    - 第2次: read_document(50, 99)
    - 第3次: read_document(100, 149)
    - ...(直到返回的段落数 < 50 说明已读到末尾)

    【调用场景】
    1. 读取全文（分段读取）：
       - 用户说"润色全文" -> read_document(0,49), read_document(50,99), ...
       - 用户说"看看这篇文档" -> 分段读取
       - 用户说"总结文档内容" -> 分段读取

    2. 读取指定范围：
       - 当用户选中了部分内容并要求操作时
       - 当需要读取文档特定段落范围的内容时

    3. 任何需要文档内容但 documentJson 为空或没有 paragraphs 的情况

    Returns:
        文档 JSON 字符串（包含 paragraphs 等），或空字符串
    """
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

    # 检查是否在 WebSocket 会话中（有 chat_id）
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
                    if doc_json and doc_json.get("paragraphs"):
                        print(f"[read_document] ✅ 收到文档，段落数: {len(doc_json['paragraphs'])}")
                        writer(
                            {
                                "type": "read_complete",
                                "content": f"✅ 文档读取完成(段落 {startParaIndex} - {endParaIndex})",
                            }
                        )
                        return _compact_doc_json(doc_json)
                    else:
                        print(
                            f"[read_document] ⚠️ 收到空文档 (documentJson keys={list(doc_json.keys()) if isinstance(doc_json, dict) else type(doc_json).__name__})"
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

    # 非 WebSocket 模式（无 chat_id），无法双向通信获取文档
    print(f"[read_document] ⚠️ 非 WebSocket 模式，无法请求文档 (chat_id={chat_id})")
    return ""


@tool
def generate_document(document: DocumentOutput) -> dict:
    """
    生成带格式的文档 JSON，用于插入到 Word 文档。

    【最小改动原则 - 最高优先级】
    输出内容会被**插入**到文档的 insertParaIndex 位置，不会替换整个文档。
    因此必须**只输出需要变动的段落**，不要输出原文中未改动的部分，否则会导致内容重复！
    - 增加内容：只输出新增的段落
    - 修改/润色某个范围：先调用 delete_document 删除旧段落，再调用本工具插入新段落
    - 创建全新文档：输出完整文档内容

    【重要】修改已有内容时必须配合 delete_document！
    流程：delete_document(删旧段落) -> generate_document(插新段落)
    否则旧内容会残留在文档中。

    【重要】格式属性必须100%原样复制！
    除非用户明确要求修改格式，否则所有格式属性（fontName, fontSize, alignment 等）必须与原文档完全一致。

    【结构要求】document 包含以下字段：
    - paragraphs: Paragraph 对象的数组（只包含新增或被修改的段落）
    - tables: Table 对象的数组（可选）
    - styles: 样式字典（必填，且必须覆盖所有样式引用）
    - insertParaIndex: 插入位置（段落索引，0-based），前端在该段落之前插入内容
    不要把 "tables" 字符串放进 paragraphs 数组里！

    【insertParaIndex 规则】
    - 增加内容时：insertParaIndex = 要插入到的段落索引位置（在该段落之前插入）
    - 修改/润色用户选中内容时：insertParaIndex = 用户选区的 startParaIndex
    - 新建内容无特定位置时：insertParaIndex = -1（文档末尾）或 0（文档开头）

    Args:
        document: 文档结构，包含 paragraphs、tables 和 insertParaIndex

    Returns:
        文档 JSON 对象
    """
    writer = get_stream_writer()
    doc_dict = document.model_dump()
    para_count = len(doc_dict.get("paragraphs", []))
    writer({"type": "generate_complete", "content": f"✅ 文档已生成，共 {para_count} 个段落"})

    # # 保存生成的文档 JSON 到 example 文件夹
    # try:
    #     from datetime import datetime
    #     from pathlib import Path

    #     example_dir = Path(__file__).resolve().parent.parent.parent.parent / "example"
    #     example_dir.mkdir(exist_ok=True)
    #     filename = f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    #     (example_dir / filename).write_text(json.dumps(doc_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    #     print(f"[generate_document] 已保存到 example/{filename}")
    # except Exception as e:
    #     print(f"[generate_document] 保存 JSON 失败: {e}")

    return doc_dict


@tool
def query_document(query: DocumentQuery) -> str:
    """
    搜索文档内容 - 在前端文档中按文本或样式条件搜索匹配内容。

    【调用场景】
    - 用户说"找到红色的字": type=run, filters={color: "#FF0000"}
    - 用户说"加粗的楷体文字": type=run, filters={bold: true, fontName: "楷体"}
    - 用户说"所有标题": type=paragraph, filters={styleName: "标题"}
    - 用户说"字号大于14的文字": type=run, filters={fontSize: {gt: 14}}
    - 用户说"搜索关键词xxx": type=run, filters={text: "xxx"}
    - 用户说"找到实习目的": type=run, filters={text: "实习目的"}

    【JSON 结构说明】
    文档中 paragraph 没有顶层 text 字段，文本通过 runs[].text 拼接获得。
    标题通过 pStyle[7]（styleName）识别，如 "标题 1"。
    type=paragraph 时也可使用 run 样式 filter，会检查段落中是否存在匹配的 run。

    【返回值说明】
    返回 JSON 字符串，包含 matches 列表，每项含：
    - text: 匹配的文本内容
    - paragraphIndex: 段落索引（唯一定位字段）
    根据 paragraphIndex 可进一步调用 read_document 读取完整段落。

    【未命中重试】
    若返回 matchCount=0，不应立即放弃。应更换关键词继续查询（同义词/近义词、缩短核心词、章节名词）至少 1-2 次，
    仅在多次查询仍无结果时再告知用户未找到。

    Args:
        query: 查询条件，包含搜索粒度 type 和筛选条件 filters

    Returns:
        匹配结果 JSON 字符串
    """
    writer = get_stream_writer()

    query_dict = query.model_dump(exclude_none=True)
    query_type = query_dict.get("type", "run")
    filters = query_dict.get("filters", {})
    filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items())
    writer(
        {
            "type": "query_document",
            "content": f"🔍 正在搜索文档: {filter_desc}",
            "query": query_dict,
        }
    )
    print(f"[query_document] 请求前端搜索文档 (type={query_type}, filters={filters})")

    # 通过 WebSocket 回调等待前端查询结果
    chat_id = _current_chat_id.get(None)
    if is_stop_requested(chat_id):
        print("[query_document] ⛔ 检测到停止请求，终止搜索")
        return '{"matches": [], "matchCount": 0, "error": "stopped_by_user"}'

    if chat_id:
        q = _pending_tool_requests.get(chat_id)
        if q:
            print(f"[query_document] WebSocket 模式，等待前端回传查询结果 (session={chat_id})")

            loop = _pending_loops.get(chat_id)
            if loop:
                future = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(q.get(), timeout=30),
                    loop,
                )
                try:
                    result = future.result(timeout=35)
                    if result.get("type") == "stop" or result.get("error") == "stopped_by_user":
                        print("[query_document] ⛔ 用户已停止，终止搜索")
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
                        print(f"[query_document] ✅ 查询完成，匹配 {match_count} 项，涉及段落 {matched_para_indices}")
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
                        )
                    else:
                        print("[query_document] ⚠️ 未找到匹配项")
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
                        )
                except (TimeoutError, concurrent.futures.TimeoutError):
                    print("[query_document] ⏰ 等待查询结果超时")
                    writer({"type": "status", "content": "⏰ 搜索超时"})
                    return '{"matches": [], "matchCount": 0, "error": "timeout"}'
                except Exception as e:
                    print(f"[query_document] ❌ 等待查询结果出错: {e}")
                    return '{"matches": [], "matchCount": 0, "error": "' + str(e) + '"}'

    # 非 WebSocket 模式
    print("[query_document] ⚠️ 非 WebSocket 模式，无法执行查询")
    return '{"matches": [], "matchCount": 0, "error": "non-websocket"}'


@tool
def web_fetch(url: str) -> str:
    """
    拓取网页内容 - 根据 URL 获取网页正文，自动清洗 HTML 标签、脚本、样式等。

    【调用场景】
    - 用户提供了一个 URL，希望你读取其内容
    - 需要参考网页内容来回答问题或写作
    - 配合 web_search 获取搜索结果后深入读取具体页面

    Args:
        url: 目标网页 URL（必须以 http:// 或 https:// 开头）

    Returns:
        网页正文内容（纯文本），最多返回 8000 字符
    """
    from curl_cffi import requests as curl_requests
    from bs4 import BeautifulSoup
    from app.services.llm_client import get_httpx_proxy_url

    writer = get_stream_writer()
    writer({"type": "status", "content": f"🌐 正在拓取网页: {url}"})
    print(f"[web_fetch] 开始拓取: {url}")

    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": origin + "/",
            "Cache-Control": "max-age=0",
        }
        proxy_url = get_httpx_proxy_url()
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

        # 使用 Session 维持 Cookie，应对知乎等需要 Cookie 的网站
        session = curl_requests.Session(impersonate="chrome131")
        if proxies:
            session.proxies = proxies
        session.verify = False

        resp = session.get(url, headers=headers, timeout=20, allow_redirects=True)

        # 403 时尝试先访问首页获取 Cookie 再重试
        if resp.status_code == 403:
            print(f"[web_fetch] 收到 403，尝试预热 Cookie: {origin}")
            session.get(origin, headers=headers, timeout=10, allow_redirects=True)
            resp = session.get(url, headers=headers, timeout=20, allow_redirects=True)

        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            # 非 HTML 内容，直接返回截断的文本
            text = resp.text[:8000]
            print(f"[web_fetch] ✅ 非 HTML 内容，直接返回 {len(text)} 字符")
            return text

        soup = BeautifulSoup(resp.text, "lxml")

        # 移除无关元素
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe", "svg"]):
            tag.decompose()

        # 尝试提取正文区域
        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.find(attrs={"role": "main"})
            or soup.find(
                "div",
                class_=lambda c: c
                and any(
                    k in (c if isinstance(c, str) else " ".join(c))
                    for k in ["content", "article", "post", "entry", "main"]
                ),
            )
        )

        target = main_content if main_content else soup.body if soup.body else soup

        # 提取文本，保留基本结构
        lines = []
        for elem in target.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "blockquote", "pre", "code"]
        ):
            text = elem.get_text(strip=True)
            if not text:
                continue
            tag_name = elem.name
            if tag_name.startswith("h"):
                level = tag_name[1]
                lines.append(f"{'#' * int(level)} {text}")
            elif tag_name == "li":
                lines.append(f"- {text}")
            elif tag_name in ("pre", "code"):
                lines.append(f"```\n{text}\n```")
            elif tag_name == "blockquote":
                lines.append(f"> {text}")
            else:
                lines.append(text)

        result = "\n\n".join(lines)

        # 如果结构化提取结果太少，回退到 get_text
        if len(result) < 100:
            result = target.get_text(separator="\n", strip=True)

        # 截断
        if len(result) > 8000:
            result = result[:8000] + "\n\n[内容已截断，原文过长]"

        # 添加标题
        title = soup.title.get_text(strip=True) if soup.title else ""
        if title:
            result = f"标题: {title}\n\n{result}"

        print(f"[web_fetch] ✅ 已拓取 {len(result)} 字符")
        writer({"type": "status", "content": "✅ 网页拓取完成"})
        return result

    except curl_requests.errors.RequestsError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        print(f"[web_fetch] ❌ 拓取失败: HTTP {status or e}")
        writer({"type": "status", "content": f"❌ 该网页无法访问，跳过"})
        return "该网页无法访问（已跳过）。请直接使用已有的搜索摘要继续完成任务，不要因此放弃生成文档。"
    except Exception as e:
        print(f"[web_fetch] ❌ 拓取失败: {e}")
        writer({"type": "status", "content": f"❌ 该网页无法访问，跳过"})
        return "该网页无法访问（已跳过）。请直接使用已有的搜索摘要继续完成任务，不要因此放弃生成文档。"


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    网络搜索 - 使用 Bing 搜索引擎检索信息。

    【调用场景】
    - 用户要求查找某个主题的最新信息
    - 需要参考资料来写作或回答问题
    - 用户明确要求“搜索”、“查一下”、“上网找”等

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数（默认 5）

    Returns:
        搜索结果摘要，包含标题、链接和摘要
    """
    from curl_cffi import requests as curl_requests
    from bs4 import BeautifulSoup
    from app.services.llm_client import get_httpx_proxy_url

    writer = get_stream_writer()
    writer({"type": "status", "content": f"🔎 正在搜索: {query}"})
    print(f"[web_search] 开始搜索: {query}")

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        proxy_url = get_httpx_proxy_url()
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        # 有代理时用国际版 bing（代理出口通常在海外，cn.bing.com 可能异常）
        bing_url = "https://www.bing.com/search" if proxy_url else "https://cn.bing.com/search"
        params = {"q": query, "count": str(max_results * 2)}

        resp = curl_requests.get(
            bing_url,
            params=params,
            headers=headers,
            impersonate="chrome131",
            timeout=15,
            allow_redirects=True,
            proxies=proxies,
            verify=False,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        results = []
        for item in soup.select("li.b_algo"):
            if len(results) >= max_results:
                break

            title_elem = item.select_one("h2 a")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            href = title_elem.get("href", "")

            snippet_elem = item.select_one(".b_caption p") or item.select_one("p")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            if title and href:
                results.append({"title": title, "href": href, "snippet": snippet})

        if not results:
            msg = f"未找到与 '{query}' 相关的搜索结果"
            print(f"[web_search] ⚠️ {msg}")
            writer({"type": "status", "content": f"⚠️ {msg}"})
            return msg

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"{i}. [{r['title']}]({r['href']})\n   {r['snippet']}")

        output = f"搜索关键词: {query}\n结果数: {len(results)}\n\n" + "\n\n".join(formatted)

        print(f"[web_search] ✅ 找到 {len(results)} 条结果")
        writer({"type": "status", "content": f"✅ 搜索完成，找到 {len(results)} 条结果"})
        return output

    except Exception as e:
        msg = f"搜索失败: {e}"
        print(f"[web_search] ❌ {msg}")
        writer({"type": "status", "content": f"❌ {msg}"})
        return msg


# @tool
# def comment_document(comment: str, startPos: int = -1, endPos: int = -1) -> str:
#     """
#     在文档指定位置添加评论。

#     Args:
#         comment: 评论内容
#         startPos: 文档起始位置（字符位置），-1 表示文档开头
#         endPos: 文档结束位置（字符位置），-1 表示文档结尾

#     Returns:
#         添加评论的确认字符串
#     """
#     writer = get_stream_writer()
#     writer({"type": "comment_document", "content": f"💬 正在添加评论: {comment} ({startPos} - {endPos})"})
#     print(f"[comment_document] 请求前端添加评论 (comment={comment}, startPos={startPos}, endPos={endPos})")
#     return f"已在文档位置 ({startPos} - {endPos}) 添加评论: '{comment}'"


# region 多智能体专用工具


class WorkflowStep(BaseModel):
    """工作流步骤"""

    agent: Literal["research", "outline", "writer", "reviewer"] = Field(description="执行该步骤的 agent 名称")
    task: str = Field(description="该步骤的具体任务描述，将作为指令发送给对应 agent")
    depends_on: list[int] = Field(
        default_factory=list,
        description="依赖的步骤编号（从 0 开始），该步骤会等依赖步骤完成后再执行",
    )


class Workflow(BaseModel):
    """工作流定义"""

    steps: list[WorkflowStep] = Field(description="工作流步骤列表，按执行顺序排列")
    summary: str = Field(description="工作流总体说明（一句话概括整个计划）")


@tool
def create_workflow(workflow: Workflow) -> str:
    """
    创建多智能体工作流 —— 规划任务执行步骤。

    你是 Planner Agent，负责将用户的写作需求拆解为多步骤工作流。
    每个步骤指定由哪个 agent 执行、具体任务、以及依赖关系。

    可用的 agent：
    - research: 负责搜索网络资料（web_search, web_fetch）
    - outline: 负责读取文档和生成大纲（read_document, query_document）
    - writer: 负责生成 Word 文档（generate_document）
    - reviewer: 负责审核文档质量并打分（review_document）

    典型工作流示例：
    1. research: 搜索相关资料
    2. outline: 根据资料生成大纲
    3. writer: 根据大纲和资料撰写文档
    4. reviewer: 审核文档质量

    Args:
        workflow: 工作流定义，包含步骤列表和总体说明

    Returns:
        工作流 JSON
    """
    writer = get_stream_writer()
    wf_dict = workflow.model_dump()
    step_count = len(wf_dict.get("steps", []))
    print(f"[create_workflow] 工作流: {wf_dict['summary']}, {step_count} 个步骤")
    return json.dumps(wf_dict, ensure_ascii=False)


class ReviewResult(BaseModel):
    """审查结果"""

    score: int = Field(description="文档质量评分（1-10），7 分及以上视为通过", ge=1, le=10)
    passed: bool = Field(description="是否通过审核。True=通过，False=需要重写")
    feedback: str = Field(description="审核意见，指出优点和不足")
    rewrite_instructions: str = Field(
        default="",
        description="重写指令（仅当 passed=False 时需要填写），具体说明需要改进的地方",
    )


@tool
def review_document(review: ReviewResult) -> str:
    """
    审核文档质量并给出评分和反馈。

    你是 Reviewer Agent，负责检查 Writer 生成的文档是否满足用户需求。

    评分标准：
    - 1-3 分：严重不足，需要完全重写
    - 4-6 分：有明显不足，需要修改
    - 7-8 分：基本合格，可以通过
    - 9-10 分：优秀

    7 分及以上视为通过（passed=True），低于 7 分需要重写（passed=False）。
    重写时必须在 rewrite_instructions 中给出具体的改进指令。

    Args:
        review: 审查结果，包含评分、是否通过、反馈意见和重写指令

    Returns:
        审核结果 JSON
    """
    writer = get_stream_writer()
    review_dict = review.model_dump()
    print(f"[review_document] 评分: {review_dict['score']}/10, 通过: {review_dict['passed']}")
    return json.dumps(review_dict, ensure_ascii=False)


@tool
def delete_document(startParaIndex: int = 0, endParaIndex: int = -1) -> str:
    """
    删除文档中指定范围的段落。通过 WebSocket 通知前端标记并等待用户确认删除。

    本工具为非阻塞调用：发送删除请求后立即返回，不等待用户确认。
    前端会用蓝色批注高亮要删除的段落，用户可在 agent 执行完毕后再确认。

    Args:
        startParaIndex: 要删除的起始段落索引（0-based）。0 表示从文档开头开始。
        endParaIndex: 要删除的结束段落索引（0-based，含）。-1 表示到文档结尾。

    【调用场景】
    - 用户要求删除某些段落、章节或内容
    - 用户说"删掉第X段"、"把这部分去掉"、"移除这段内容"
    - 配合 query_document 定位后，删除匹配的段落

    【注意】
    - 删除操作需要用户在前端确认后才会执行
    - 删除是不可逆的，请确保范围正确
    - 本工具不会阻塞，可以继续调用其他工具（如 generate_document）

    Returns:
        删除请求已发送的描述字符串
    """
    writer = get_stream_writer()
    writer(
        {
            "type": "delete_document",
            "content": f"🗑️ 准备删除文档段落(段落 {startParaIndex} - {endParaIndex})",
            "startParaIndex": startParaIndex,
            "endParaIndex": endParaIndex,
        }
    )
    print(f"[delete_document] 请求前端删除文档段落 (startParaIndex={startParaIndex}, endParaIndex={endParaIndex})")

    # 非阻塞：立即返回，前端自行处理用户确认
    return f"已通知前端标记删除段落 {startParaIndex} - {endParaIndex}，等待用户确认"


# region Tools 注册

ALL_TOOLS = [read_document, generate_document, delete_document, query_document, web_search, web_fetch]
TOOL_MAP = {t.name: t for t in ALL_TOOLS}

# 按 agent 角色分组的工具集
PLANNER_TOOLS = [create_workflow]
RESEARCH_TOOLS = [web_search, web_fetch]
OUTLINE_TOOLS = [read_document, query_document]
WRITER_TOOLS = [generate_document, delete_document, read_document, query_document]
REVIEWER_TOOLS = [review_document]

AGENT_TOOLS = {
    "planner": PLANNER_TOOLS,
    "research": RESEARCH_TOOLS,
    "outline": OUTLINE_TOOLS,
    "writer": WRITER_TOOLS,
    "reviewer": REVIEWER_TOOLS,
}
