"""
对话记忆管理模块

提供两层记忆机制：

记忆层级：
1. 短期记忆 (Short-term)   — 固定 token 预算（类 Claude Code）
2. 长期记忆 (Long-term)    — 单个 md 文件持久化（memory.md）

"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"langchain_classic")

from langchain_core.messages import AIMessage, HumanMessage

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

# ============== 配置常量 ==============


def _get_env_int(name: str, default: int) -> int:
    """Read positive int env value with fallback."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        val = int(str(raw).strip())
        return val if val > 0 else default
    except Exception:
        return default


def _get_env_float(name: str, default: float) -> float:
    """Read positive float env value with fallback."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        val = float(str(raw).strip())
        return val if val > 0 else default
    except Exception:
        return default


# ============ 短期记忆 Token 预算（类 Claude Code 风格） ============
SHORT_TERM_TOKEN_BUDGET = _get_env_int("WORDAGENT_SHORT_TERM_TOKEN_BUDGET", 50000)
SHORT_TERM_MIN_TURNS = _get_env_int("WORDAGENT_SHORT_TERM_MIN_TURNS", 3)
SHORT_TERM_LARGE_TOOL_OUTPUT_TOKENS = _get_env_int("WORDAGENT_SHORT_TERM_LARGE_TOOL_OUTPUT_TOKENS", 2000)


# ============== 长期记忆配置 ==============
MEMORY_EXTRACT_TEMPERATURE = _get_env_float("WORDAGENT_MEMORY_EXTRACT_TEMPERATURE", 0.1)

# 长期记忆上限（条数）
MAX_MEMORY_ITEMS = _get_env_int("WORDAGENT_MEMORY_MAX_ITEMS", 20)


# ============== Memory Tool 定义 ==============


def _get_memory_dir() -> Path:
    """获取 wence_data 目录"""
    from app.core.config import get_wence_data_dir

    return get_wence_data_dir()


def _get_memory_file() -> Path:
    """获取记忆文件路径"""
    return _get_memory_dir() / "memory.md"


def is_long_term_memory_enabled() -> bool:
    """是否启用长期记忆（由用户设置控制，默认关闭）。"""
    try:
        from app.core.config import get_user_settings_file

        settings_file = get_user_settings_file()
        if not settings_file.exists():
            return False
        raw = settings_file.read_text(encoding="utf-8")
        data = json.loads(raw) if raw.strip() else {}
        return bool(data.get("enableLongTermMemory", False))
    except Exception as e:
        print(f"[Memory] 读取长期记忆开关失败，按关闭处理: {e}")
        return False


def _get_all_items() -> list[str]:
    """获取所有记忆条目（以 - 开头的行）"""
    file_path = _get_memory_file()
    if not file_path.exists():
        return []
    try:
        content = file_path.read_text(encoding="utf-8")
        items = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                item = line[1:].strip()
                if item:
                    items.append(item)
        return items
    except Exception:
        return []


def _save_items(items: list[str]) -> bool:
    """保存所有记忆条目到文件"""
    file_path = _get_memory_file()
    try:
        content = "\n".join(f"- {item}" for item in items if item)
        file_path.write_text(content + "\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"[Memory] 保存记忆失败: {e}")
        return False


def _get_item_count() -> int:
    """获取当前记忆条数"""
    return len(_get_all_items())


def _is_too_similar(item1: str, item2: str, threshold: float = 0.8) -> bool:
    """检查两个条目是否过于相似"""
    import difflib

    ratio = difflib.SequenceMatcher(None, item1.lower(), item2.lower()).ratio()
    return ratio >= threshold


def _should_skip_item(new_item: str, existing_items: list[str]) -> tuple[bool, str]:
    """
    检查是否应该跳过新条目。
    返回 (是否跳过, 原因)
    """
    new_lower = new_item.lower()
    for existing in existing_items:
        if new_lower == existing.lower():
            return True, "完全相同"
        if _is_too_similar(existing, new_item):
            if len(existing) >= len(new_item):
                return True, f"与已有记忆相似: {existing[:30]}..."
            else:
                return False, f"替换更完整的版本: {existing[:30]}..."
    return False, ""


def _add_item(new_item: str) -> tuple[bool, str]:
    """
    添加一条记忆。新记忆追加到末尾（最新位置）。
    如果超过上限，会触发压缩删除旧记忆。
    返回 (是否添加成功, 原因)
    """
    should_skip, reason = _should_skip_item(new_item, _get_all_items())
    if should_skip:
        return False, f"跳过: {reason}"

    # 直接追加（压缩逻辑在外部处理）
    existing_items = _get_all_items()

    # 如果有相似的但新条目更完整，替换旧条目
    new_lower = new_item.lower()
    filtered = []
    replaced = False
    for existing in existing_items:
        if not replaced and _is_too_similar(existing, new_item) and len(new_item) > len(existing):
            filtered.append(new_item)
            replaced = True
        elif existing.lower() != new_lower:
            filtered.append(existing)

    if not replaced:
        filtered.append(new_item)

    # 超过上限时压缩
    if len(filtered) > MAX_MEMORY_ITEMS:
        filtered = _compact_by_removing_old(filtered)

    if _save_items(filtered):
        return True, f"已添加 ({len(filtered)}/{MAX_MEMORY_ITEMS})"
    return False, "保存失败"


def _compact_by_removing_old(items: list[str]) -> list[str]:
    """
    简单压缩：添加新记忆后超过阈值时，删掉超出的条目（从最老的开始删）。
    """
    if not items:
        return []

    if len(items) <= MAX_MEMORY_ITEMS:
        return items

    removed = len(items) - MAX_MEMORY_ITEMS
    print(f"[Memory] 压缩: 删除 {removed} 条旧记忆，保留 {MAX_MEMORY_ITEMS} 条")
    return items[-MAX_MEMORY_ITEMS:]


# ============== 长期记忆读写 ==============


def read_long_term_memory() -> str:
    """读取长期记忆文件内容"""
    file_path = _get_memory_file()
    if not file_path.exists():
        return ""
    try:
        return file_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"[Memory] 读取记忆失败: {e}")
        return ""


def build_long_term_memory_prompt() -> str:
    """将长期记忆格式化为系统提示词的一部分"""
    if not is_long_term_memory_enabled():
        return ""

    content = read_long_term_memory()
    if not content:
        return ""

    count = len(_get_all_items())
    if len(content) > 4000:
        content = content[:4000] + f"\n[...截断，原 {len(content)} 字符]"

    return f"""## Long-term Memory ({count} items, persisted across sessions)

**Note: Memory is stored in chronological order — OLDEST entries are at the TOP, NEWEST at the BOTTOM.**

{content}
"""


# ============== 短期记忆（固定 Token 预算，类 Claude Code） ==============


def build_short_term_messages(
    history: list[dict],
    token_budget: int | None = None,
) -> list[HumanMessage | AIMessage]:
    """
    使用固定 token 预算加载短期记忆（类 Claude Code 风格）。

    从最近的消息开始，保留足够的内容满足 token 预算。

    """
    if not history:
        return []

    budget = token_budget or SHORT_TERM_TOKEN_BUDGET
    pairs = _pair_history(history)

    if not pairs:
        return []

    def _render_pair(pair: tuple[dict, dict], include_tool_outputs: bool) -> tuple[str, str]:
        user_entry, ai_entry = pair
        return (
            _format_history_entry(user_entry, include_tool_outputs=include_tool_outputs).strip(),
            _format_history_entry(ai_entry, include_tool_outputs=include_tool_outputs).strip(),
        )

    def _pair_token_count(rendered_pair: tuple[str, str]) -> int:
        user_msg, ai_msg = rendered_pair
        return _estimate_token_count(user_msg) + _estimate_token_count(ai_msg) + 40

    min_turns = min(SHORT_TERM_MIN_TURNS, len(pairs))
    selected: list[dict[str, Any]] = []
    total_tokens = 0

    for pair in pairs[-min_turns:]:
        rendered = _render_pair(pair, include_tool_outputs=True)
        pair_tokens = _pair_token_count(rendered)
        selected.append(
            {
                "pair": pair,
                "rendered": rendered,
                "include_outputs": True,
                "tokens": pair_tokens,
            }
        )
        total_tokens += pair_tokens

    # If the selected window is over budget, remove tool outputs from the oldest
    # selected turns first. Keep tool names and input parameters.
    stripped_outputs = 0
    for item in selected:
        if total_tokens <= budget:
            break
        if not item["include_outputs"]:
            continue
        stripped = _render_pair(item["pair"], include_tool_outputs=False)
        stripped_tokens = _pair_token_count(stripped)
        total_tokens -= item["tokens"] - stripped_tokens
        item["rendered"] = stripped
        item["tokens"] = stripped_tokens
        item["include_outputs"] = False
        stripped_outputs += 1

    older_pairs = pairs[: len(pairs) - min_turns]
    for pair in reversed(older_pairs):
        rendered = _render_pair(pair, include_tool_outputs=True)
        pair_tokens = _pair_token_count(rendered)
        if total_tokens + pair_tokens <= budget:
            selected.insert(
                0,
                {
                    "pair": pair,
                    "rendered": rendered,
                    "include_outputs": True,
                    "tokens": pair_tokens,
                },
            )
            total_tokens += pair_tokens
            continue

        stripped = _render_pair(pair, include_tool_outputs=False)
        stripped_tokens = _pair_token_count(stripped)
        if total_tokens + stripped_tokens <= budget:
            selected.insert(
                0,
                {
                    "pair": pair,
                    "rendered": stripped,
                    "include_outputs": False,
                    "tokens": stripped_tokens,
                },
            )
            total_tokens += stripped_tokens
            stripped_outputs += 1
            continue

        break

    result: list[HumanMessage | AIMessage] = []
    for item in selected:
        user_msg, ai_msg = item["rendered"]
        result.append(HumanMessage(content=user_msg))
        if ai_msg:
            result.append(AIMessage(content=ai_msg))

    over_budget_note = " (over budget after stripping tool outputs)" if total_tokens > budget else ""
    print(
        f"[Memory] 短期记忆: 保留 {len(selected)} 轮对话, "
        f"剥离工具输出 {stripped_outputs} 轮, ~{total_tokens} tokens{over_budget_note}"
    )
    return result


# ============== 工具函数 ==============


def _normalize_history_role(entry: dict) -> str:
    """将不同来源的角色字段统一为 user / assistant。"""
    role = str(entry.get("role", "")).strip().lower()
    if role in ("user", "assistant"):
        return role

    msg_type = str(entry.get("type", "")).strip().lower()
    if msg_type in ("human", "user"):
        return "user"
    if msg_type in ("ai", "assistant"):
        return "assistant"

    return ""


def _normalize_history_content(content: Any) -> str:
    """将消息 content 统一转换为文本。"""
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
        fallback = content.get("content")
        return fallback if isinstance(fallback, str) else ""

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            item_text = _normalize_history_content(item)
            if item_text:
                parts.append(item_text)
        return "".join(parts)

    return ""


def _dump_memory_json(value: Any) -> str:
    """Compact JSON used in short-term memory while preserving Chinese text."""
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(value)


def _get_history_field(entry: dict, snake_name: str, camel_name: str) -> Any:
    if snake_name in entry:
        return entry.get(snake_name)
    return entry.get(camel_name)


def _has_tool_calls(tool_json: Any) -> bool:
    if isinstance(tool_json, dict) and isinstance(tool_json.get("calls"), list):
        return len(tool_json.get("calls") or []) > 0
    return bool(tool_json)


def _format_tool_value_for_memory(value: Any, indent: str = "  ") -> str:
    text = _dump_memory_json(value)
    if "\n" not in text:
        return text
    return "\n" + "\n".join(f"{indent}{line}" for line in text.splitlines())


def _format_tool_output_for_memory(value: Any, indent: str = "  ") -> str:
    text = _dump_memory_json(value)
    token_count = _estimate_token_count(text)
    if token_count > SHORT_TERM_LARGE_TOOL_OUTPUT_TOKENS:
        max_chars = max(500, SHORT_TERM_LARGE_TOOL_OUTPUT_TOKENS * 2)
        text = (
            f"[tool output preview: original ~{token_count} tokens, "
            f"threshold={SHORT_TERM_LARGE_TOOL_OUTPUT_TOKENS}]\n" + _truncate_text(text, max_chars)
        )
    if "\n" not in text:
        return text
    return "\n" + "\n".join(f"{indent}{line}" for line in text.splitlines())


def _format_tool_json_for_memory(tool_json: Any, include_outputs: bool = True) -> str:
    """Render tool_json as readable Markdown for short-term memory."""
    if not isinstance(tool_json, dict):
        return _dump_memory_json(tool_json)

    calls = tool_json.get("calls")
    if not isinstance(calls, list):
        return _dump_memory_json(tool_json)

    lines: list[str] = []
    for index, call in enumerate(calls, 1):
        if not isinstance(call, dict):
            lines.append(f"- tool_call_{index}: {_format_tool_value_for_memory(call)}")
            continue

        tool_name = str(call.get("tool") or call.get("name") or f"tool_call_{index}")
        lines.append(f"- tool: {tool_name}")

        if tool_name != "generate_document" and "input" in call:
            lines.append(f"  - input: {_format_tool_value_for_memory(call.get('input'), indent='    ')}")

        if include_outputs and "output" in call:
            lines.append(f"  - output: {_format_tool_output_for_memory(call.get('output'), indent='    ')}")

        if call.get("error"):
            lines.append(f"  - error: {str(call.get('error')).lower()}")

        for key in ("agent", "repaired", "is_mcp"):
            if key in call and call.get(key) not in (None, False):
                lines.append(f"  - {key}: {_format_tool_value_for_memory(call.get(key), indent='    ')}")

    return "\n".join(lines)


def _format_history_entry(entry: dict, include_tool_outputs: bool = True) -> str:
    """Format one DB/front-end compatible history entry for short-term memory."""
    sections: list[str] = []

    content = _normalize_history_content(entry.get("content")).strip()
    if content:
        sections.append(content)

    tool_json = _get_history_field(entry, "tool_json", "toolJson")
    if _has_tool_calls(tool_json):
        sections.append("[tool_json]\n" + _format_tool_json_for_memory(tool_json, include_outputs=include_tool_outputs))

    return "\n\n".join(sections)


def _pair_history(history: list[dict]) -> list[tuple[dict, dict]]:
    """将 history 列表配对为 (user_entry, assistant_entry) 元组列表。"""
    pairs: list[tuple[dict, dict]] = []
    i = 0
    valid: list[dict[str, Any]] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue

        role = _normalize_history_role(entry)
        if role not in ("user", "assistant"):
            continue

        content = _format_history_entry(entry, include_tool_outputs=False).strip()

        if role == "user" and not content:
            continue
        if role == "assistant" and not content:
            continue

        valid.append({"role": role, "entry": entry})

    print(f"[Memory] _pair_history: 原始 history={len(history)}, 过滤后 valid={len(valid)}")

    while i < len(valid) - 1:
        if valid[i]["role"] == "user" and valid[i + 1]["role"] == "assistant":
            pairs.append((valid[i]["entry"], valid[i + 1]["entry"]))
            i += 2
        else:
            i += 1
    return pairs


def _estimate_token_count(text: str) -> int:
    """Estimate token count with tiktoken (cl100k_base), fallback to char heuristic."""
    if not text:
        return 0

    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, int(len(text) / 1.7))


def _truncate_text(text: str, max_chars: int) -> str:
    """Truncate text by chars with a readable suffix."""
    if len(text) <= max_chars:
        return text
    keep = max(0, max_chars - 48)
    omitted = len(text) - keep
    return f"{text[:keep]}\n[内容过长，已截断 {omitted} 字符]"


# ============== 长期记忆提取 ==============


def _load_extract_prompt_template() -> str:
    """从 md 文件加载记忆提取提示词模板"""
    from pathlib import Path

    template_path = Path(__file__).parent / "agent" / "prompts" / "system-prompt-memory-extract-template.md"
    try:
        return template_path.read_text(encoding="utf-8")
    except Exception:
        return "Extract key information from the following conversation:\n{conversation}"


_EXTRACT_PROMPT_TEMPLATE = _load_extract_prompt_template()


def _build_extract_prompt(conversation: str) -> str:
    """构建记忆提取的提示词"""
    return _EXTRACT_PROMPT_TEMPLATE.format(conversation=conversation)


def _extract_latest_user_assistant_turn(conversation: str) -> str:
    """
    从拼接后的对话文本中提取最近一轮 user/assistant 对话。

    兼容输入形态：
    - USER: ...
      ASSISTANT: ...
      USER: ...
      ASSISTANT: ...
    """
    if not conversation:
        return ""

    messages: list[tuple[str, str]] = []
    current_role: str | None = None
    current_lines: list[str] = []

    def _flush_current() -> None:
        nonlocal current_role, current_lines
        if current_role is None:
            return
        content = "\n".join(current_lines).strip()
        if content:
            messages.append((current_role, content))
        current_role = None
        current_lines = []

    for raw_line in conversation.splitlines():
        stripped = raw_line.strip()
        marker = stripped.upper()

        if marker.startswith("USER:"):
            _flush_current()
            current_role = "user"
            current_lines = [stripped[5:].lstrip()]
            continue

        if marker.startswith("ASSISTANT:"):
            _flush_current()
            current_role = "assistant"
            current_lines = [stripped[10:].lstrip()]
            continue

        if current_role is not None:
            current_lines.append(raw_line)

    _flush_current()

    # 没有 role 标记时，保持原始文本，避免误伤其他调用方
    if not messages:
        return conversation.strip()

    last_assistant_idx = -1
    for idx in range(len(messages) - 1, -1, -1):
        if messages[idx][0] == "assistant":
            last_assistant_idx = idx
            break

    if last_assistant_idx == -1:
        # 没有 assistant 时，退化为最近一条 user
        for idx in range(len(messages) - 1, -1, -1):
            if messages[idx][0] == "user":
                return f"USER: {messages[idx][1]}"
        return conversation.strip()

    assistant_text = messages[last_assistant_idx][1]
    user_text = ""
    for idx in range(last_assistant_idx - 1, -1, -1):
        if messages[idx][0] == "user":
            user_text = messages[idx][1]
            break

    if user_text:
        return f"USER: {user_text}\n\nASSISTANT: {assistant_text}"
    return f"ASSISTANT: {assistant_text}"


def _parse_extracted_items(content: str) -> list[str]:
    """从 LLM 响应中解析记忆条目"""
    content = content.strip()

    # 检查是否表示不需要添加记忆
    if content.upper() == "NO_MEMORY":
        return []

    items = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("-"):
            item = line[1:].strip()
            if item and item.upper() != "NO_MEMORY":
                items.append(item)
        elif line.startswith("[记忆]") or line.startswith("[memory]"):
            item = line.split("]", 1)[-1].strip()
            if item and item.upper() != "NO_MEMORY":
                items.append(item)
    return items


def extract_and_save_memory(
    conversation: str,
    llm: Any,
) -> dict[str, bool]:
    """
    从对话中提取关键信息并保存到长期记忆。

    机制：
    - LLM 可能返回多条记忆，也可能返回"不需要添加任何记忆"
    - 自动去重和合并相似条目
    - 超过上限时跳过或触发精炼

    Args:
        conversation: 对话内容
        llm: LLM 实例
    Returns:
        dict[str, bool]: {"added": True/False}
    """
    if not is_long_term_memory_enabled():
        print("[Memory] 长期记忆开关关闭，跳过自动记忆提取")
        return {"added": False}

    if not conversation or not llm:
        return {"added": False}

    latest_turn_conversation = _extract_latest_user_assistant_turn(conversation)
    if not latest_turn_conversation:
        return {"added": False}

    if latest_turn_conversation.strip() != conversation.strip():
        print("[Memory] 记忆提取仅使用最近一轮 user/assistant 对话")

    prompt = _build_extract_prompt(latest_turn_conversation)

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])

        content = ""
        if hasattr(response, "content") and response.content:
            content = response.content.strip()
        elif hasattr(response, "text") and response.text:
            content = response.text.strip()

        if not content:
            print("[Memory] LLM 未返回任何内容")
            return {"added": False}

        items = _parse_extracted_items(content)
        if not items:
            print("[Memory] 未提取到有效记忆条目")
            return {"added": False}

        print(f"[Memory] 提取到 {len(items)} 条候选记忆")

        added_count = 0
        for item in items:
            success, reason = _add_item(item)
            if success:
                added_count += 1
                print(f"[Memory] 添加: {item[:40]}... ({reason})")
            else:
                print(f"[Memory] 跳过: {item[:40]}... ({reason})")

        current_count = _get_item_count()
        print(f"[Memory] 记忆提取完成: 新增 {added_count} 条, 当前共 {current_count} 条")

        return {"added": added_count > 0}

    except Exception as e:
        print(f"[Memory] 记忆提取失败: {e}")
        import traceback

        traceback.print_exc()
        return {"added": False}
