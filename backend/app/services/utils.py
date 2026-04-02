"""服务层通用工具函数。"""

import json
from typing import Any


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

            if not isinstance(parsed_document, dict):
                raise ValueError(
                    "generate_document.document 解析失败。请传对象(dict)而非字符串；"
                    "若为 JSON 字符串请确保内部引号已正确转义。"
                )
            args = {**args, "document": parsed_document}

    return args
