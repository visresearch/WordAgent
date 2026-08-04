"""服务层通用工具函数。"""

import json
import os
import secrets
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_uuid7() -> str:
    """生成按时间排序的 UUIDv7 字符串，不引入额外运行时依赖。"""
    timestamp_ms = (time.time_ns() // 1_000_000) & ((1 << 48) - 1)
    value = (timestamp_ms << 80) | (0x7 << 76) | (secrets.randbits(12) << 64) | (0b10 << 62) | secrets.randbits(62)
    return str(uuid.UUID(int=value))


def normalize_uuid(value: Any) -> str | None:
    """把 UUID 输入规范化为小写连字符格式；非法值返回 None。"""
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value).strip()))
    except (AttributeError, TypeError, ValueError):
        return None


def _get_env_int(name: str, default: int) -> int:
    """读取正整数环境变量；未设置或值无效时返回默认值。"""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def _get_env_float(name: str, default: float) -> float:
    """读取正浮点数环境变量；未设置或值无效时返回默认值。"""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(str(raw).strip())
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def try_init_langsmith() -> bool:
    """尝试加载项目环境变量并初始化 LangSmith tracing。"""
    try:
        from dotenv import load_dotenv

        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).parent / ".env")
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(Path(meipass) / ".env")

        backend_dir = Path(__file__).resolve().parent.parent.parent
        candidates.append(backend_dir / ".env")
        candidates.append(Path.cwd() / ".env")

        seen: set[Path] = set()
        for env_path in candidates:
            try:
                resolved = env_path.resolve()
            except Exception:
                resolved = env_path
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.exists():
                logger.info(f"[LangSmith] 加载 .env: {resolved}")
                load_dotenv(resolved, override=False)

        api_key = os.environ.get("LANGSMITH_API_KEY") or ""
        endpoint = os.environ.get("LANGSMITH_ENDPOINT") or "https://api.smith.langchain.com"
        project = os.environ.get("LANGSMITH_PROJECT") or "WordAgent"

        if api_key and project:
            os.environ["LANGCHAIN_API_KEY"] = api_key
            os.environ["LANGCHAIN_ENDPOINT"] = endpoint
            os.environ["LANGCHAIN_PROJECT"] = project
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            logger.info(f"[LangSmith] ✅ 已启用 tracing，project = {project}")
            return True

        logger.warning(f"[LangSmith] ⚠️ 未启用 - API_KEY: {'已设置' if api_key else '未设置'}, PROJECT: {project}")
    except Exception as exc:
        logger.error(f"[LangSmith] ⚠️ 初始化失败: {exc}")
    return False


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


def normalize_json_punctuation_outside_strings(raw: str) -> str:
    """Normalize common Chinese punctuation used as JSON separators.

    Only punctuation outside quoted strings is changed, so normal Chinese text
    inside values is preserved.
    """

    replacements = {
        "，": ",",
        "、": ",",
        "：": ":",
        "；": ";",
        "｛": "{",
        "｝": "}",
        "［": "[",
        "］": "]",
    }

    quote_pairs = {
        '"': '"',
        "'": "'",
        "“": "”",
        "‘": "’",
    }
    quote_output = {
        '"': '"',
        "'": "'",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
    }

    out: list[str] = []
    quote: str | None = None
    escape = False
    for ch in raw:
        if quote:
            if escape:
                out.append(ch)
                escape = False
            elif ch == "\\":
                out.append(ch)
                escape = True
            elif ch == quote:
                out.append(quote_output.get(ch, ch))
                quote = None
            else:
                out.append(ch)
            continue

        if ch in quote_pairs:
            quote = quote_pairs[ch]
            out.append(quote_output.get(ch, ch))
            continue

        out.append(replacements.get(ch, ch))

    return "".join(out)


def _loads_json_object_allow_trailing_closers(raw: str) -> dict | None:
    """Parse a JSON object and tolerate extra trailing closing delimiters.

    Some LLM tool calls end with one more `}`/`]` than needed. `json.loads`
    reports this as "Extra data" even though the first object is complete.
    Only accept this repair when the remaining text contains closing
    delimiters and whitespace only.
    """

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    try:
        parsed, end = json.JSONDecoder().raw_decode(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    remainder = raw[end:].strip()
    if remainder and all(ch in "]} \t\r\n" for ch in remainder):
        return parsed
    return None


def parse_tool_args_with_repair(raw_args: Any) -> dict | None:
    """尝试解析工具参数；若 JSON 非法，执行一次轻量修复后重试。"""
    if isinstance(raw_args, dict):
        return raw_args
    if not isinstance(raw_args, str) or not raw_args.strip():
        return None

    raw_args = _strip_code_fence(raw_args)

    candidates = [raw_args]
    punctuation_repaired = normalize_json_punctuation_outside_strings(raw_args)
    if punctuation_repaired != raw_args:
        candidates.append(punctuation_repaired)

    for candidate in list(candidates):
        quote_repaired = repair_unescaped_quotes_in_json(candidate)
        if quote_repaired != candidate:
            candidates.append(quote_repaired)

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)

        parsed = _loads_json_object_allow_trailing_closers(candidate)
        if parsed is not None:
            return parsed

        try:
            import ast

            parsed = ast.literal_eval(candidate)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            pass

    return None


def _normalize_blank_paragraph_shape(document: dict) -> dict:
    """Preserve blank paragraph styles; schema validation enforces non-empty pStyle."""
    return document


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

    normalized_styles = {style_id: _pad_style_array(style_id, style_value) for style_id, style_value in styles.items()}
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
                logger.debug("[normalize_tool_args] 成功解析 document 字符串为 dict")
            else:
                # 解析失败，打印警告但继续（不抛错），让 Pydantic schema 处理
                logger.warning(f"[normalize_tool_args] document 字符串解析失败，将由 schema 处理: {doc_raw[:100]}...")
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
