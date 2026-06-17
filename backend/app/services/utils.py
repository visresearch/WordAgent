"""服务层通用工具函数。"""

import json
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def _strip_code_fence(text: str) -> str:
    """去掉可能包裹参数的 Markdown 代码块围栏。"""
    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return cleaned


def repair_unescaped_quotes_in_json(raw: str) -> str:
    """修复 JSON 字符串值中的未转义双引号。"""
    out: list[str] = []
    in_string = False
    escape = False
    i = 0
    n = len(raw)

    while i < n:
        ch = raw[i]
        if in_string:
            if escape:
                out.append(ch)
                escape = False
                i += 1
                continue

            if ch == "\\":
                out.append(ch)
                escape = True
                i += 1
                continue

            if ch == '"':
                j = i + 1
                while j < n and raw[j] in " \t\r\n":
                    j += 1
                next_sig = raw[j] if j < n else ""
                if next_sig in {",", "}", "]", ":"}:
                    out.append('"')
                    in_string = False
                else:
                    out.append('\\"')
                i += 1
                continue

            out.append(ch)
            i += 1
            continue

        out.append(ch)
        if ch == '"':
            in_string = True
        i += 1

    return "".join(out)


def parse_tool_args_with_repair(raw_args: Any) -> dict | None:
    """尝试解析工具参数；若 JSON 非法，执行一次轻量修复后重试。"""
    if isinstance(raw_args, dict):
        return raw_args
    if not isinstance(raw_args, str) or not raw_args.strip():
        return None

    raw_args = _strip_code_fence(raw_args)

    try:
        return json.loads(raw_args)
    except json.JSONDecodeError:
        repaired = repair_unescaped_quotes_in_json(raw_args)
        if repaired != raw_args:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass
    return None


def _normalize_blank_paragraph_shape(document: dict) -> dict:
    """Normalize blank paragraph shape for generate_document payload.

    Rule: when runs is an empty list, pStyle must be an empty string.
    """
    paragraphs = document.get("paragraphs")
    if not isinstance(paragraphs, list):
        return document

    normalized_paragraphs: list[Any] = []
    for para in paragraphs:
        if not isinstance(para, dict):
            normalized_paragraphs.append(para)
            continue

        runs = para.get("runs")
        if isinstance(runs, list) and len(runs) == 0 and para.get("pStyle") != "":
            para = {**para, "pStyle": ""}

        normalized_paragraphs.append(para)

    return {**document, "paragraphs": normalized_paragraphs}


def _pad_style_array(style_id: str, style_value: Any) -> Any:
    """Pad known style arrays when the model omits trailing default fields."""
    if not isinstance(style_value, list):
        return style_value

    defaults_by_prefix = {
        "pS_": ["left", 0, 0, 0, 0, 0, 0, "", 1],
        "rS_": ["", 12, False, False, 0, "#000000", "#000000", 0, False, False, False],
        "cS_": [1, 1, "left", "center"],
        "tS_": [1],
    }

    for prefix, defaults in defaults_by_prefix.items():
        if not style_id.startswith(prefix):
            continue
        if len(style_value) >= len(defaults):
            return style_value
        return [*style_value, *defaults[len(style_value) :]]

    return style_value


def _normalize_style_shapes(document: dict) -> dict:
    """Normalize generate_document styles before Pydantic validates them."""
    styles = document.get("styles")
    if not isinstance(styles, dict):
        return document

    normalized_styles = {
        style_id: _pad_style_array(style_id, style_value)
        for style_id, style_value in styles.items()
    }
    return {**document, "styles": normalized_styles}


def _normalize_generate_document_payload(document: dict) -> dict:
    document = _normalize_blank_paragraph_shape(document)
    document = _normalize_style_shapes(document)
    return document


def normalize_tool_args(tool_name: str, raw_args: Any) -> dict:
    """归一化工具参数，修复常见的模型参数形态偏差。"""
    args = parse_tool_args_with_repair(raw_args)
    if args is None:
        raise ValueError("工具参数不是合法 JSON 对象")

    # 兼容模型将 document 误生成为 JSON 字符串的情况
    # 预期: {"document": {...}}，实际偶发: {"document": "{...}"}
    if tool_name == "generate_document":
        document = args.get("document")
        if isinstance(document, str):
            doc_raw = _strip_code_fence(document).strip()
            parsed_document = parse_tool_args_with_repair(doc_raw)

            # 兼容 Python 字面量字符串（如 str(dict)）
            if not isinstance(parsed_document, dict):
                try:
                    import ast

                    literal_val = ast.literal_eval(doc_raw)
                    if isinstance(literal_val, dict):
                        parsed_document = literal_val
                except Exception:
                    pass

            if isinstance(parsed_document, dict):
                # 成功解析，用 dict 替换字符串
                args = {**args, "document": _normalize_blank_paragraph_shape(parsed_document)}
                logger.info(f"[normalize_tool_args] ✅ 成功解析 document 字符串为 dict")
            else:
                # 解析失败，打印警告但继续（不抛错），让 Pydantic schema 处理
                logger.error(f"[normalize_tool_args] ⚠️ document 字符串解析失败，将由 schema 处理: {doc_raw[:100]}...")
        elif isinstance(document, dict):
            args = {**args, "document": _normalize_blank_paragraph_shape(document)}

    if tool_name == "generate_document" and isinstance(args.get("document"), str):
        doc_raw = _strip_code_fence(args["document"]).strip()
        parsed_document = parse_tool_args_with_repair(doc_raw)
        if not isinstance(parsed_document, dict):
            try:
                import ast

                literal_val = ast.literal_eval(doc_raw)
                if isinstance(literal_val, dict):
                    parsed_document = literal_val
            except Exception:
                pass
        if isinstance(parsed_document, dict):
            args = {**args, "document": parsed_document}

    if tool_name == "generate_document" and isinstance(args.get("document"), dict):
        args = {**args, "document": _normalize_generate_document_payload(args["document"])}

    return args
