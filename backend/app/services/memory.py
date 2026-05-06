"""
对话记忆管理模块

提供两层记忆机制：

记忆层级：
1. 短期记忆 (Short-term)   — 固定 token 预算（类 Claude Code）
2. 长期记忆 (Long-term)    — md 文件持久化（user-memory.md, feedback-memory.md, document-memory.md）

"""

from __future__ import annotations

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


# ============ 短期记忆 Token 预算（类 Claude Code 风格） ============
SHORT_TERM_TOKEN_BUDGET = _get_env_int("WORDAGENT_SHORT_TERM_TOKEN_BUDGET", 30000)


# ============== 长期记忆配置 ==============
ENABLE_AUTO_MEMORY_EXTRACT = os.environ.get("WORDAGENT_ENABLE_AUTO_MEMORY_EXTRACT", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

MEMORY_EXTRACT_TEMPERATURE = _get_env_int("WORDAGENT_MEMORY_EXTRACT_TEMPERATURE", 0)

LONG_TERM_MEMORY_TYPES = ["user", "feedback", "document"]


# ============== Memory Tool 定义 ==============


def _get_memory_dir() -> Path:
    """获取长期记忆目录，不存在则创建"""
    from app.core.config import get_wence_data_dir

    memory_dir = get_wence_data_dir() / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def _get_memory_file(name: str) -> Path:
    """获取指定名称的记忆文件路径"""
    return _get_memory_dir() / f"{name}-memory.md"


def _get_memory_tools():
    """延迟导入避免循环依赖"""
    from langchain_core.tools import tool

    @tool
    def save_user_memory(memory: str) -> str:
        """保存用户偏好和写作风格等记忆。只在用户明确提供了偏好或相关信息时才调用。"""
        file_path = _get_memory_file("user")
        try:
            file_path.write_text(memory.strip(), encoding="utf-8")
            return f"已保存到 {file_path}"
        except Exception as e:
            return f"保存失败: {e}"

    @tool
    def save_feedback_memory(memory: str) -> str:
        """保存用户对 AI 输出的反馈和纠正。只在用户明确提供了反馈时才调用。"""
        file_path = _get_memory_file("feedback")
        try:
            file_path.write_text(memory.strip(), encoding="utf-8")
            return f"已保存到 {file_path}"
        except Exception as e:
            return f"保存失败: {e}"

    @tool
    def save_document_memory(memory: str) -> str:
        """保存当前文档的相关信息（类型、主题、格式要求等）。只在对话涉及具体文档时才调用。"""
        file_path = _get_memory_file("document")
        try:
            file_path.write_text(memory.strip(), encoding="utf-8")
            return f"已保存到 {file_path}"
        except Exception as e:
            return f"保存失败: {e}"

    return [save_user_memory, save_feedback_memory, save_document_memory]


def get_memory_tools():
    """获取记忆工具列表（供外部调用）"""
    return _get_memory_tools()


# ============== 长期记忆读写 ==============


def read_long_term_memory() -> dict[str, str]:
    """读取所有长期记忆文件。"""
    result = {}
    for name in LONG_TERM_MEMORY_TYPES:
        file_path = _get_memory_file(name)
        try:
            if file_path.exists():
                result[name] = file_path.read_text(encoding="utf-8").strip()
            else:
                result[name] = ""
        except Exception as e:
            print(f"[Memory] 读取 {name} 记忆失败: {e}")
            result[name] = ""
    return result


def write_long_term_memory(name: str, content: str) -> bool:
    """写入单个长期记忆文件。"""
    file_path = _get_memory_file(name)
    try:
        file_path.write_text(content.strip(), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[Memory] 写入 {name} 记忆失败: {e}")
        return False


def build_long_term_memory_prompt() -> str:
    """将长期记忆格式化为系统提示词的一部分。"""
    memories = read_long_term_memory()
    parts = []

    title_map = {
        "user": "User Memory",
        "feedback": "Feedback Memory",
        "document": "Document Memory",
    }

    for name, content in memories.items():
        if not content:
            continue

        title = title_map.get(name, name)

        if len(content) > 4000:
            content = content[:4000] + f"\n[...截断，原 {len(content)} 字符]"

        parts.append(f"### {title}\n{content}")

    if not parts:
        return ""

    header = "## Long-term Memory (Persisted across sessions)\n"
    return header + "\n\n".join(parts) + "\n"


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

    selected_pairs: list[tuple[str, str]] = []
    total_tokens = 0

    for user_msg, ai_msg in reversed(pairs):
        user_tokens = _estimate_token_count(user_msg) + 20
        ai_tokens = _estimate_token_count(ai_msg) + 20
        pair_tokens = user_tokens + ai_tokens

        if total_tokens + pair_tokens <= budget:
            selected_pairs.insert(0, (user_msg, ai_msg))
            total_tokens += pair_tokens
        else:
            if not selected_pairs:
                max_chars = int(budget * 2)
                truncated_user = _truncate_text(user_msg, max_chars)
                if _estimate_token_count(truncated_user) <= budget:
                    selected_pairs.append((truncated_user, ""))
            break

    result: list[HumanMessage | AIMessage] = []
    for user_msg, ai_msg in selected_pairs:
        result.append(HumanMessage(content=user_msg))
        if ai_msg:
            result.append(AIMessage(content=ai_msg))

    print(f"[Memory] 短期记忆: 保留 {len(selected_pairs)} 轮对话, ~{total_tokens} tokens")
    return result


# ============== 工具函数 ==============


def _pair_history(history: list[dict]) -> list[tuple[str, str]]:
    """将 history 列表配对为 (user_msg, assistant_msg) 元组列表。"""
    pairs = []
    i = 0
    valid = [
        h
        for h in history
        if h.get("content") and isinstance(h["content"], str) and h.get("role") in ("user", "assistant")
    ]
    print(f"[Memory] _pair_history: 原始 history={len(history)}, 过滤后 valid={len(valid)}")
    while i < len(valid) - 1:
        if valid[i]["role"] == "user" and valid[i + 1]["role"] == "assistant":
            pairs.append((valid[i]["content"], valid[i + 1]["content"]))
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


# ============== 长期记忆提取（Tool 方式） ==============


def extract_and_save_memory(
    conversation: str,
    llm: Any,
    force: bool = False,
) -> dict[str, bool]:
    """
    使用 Tool 方式从对话中提取关键信息并保存到长期记忆。

    Args:
        conversation: 对话内容
        llm: LLM 实例
        force: 强制提取，忽略 ENABLE_AUTO_MEMORY_EXTRACT 配置

    Returns:
        dict[str, bool]: 各记忆类型的保存结果
    """
    if not force and not ENABLE_AUTO_MEMORY_EXTRACT:
        print("[Memory] 自动记忆提取已禁用 (WORDAGENT_ENABLE_AUTO_MEMORY_EXTRACT=false)")
        return {name: False for name in LONG_TERM_MEMORY_TYPES}

    if not conversation or not llm:
        return {name: False for name in LONG_TERM_MEMORY_TYPES}

    prompt = _build_extract_prompt(conversation)

    try:
        memory_tools = _get_memory_tools()
        llm_with_tools = llm.bind_tools(memory_tools)
        response = llm_with_tools.invoke([{"role": "user", "content": prompt}])

        saved = {}
        tool_calls = response.tool_calls if hasattr(response, "tool_calls") else []

        if not tool_calls:
            print(
                f"[Memory] LLM 未调用任何工具，响应: {response.content[:200] if hasattr(response, 'content') else response}"
            )
            return {name: False for name in LONG_TERM_MEMORY_TYPES}

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})

            if tool_name == "save_user_memory":
                saved["user"] = write_long_term_memory("user", tool_args.get("memory", ""))
            elif tool_name == "save_feedback_memory":
                saved["feedback"] = write_long_term_memory("feedback", tool_args.get("memory", ""))
            elif tool_name == "save_document_memory":
                saved["document"] = write_long_term_memory("document", tool_args.get("memory", ""))

        for name in LONG_TERM_MEMORY_TYPES:
            if name not in saved:
                saved[name] = False

        print(f"[Memory] 长期记忆提取完成: {saved}")
        return saved

    except Exception as e:
        print(f"[Memory] 长期记忆提取失败: {e}")
        import traceback

        traceback.print_exc()
        return {name: False for name in LONG_TERM_MEMORY_TYPES}


def _load_extract_prompt_template() -> str:
    """从 md 文件加载记忆提取提示词模板。"""
    from pathlib import Path

    template_path = Path(__file__).parent / "agent" / "prompts" / "system-prompt-memory-extract-template.md"
    try:
        return template_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[Memory] 加载提取提示词模板失败: {e}")
        return "Extract key information from the following conversation:\n{conversation}"


_EXTRACT_PROMPT_TEMPLATE = _load_extract_prompt_template()


def _build_extract_prompt(conversation: str) -> str:
    """构建记忆提取的提示词"""
    return _EXTRACT_PROMPT_TEMPLATE.format(conversation=conversation)
