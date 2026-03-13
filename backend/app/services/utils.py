"""服务层通用工具函数。"""

import json
from typing import Any


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
