"""
对话记忆管理模块

提供两层记忆机制：

记忆层级：
1. 短期记忆 (Short-term)   — LangGraph Checkpointer 持久化会话状态
2. 长期记忆 (Long-term)    — 单个 md 文件持久化（memory.md）

"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any
from weakref import WeakValueDictionary

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.core.logging import get_logger
from app.services.utils import _get_env_float, _get_env_int

logger = get_logger(__name__)

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

_THREAD_LOCKS: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()


# ============== 长期记忆配置 ==============
MEMORY_EXTRACT_TEMPERATURE = _get_env_float("WORDAGENT_MEMORY_EXTRACT_TEMPERATURE", 0.1)

# 长期记忆上限（条数）
MAX_MEMORY_ITEMS = _get_env_int("WORDAGENT_MEMORY_MAX_ITEMS", 20)


# ============== 官方短期记忆（LangGraph Checkpointer） ==============


def get_checkpoint_db_path() -> Path:
    """返回独立于业务数据库的 LangGraph Checkpoint 文件路径。"""
    data_dir = _get_memory_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "langgraph_checkpoints.db"


@asynccontextmanager
async def open_checkpointer() -> AsyncIterator[AsyncSqliteSaver]:
    """在应用生命周期内打开并复用官方异步 SQLite Checkpointer。"""
    async with AsyncSqliteSaver.from_conn_string(str(get_checkpoint_db_path())) as checkpointer:
        yield checkpointer


def build_thread_id(session_id: int) -> str:
    """把业务 Session ID 映射为稳定的 LangGraph thread_id。"""
    return f"session:{session_id}"


def build_thread_config(session_id: int) -> dict:
    """构造访问某个持久会话 Checkpoint 的配置。"""
    return {"configurable": {"thread_id": build_thread_id(session_id)}}


def build_runtime_thread_id(session_id: int | None, chat_id: str | None) -> str:
    """持久会话使用 session_id；无 Session 的连接使用临时 thread_id。"""
    if session_id is not None:
        return build_thread_id(session_id)
    return f"ephemeral:{chat_id or 'anonymous'}"


async def delete_thread(checkpointer, session_id: int) -> None:
    """删除 Session 对应的全部 LangGraph Checkpoint。"""
    await checkpointer.adelete_thread(build_thread_id(session_id))


def get_thread_lock(session_id: int | None, chat_id: str | None) -> asyncio.Lock:
    """返回 thread_id 对应的进程内互斥锁。"""
    thread_id = build_runtime_thread_id(session_id, chat_id)
    lock = _THREAD_LOCKS.get(thread_id)
    if lock is None:
        lock = asyncio.Lock()
        _THREAD_LOCKS[thread_id] = lock
    return lock


@asynccontextmanager
async def single_agent_thread_lock(
    session_id: int | None,
    chat_id: str | None,
) -> AsyncIterator[None]:
    """保证同一持久会话最多运行一个单智能体请求。"""
    async with get_thread_lock(session_id, chat_id):
        yield


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
        logger.error(f"[Memory] 读取长期记忆开关失败，按关闭处理: {e}")
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
        logger.error(f"[Memory] 保存记忆失败: {e}")
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
    logger.info(f"[Memory] 压缩: 删除 {removed} 条旧记忆，保留 {MAX_MEMORY_ITEMS} 条")
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
        logger.error(f"[Memory] 读取记忆失败: {e}")
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
        logger.info("[Memory] 长期记忆开关关闭，跳过自动记忆提取")
        return {"added": False}

    if not conversation or not llm:
        return {"added": False}

    latest_turn_conversation = _extract_latest_user_assistant_turn(conversation)
    if not latest_turn_conversation:
        return {"added": False}

    if latest_turn_conversation.strip() != conversation.strip():
        logger.info("[Memory] 记忆提取仅使用最近一轮 user/assistant 对话")

    prompt = _build_extract_prompt(latest_turn_conversation)

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])

        content = ""
        if hasattr(response, "content") and response.content:
            content = response.content.strip()
        elif hasattr(response, "text") and response.text:
            content = response.text.strip()

        if not content:
            logger.info("[Memory] LLM 未返回任何内容")
            return {"added": False}

        items = _parse_extracted_items(content)
        if not items:
            logger.info("[Memory] 未提取到有效记忆条目")
            return {"added": False}

        logger.info(f"[Memory] 提取到 {len(items)} 条候选记忆")

        added_count = 0
        for item in items:
            success, reason = _add_item(item)
            if success:
                added_count += 1
                logger.info(f"[Memory] 添加: {item[:40]}... ({reason})")
            else:
                logger.info(f"[Memory] 跳过: {item[:40]}... ({reason})")

        current_count = _get_item_count()
        logger.info(f"[Memory] 记忆提取完成: 新增 {added_count} 条, 当前共 {current_count} 条")

        return {"added": added_count > 0}

    except Exception as e:
        logger.error(f"[Memory] 记忆提取失败: {e}")
        import traceback

        traceback.print_exc()
        return {"added": False}
