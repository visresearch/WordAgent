"""
对话记忆管理模块

提供两层记忆机制 + 两级上下文压缩（类 Claude Code 风格）：

压缩层级：
1. 轻量压缩 (Light Compact / Microcompact) - 无 LLM 调用，仅清除旧工具结果
2. 重量压缩 (Heavy Compact) - LLM 生成 9 段结构化摘要

记忆层级：
1. 短期记忆 (Short-term)   — 保留最近 k 轮对话原文
2. 总结记忆 (Summary)      — 对更早的对话做 LLM 滚动摘要
"""

from __future__ import annotations

import os
import warnings
from typing import TYPE_CHECKING, Any

warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"langchain_classic")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

# ============== 配置常量 ==============

SHORT_TERM_K = 5  # 短期记忆保留最近 k 轮


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


# 上下文预算控制（可通过环境变量覆盖，默认200k）
MAX_CONTEXT_TOKENS = _get_env_int("WORDAGENT_MAX_CONTEXT_TOKENS", 200000)

# ============ LLMChainExtractor 语义压缩配置（默认禁用） ============
ENABLE_LLM_CHAIN_EXTRACTOR = os.environ.get("WORDAGENT_ENABLE_LLM_CHAIN_EXTRACTOR", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
EXTRACTOR_KEEP_RECENT_MESSAGES = _get_env_int("WORDAGENT_EXTRACTOR_KEEP_RECENT_MESSAGES", 4)
EXTRACTOR_MAX_SOURCE_MESSAGES = _get_env_int("WORDAGENT_EXTRACTOR_MAX_SOURCE_MESSAGES", 16)

# ============ Claude Code 风格的两级压缩配置 ============
# 轻量压缩 (Microcompact) - 无 LLM 调用
ENABLE_LIGHT_COMPACT = os.environ.get("WORDAGENT_ENABLE_LIGHT_COMPACT", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LIGHT_COMPACT_PROTECT_TOKENS = _get_env_int("WORDAGENT_LIGHT_COMPACT_PROTECT_TOKENS", 40000)  # 保护最近 40k tokens
LIGHT_COMPACT_MIN_TOOL_RESULTS = _get_env_int(
    "WORDAGENT_LIGHT_COMPACT_MIN_TOOL_RESULTS", 3
)  # 始终保留最后 3 个工具结果
LIGHT_COMPACT_MIN_SAVINGS = _get_env_int("WORDAGENT_LIGHT_COMPACT_MIN_SAVINGS", 20000)  # 至少节省 20k 才执行

# 重量压缩 (Heavy Compact) - LLM 生成结构化摘要
ENABLE_HEAVY_COMPACT = os.environ.get("WORDAGENT_ENABLE_HEAVY_COMPACT", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
HEAVY_COMPACT_TRIGGER_PCT = _get_env_int("WORDAGENT_HEAVY_COMPACT_TRIGGER_PCT", 93)  # 应用于 effective_window 的百分比
HEAVY_COMPACT_RESERVE_OUTPUT = _get_env_int("WORDAGENT_HEAVY_COMPACT_RESERVE_OUTPUT", 20000)  # 预留 20k 给输出
HEAVY_COMPACT_MAX_OUTPUT = _get_env_int("WORDAGENT_HEAVY_COMPACT_MAX_OUTPUT", 20000)  # 最大输出 20k
HEAVY_COMPACT_KEEP_RECENT_MSGS = _get_env_int("WORDAGENT_HEAVY_COMPACT_KEEP_RECENT", 4)  # 保留最近 N 条消息原文


# ============== 短期记忆 (ConversationBufferWindowMemory) ==============


def build_short_term_messages(
    history: list[dict],
    k: int = SHORT_TERM_K,
) -> list[HumanMessage | AIMessage]:
    """
    使用 ConversationBufferWindowMemory 提取最近 k 轮对话。
    """
    if not history:
        return []

    from langchain_classic.memory import ConversationBufferWindowMemory

    memory = ConversationBufferWindowMemory(k=k, return_messages=True)
    pairs = _pair_history(history)
    for user_msg, ai_msg in pairs:
        memory.save_context({"input": user_msg}, {"output": ai_msg})

    windowed = memory.load_memory_variables({}).get("history", [])
    return windowed if isinstance(windowed, list) else []


# ============== 总结记忆 (ConversationSummaryMemory) ==============


def build_summary_memory(
    history: list[dict],
    llm: "ChatOpenAI",
    k: int = SHORT_TERM_K,
) -> str:
    """
    使用 ConversationSummaryMemory 对短期记忆之前的对话生成渐进式摘要。
    """
    if not history:
        return ""

    pairs = _pair_history(history)
    if len(pairs) <= k:
        return ""

    older_pairs = pairs[: len(pairs) - k]
    if not older_pairs:
        return ""

    try:
        from langchain_classic.memory import ConversationSummaryMemory

        summary_memory = ConversationSummaryMemory(llm=llm)
        for user_msg, ai_msg in older_pairs:
            summary_memory.save_context({"input": user_msg}, {"output": ai_msg})

        summary = summary_memory.load_memory_variables({}).get("history", "")
        if summary:
            print(f"[Memory] ConversationSummaryMemory 生成摘要: {len(summary)} 字")
        return summary
    except Exception as e:
        print(f"[Memory] ⚠️ 生成摘要失败: {e}")
        return ""


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


def _extract_message_text(content) -> str:
    """Extract plain text from message content (str/dict/list)."""
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
            item_text = _extract_message_text(item)
            if item_text:
                parts.append(item_text)
        return "".join(parts)
    return str(content)


def _estimate_token_count(text: str) -> int:
    """
    Estimate token count with tiktoken (cl100k_base), fallback to char heuristic.
    使用 tiktoken 计算 token 数，避免使用字符串长度估算。
    """
    if not text:
        return 0

    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # CJK fallback: 1.7 chars/token, use conservative upper bound
        return max(1, int(len(text) / 1.7))


def _estimate_messages_tokens(messages: list[SystemMessage | HumanMessage | AIMessage | ToolMessage]) -> int:
    """Estimate total token count of a message list."""
    total = 0
    for msg in messages:
        role = "system" if isinstance(msg, SystemMessage) else "user" if isinstance(msg, HumanMessage) else "assistant"
        text = _extract_message_text(getattr(msg, "content", ""))
        # Reserve fixed overhead for role and message structure
        total += 6 + _estimate_token_count(role) + _estimate_token_count(text)
    return total


def _truncate_text(text: str, max_chars: int) -> str:
    """Truncate text by chars with a readable suffix."""
    if len(text) <= max_chars:
        return text
    keep = max(0, max_chars - 48)
    omitted = len(text) - keep
    return f"{text[:keep]}\n[内容过长，已截断 {omitted} 字符]"


def _truncate_message(msg: SystemMessage | HumanMessage | AIMessage | ToolMessage, max_chars: int):
    """Return same message type with truncated content if needed."""
    content = _extract_message_text(getattr(msg, "content", ""))
    new_text = _truncate_text(content, max_chars)

    if isinstance(msg, ToolMessage):
        return ToolMessage(content=new_text, tool_call_id=getattr(msg, "tool_call_id", ""))
    if isinstance(msg, HumanMessage):
        return HumanMessage(content=new_text)
    if isinstance(msg, AIMessage):
        return AIMessage(content=new_text)
    return SystemMessage(content=new_text)


def _message_role(msg: SystemMessage | HumanMessage | AIMessage) -> str:
    """Return normalized role name for a message object."""
    if isinstance(msg, HumanMessage):
        return "user"
    if isinstance(msg, AIMessage):
        return "assistant"
    return "system"


# ============ Claude Code 风格的轻量压缩 (Light Compact / Microcompact) ============
# 无 LLM 调用，仅清除旧工具结果


def _light_compact_tool_results(
    messages: list[SystemMessage | HumanMessage | AIMessage | ToolMessage],
    protect_tokens: int = LIGHT_COMPACT_PROTECT_TOKENS,
    protect_count: int = LIGHT_COMPACT_MIN_TOOL_RESULTS,
    min_savings: int = LIGHT_COMPACT_MIN_SAVINGS,
) -> tuple[list[SystemMessage | HumanMessage | AIMessage | ToolMessage], dict[str, Any]]:
    """
    轻量压缩：清除旧的工具结果，保留最近的工具结果。

    LangChain @tool 架构下的工具结果为 ToolMessage 类型。
    """
    meta: dict[str, Any] = {
        "light_compact_triggered": False,
        "cleared_tool_results": 0,
        "cleared_tokens": 0,
    }

    if not ENABLE_LIGHT_COMPACT:
        print(f"[Memory] 轻量压缩: 已禁用")
        return messages, meta

    # 分离消息：ToolMessage vs 其他
    tool_msgs: list[tuple[int, ToolMessage]] = []
    other_msgs: list[tuple[int, SystemMessage | HumanMessage | AIMessage]] = []

    for i, msg in enumerate(messages):
        if isinstance(msg, ToolMessage):
            tool_msgs.append((i, msg))
        else:
            other_msgs.append((i, msg))

    if len(tool_msgs) <= protect_count:
        print(f"[Memory] 轻量压缩: 跳过（ToolMessage {len(tool_msgs)} <= 保护数量 {protect_count}）")
        return messages, meta

    # 计算需要保护的 token：从后往前累加
    protected_indices: set[int] = set()
    protected_tokens = 0

    # 首先保护最后 N 个
    for idx, _ in tool_msgs[-protect_count:]:
        protected_indices.add(idx)

    # 从后往前，累加保护更多工具结果直到超过保护阈值
    for i in range(len(tool_msgs) - 1, -1, -1):
        idx, msg = tool_msgs[i]
        if idx in protected_indices:
            continue
        msg_tokens = _estimate_messages_tokens([msg])
        if protected_tokens + msg_tokens <= protect_tokens:
            protected_indices.add(idx)
            protected_tokens += msg_tokens
        else:
            break

    # 计算可以清除的内容
    clearable_tokens = 0
    clearable_indices: set[int] = set()
    for i, (idx, msg) in enumerate(tool_msgs):
        if idx not in protected_indices:
            clearable_indices.add(idx)
            clearable_tokens += _estimate_messages_tokens([msg])

    # 如果节省的不够，不执行
    if clearable_tokens < min_savings:
        print(f"[Memory] 轻量压缩: 跳过（可节省 {clearable_tokens} tokens < 最低要求 {min_savings}）")
        return messages, meta

    # 执行清除
    result: list[SystemMessage | HumanMessage | AIMessage | ToolMessage] = []
    cleared_count = 0
    for i, msg in enumerate(messages):
        if i in clearable_indices:
            result.append(ToolMessage(content="[工具结果已清除]", tool_call_id=getattr(msg, "tool_call_id", "")))
            cleared_count += 1
        else:
            result.append(msg)

    meta["light_compact_triggered"] = True
    meta["cleared_tool_results"] = cleared_count
    meta["cleared_tokens"] = clearable_tokens
    print(f"[Memory] 轻量压缩: 清除 {cleared_count} 个工具结果, 节省 ~{clearable_tokens} tokens")

    return result, meta


# ============ Claude Code 风格的重量压缩 (Heavy Compact) ============
# LLM 生成 9 段结构化摘要


def _extract_structured_summary(
    history: list[dict],
    llm: "ChatOpenAI",
    current_task: str = "",
    max_output_tokens: int = HEAVY_COMPACT_MAX_OUTPUT,
) -> str:
    """
    使用 LLM 生成 Claude Code 风格的 9 段结构化摘要。

    9 段结构：
    1. Primary Request and Intent - 用户的主要请求和意图
    2. Key Technical Concepts - 关键的技术概念
    3. Files and Code Sections - 文件和代码段
    4. Errors and Fixes - 错误和修复
    5. Problem Solving - 问题解决
    6. All User Messages - 所有用户消息
    7. Pending Tasks - 待办任务
    8. Current Work - 当前工作
    9. Next Steps - 下一步
    """
    if not history:
        return ""

    # 构建对话历史文本
    history_text = _format_history_for_summary(history)

    # 加载外部提示词模板
    from app.services.agent.prompts import get_compaction_summary_prompt

    prompt_template = get_compaction_summary_prompt()

    # 替换模板变量
    current_task_block = f"CURRENT TASK: {current_task}" if current_task else ""
    prompt = prompt_template.format(
        history_text=history_text,
        current_task=current_task_block,
    )

    try:
        # 使用 LangChain 的 invoke API，限制输出 token 数
        response = llm.invoke(
            [HumanMessage(content=prompt)],
            max_tokens=max_output_tokens,
        )
        summary = _extract_message_text(getattr(response, "content", ""))
        if summary:
            print(f"[Memory] 重量压缩生成摘要: {len(summary)} 字")
        return summary
    except Exception as e:
        print(f"[Memory] ⚠️ 生成结构化摘要失败: {e}")
        return ""


def _format_history_for_summary(history: list[dict]) -> str:
    """将历史记录格式化为可读的文本。"""
    lines = []
    total_chars = 0
    max_total_chars = 4000  # 总输入限制，避免 LLM 生成过多内容
    for i, msg in enumerate(history):
        role = msg.get("role", "unknown")
        content = _extract_message_text(msg.get("content", ""))
        if not content:
            continue
        # 每条消息截断到 800 字符，总量限制到 4000
        if len(content) > 800:
            content = content[:800] + f"\n[...截断，原 {len(content)} 字符]"
        entry = f"[{i + 1}] {role.upper()}: {content}"
        if total_chars + len(entry) > max_total_chars:
            break
        lines.append(entry)
        total_chars += len(entry)
    return "\n\n".join(lines)


def _heavy_compact_with_summary(
    messages: list[SystemMessage | HumanMessage | AIMessage | ToolMessage],
    history: list[dict],
    llm: "ChatOpenAI",
    current_task: str = "",
    keep_recent: int = HEAVY_COMPACT_KEEP_RECENT_MSGS,
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
) -> tuple[list[SystemMessage | HumanMessage | AIMessage], dict[str, Any]]:
    """
    重量压缩：使用 LLM 生成 9 段结构化摘要替换历史。

    类似 Claude Code 的 Full Compact：
    - 调用 LLM 生成结构化摘要
    - 保留最近的 N 条对话原文
    - 摘要 + 最近对话 替代 完整历史
    """
    meta: dict[str, Any] = {
        "heavy_compact_triggered": False,
        "summary_length": 0,
        "kept_recent_count": 0,
    }

    if not ENABLE_HEAVY_COMPACT or llm is None:
        return messages, meta

    before_tokens = _estimate_messages_tokens(messages)
    meta["before_tokens"] = before_tokens

    # 生成结构化摘要
    summary = _extract_structured_summary(history, llm, current_task)
    if not summary:
        print("[Memory] ⚠️ 重量压缩：未能生成摘要，回退")
        return messages, meta

    meta["summary_length"] = len(summary)

    # 分离系统消息和对话消息
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    convo_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

    # 保留最近的对话原文
    recent_msgs = convo_msgs[-keep_recent:] if keep_recent > 0 else []
    meta["kept_recent_count"] = len(recent_msgs)

    # 构建压缩后的消息
    summary_msg = SystemMessage(content=f"【对话历史摘要】\n{summary}")
    result = system_msgs + [summary_msg] + recent_msgs

    after_tokens = _estimate_messages_tokens(result)
    compression_ratio = (1 - after_tokens / before_tokens) * 100 if before_tokens > 0 else 0

    meta["heavy_compact_triggered"] = True
    meta["after_tokens"] = after_tokens
    meta["compression_ratio"] = compression_ratio

    print(f"[Memory] 重量压缩: {before_tokens} → {after_tokens} tokens (压缩 {compression_ratio:.1f}%)")

    return result, meta


# ============ 统一的压缩入口 ============


def compact_conversation(
    messages: list[SystemMessage | HumanMessage | AIMessage | ToolMessage],
    history: list[dict] | None = None,
    llm: "ChatOpenAI | None" = None,
    current_task: str = "",
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
    compact_level: str = "auto",
    current_input_tokens: int = 0,  # 优先使用 API 真实 input_tokens
) -> tuple[list[SystemMessage | HumanMessage | AIMessage], dict[str, Any]]:
    """
    统一的对话压缩入口，支持轻量和重量两级压缩。

    Args:
        messages: 当前消息列表
        history: 原始历史记录（用于重量压缩）
        llm: LLM 实例
        current_task: 当前任务描述
        max_context_tokens: 最大上下文 tokens
        compact_level: 压缩级别
            - "light": 仅轻量压缩
            - "heavy": 仅重量压缩（需要 LLM）
            - "auto": 自动选择（先轻量，不够再重量）
            - "both": 先轻量再重量

    Returns:
        (压缩后消息, 元数据)
    """
    meta: dict[str, Any] = {
        "level": compact_level,
        "light_compact": {},
        "heavy_compact": {},
    }

    current_messages = list(messages)
    # 优先使用 API 真实 input_tokens，比本地估算更准确
    current_tokens = current_input_tokens if current_input_tokens > 0 else _estimate_messages_tokens(current_messages)

    # 计算触发阈值（参考 Claude Code autoCompact.ts）
    # Claude Code: light compact 每次都执行（无阈值，只清理工具结果），heavy compact 才设阈值
    effective_window = max_context_tokens - HEAVY_COMPACT_RESERVE_OUTPUT
    heavy_trigger_threshold = int(effective_window * HEAVY_COMPACT_TRIGGER_PCT / 100)

    # 轻量压缩：每次都执行（清理旧工具结果，无 LLM 调用，成本极低）
    current_messages, light_meta = _light_compact_tool_results(current_messages)
    meta["light_compact"] = light_meta

    # 重量压缩：检查是否需要
    after_light_tokens = _estimate_messages_tokens(current_messages)
    need_heavy = after_light_tokens > heavy_trigger_threshold

    if compact_level in ("heavy", "both") or (compact_level == "auto" and need_heavy):
        if llm is None:
            print("[Memory] ⚠️ 重量压缩需要 LLM，但未提供，回退到 token 裁剪")
            # 回退到简单裁剪
            current_messages, hard_meta = _fit_memory_messages_to_budget(
                current_messages, llm=None, query=current_task, max_context_tokens=max_context_tokens
            )
            meta["hard_truncate"] = hard_meta
        else:
            # 使用 9 段摘要压缩
            current_messages, heavy_meta = _heavy_compact_with_summary(
                current_messages,
                history or [],
                llm,
                current_task,
                max_context_tokens=max_context_tokens,
            )
            meta["heavy_compact"] = heavy_meta

    # 最终检查：如果还是超限，执行硬裁剪
    final_tokens = _estimate_messages_tokens(current_messages)
    if final_tokens > max_context_tokens:
        current_messages, hard_meta = _fit_memory_messages_to_budget(
            current_messages, llm=None, query=current_task, max_context_tokens=max_context_tokens
        )
        meta["hard_truncate"] = hard_meta

    meta["final_tokens"] = _estimate_messages_tokens(current_messages)
    return current_messages, meta


def _compress_with_llm_chain_extractor(
    messages: list[SystemMessage | HumanMessage | AIMessage | ToolMessage],
    llm: "ChatOpenAI | None",
    query: str,
) -> list[SystemMessage | HumanMessage | AIMessage]:
    """Use LLMChainExtractor to keep only query-relevant parts of older dialogue."""
    if not ENABLE_LLM_CHAIN_EXTRACTOR or llm is None:
        return messages

    convo_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
    if len(convo_msgs) <= EXTRACTOR_KEEP_RECENT_MESSAGES:
        return messages

    try:
        from langchain_core.documents import Document
        from langchain_classic.retrievers.document_compressors import LLMChainExtractor
    except Exception as e:
        print(f"[Memory] ⚠️ LLMChainExtractor 不可用，跳过抽取压缩: {e}")
        return messages

    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    keep_recent = max(1, EXTRACTOR_KEEP_RECENT_MESSAGES)
    tail_msgs = convo_msgs[-keep_recent:]
    old_msgs = convo_msgs[:-keep_recent]

    if EXTRACTOR_MAX_SOURCE_MESSAGES > 0 and len(old_msgs) > EXTRACTOR_MAX_SOURCE_MESSAGES:
        old_msgs = old_msgs[-EXTRACTOR_MAX_SOURCE_MESSAGES:]

    docs = []
    for i, msg in enumerate(old_msgs):
        text = _extract_message_text(getattr(msg, "content", "")).strip()
        if not text:
            continue
        role = _message_role(msg)
        docs.append(Document(page_content=f"[{role}] {text}", metadata={"role": role, "idx": i}))

    if not docs:
        return messages

    question = (query or "").strip() or "请提取与当前任务最相关的上下文信息。"

    try:
        extractor = LLMChainExtractor.from_llm(llm)
        compressed_docs = extractor.compress_documents(docs, query=question)
    except Exception as e:
        print(f"[Memory] ⚠️ LLMChainExtractor 压缩失败，回退常规裁剪: {e}")
        return messages

    if not compressed_docs:
        return system_msgs + tail_msgs

    parts: list[str] = []
    for d in compressed_docs:
        content = (d.page_content or "").strip()
        if not content:
            continue
        role = str(d.metadata.get("role", "context"))
        parts.append(f"[{role}] {content}")

    if not parts:
        return system_msgs + tail_msgs

    compressed_context = (
        "以下为经 LLMChainExtractor 压缩后的较早历史上下文（仅保留与当前请求相关的信息）：\n" + "\n---\n".join(parts)
    )

    return system_msgs + [SystemMessage(content=compressed_context)] + tail_msgs


def _fit_memory_messages_to_budget(
    messages: list[SystemMessage | HumanMessage | AIMessage | ToolMessage],
    llm: "ChatOpenAI | None" = None,
    query: str = "",
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
) -> tuple[list[SystemMessage | HumanMessage | AIMessage], dict[str, Any]]:
    """Compress memory messages when token estimate exceeds configured budget."""
    meta: dict[str, Any] = {
        "triggered": False,
        "strategy": "none",
        "before_tokens_est": 0,
        "after_tokens_est": 0,
        "hard_budget": 0,
        "dropped_messages": 0,
    }

    if not messages:
        return messages, meta

    # Estimate tokens without single message truncation
    est_tokens = _estimate_messages_tokens(messages)
    meta["before_tokens_est"] = est_tokens

    hard_budget = max_context_tokens
    meta["hard_budget"] = hard_budget
    if est_tokens <= hard_budget:
        meta["after_tokens_est"] = est_tokens
        return messages, meta

    meta["triggered"] = True

    # Prefer LLMChainExtractor for semantic-preserving compression
    extracted = _compress_with_llm_chain_extractor(messages, llm=llm, query=query)
    extracted_tokens = _estimate_messages_tokens(extracted)
    if extracted_tokens <= hard_budget:
        meta["strategy"] = "llm_chain_extractor"
        meta["after_tokens_est"] = extracted_tokens
        return extracted, meta

    # Fallback to truncation if extraction still exceeds budget
    clipped = extracted
    system_msgs = [m for m in clipped if isinstance(m, SystemMessage)]
    convo_msgs = [m for m in clipped if not isinstance(m, SystemMessage)]

    selected_rev: list[HumanMessage | AIMessage] = []
    used = _estimate_messages_tokens(system_msgs)

    # Keep from most recent message, ensuring latest context is prioritized
    for msg in reversed(convo_msgs):
        msg_tokens = _estimate_messages_tokens([msg])
        if used + msg_tokens <= hard_budget:
            selected_rev.append(msg)
            used += msg_tokens
            continue

        if not selected_rev and used < hard_budget:
            # Truncate message to 35% of budget if single message exceeds
            max_chars = int(hard_budget * 2)  # rough estimate: 2 chars per token
            compact = _truncate_message(msg, max(200, min(max_chars, 4000)))
            compact_tokens = _estimate_messages_tokens([compact])
            if used + compact_tokens <= hard_budget:
                selected_rev.append(compact)
                used += compact_tokens
        break

    selected = list(reversed(selected_rev))
    dropped = len(convo_msgs) - len(selected)
    meta["dropped_messages"] = max(0, dropped)

    print(
        f"[Memory] 压缩调试: convo_msgs={len(convo_msgs)}, selected={len(selected)}, dropped={dropped}, system_msgs={len(system_msgs)}"
    )

    if dropped > 0:
        note = SystemMessage(
            content=(f"上下文压缩提示：为控制 token 预算，已压缩并省略较早的 {dropped} 条历史消息，优先保留最近对话。")
        )
        if _estimate_messages_tokens(system_msgs + [note] + selected) <= hard_budget:
            final_msgs = system_msgs + [note] + selected
            meta["strategy"] = "recent_keep_with_note"
            meta["after_tokens_est"] = _estimate_messages_tokens(final_msgs)
            return final_msgs, meta

    final_msgs = system_msgs + selected
    meta["strategy"] = "recent_keep"
    meta["after_tokens_est"] = _estimate_messages_tokens(final_msgs)
    return final_msgs, meta


# ============ [新增] 实时上下文压缩（ReAct 循环中调用） ============


def compress_conversation_history_if_needed(
    messages: list,
    llm: "ChatOpenAI | None" = None,
    query: str = "",
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
    compact_level: str = "auto",
    history: list[dict] | None = None,
    current_input_tokens: int = 0,  # 优先使用 API 真实 input_tokens，否则回退到本地估算
) -> tuple[list, dict[str, Any]]:
    """
    检测消息列表 token 数是否超过上限，超过则压缩。

    支持两种压缩模式（类 Claude Code 风格）：
    1. 轻量压缩 (light) - 无 LLM 调用，仅清除旧工具结果
    2. 重量压缩 (heavy) - LLM 生成 9 段结构化摘要

    Args:
        messages: 消息列表
        llm: LLM 实例（用于重量压缩）
        query: 当前查询（用于压缩参考）
        max_context_tokens: 最大上下文 tokens
        compact_level: 压缩级别
            - "light": 仅轻量压缩
            - "heavy": 仅重量压缩（需要 LLM）
            - "auto": 自动选择（先轻量，不够再重量，默认）
            - "both": 先轻量再重量
        history: 原始对话历史（dict 列表），用于重量压缩生成正确的摘要
        current_input_tokens: API 真实 input_tokens（优先于本地估算）

    Returns:
        (压缩后消息, 元数据)
        元数据包含 triggered=True 时表示触发了压缩
    """
    from langchain_core.messages import HumanMessage

    # 转换：如果传入的是普通 list（非 langchain message 类型），转为 HumanMessage
    converted = []
    for m in messages:
        if isinstance(m, (SystemMessage, HumanMessage, AIMessage)):
            converted.append(m)
        elif isinstance(m, dict):
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                converted.append(SystemMessage(content=content))
            elif role == "user":
                converted.append(HumanMessage(content=content))
            else:
                converted.append(AIMessage(content=content))
        else:
            converted.append(HumanMessage(content=str(m)))

    # 使用新的两级压缩
    return compact_conversation(
        messages=converted,
        history=history,
        llm=llm,
        current_task=query,
        max_context_tokens=max_context_tokens,
        compact_level=compact_level,
        current_input_tokens=current_input_tokens,
    )


# ============== 统一记忆注入接口 ==============


def build_memory_messages(
    history: list[dict] | None,
    current_message: str,
    llm: "ChatOpenAI | None" = None,
    session_id: str | None = None,
    enable_summary: bool = True,
    enable_long_term: bool = False,  # 已废弃参数，保留接口兼容
    return_meta: bool = False,
) -> (
    list[SystemMessage | HumanMessage | AIMessage]
    | tuple[list[SystemMessage | HumanMessage | AIMessage], dict[str, Any]]
):
    """
    构建包含两层记忆的消息列表，供 Agent 注入。

    已移除：长期记忆 (RAG/FAISS) 注入

    Args:
        history: 前端传入的历史消息列表
        current_message: 当前用户消息（用于压缩参考）
        llm: LLM 实例（用于生成摘要和压缩）
        session_id: 会话 ID（已废弃，仅保留接口兼容）
        enable_summary: 是否启用总结记忆
        enable_long_term: 已废弃参数（长期记忆已移除），传入无效
        return_meta: 是否返回压缩元数据

    Returns:
        按顺序排列的消息列表: [摘要上下文, 短期对话历史]
    """
    result_messages: list[SystemMessage | HumanMessage | AIMessage] = []

    # 1) 总结记忆 — 对短期记忆之前的对话做摘要
    if enable_summary and history and llm:
        try:
            summary = build_summary_memory(history, llm)
            if summary:
                result_messages.append(SystemMessage(content=f"以下是之前对话的摘要（供上下文参考）：\n{summary}"))
        except Exception as e:
            print(f"[Memory] ⚠️ 摘要记忆注入失败: {e}")

    # 2) 短期记忆 — 最近 k 轮原文
    if history:
        short_term = build_short_term_messages(history, k=SHORT_TERM_K)
        if short_term:
            result_messages.extend(short_term)
            print(f"[Memory] 注入 {len(short_term)} 条短期记忆")

    # 上下文预算压缩
    compressed, compression_meta = _fit_memory_messages_to_budget(
        result_messages,
        llm=llm,
        query=current_message,
    )
    if compression_meta.get("triggered"):
        print(
            "[Memory] 上下文压缩触发:",
            {
                "before_messages": len(result_messages),
                "after_messages": len(compressed),
                "before_tokens_est": compression_meta.get("before_tokens_est", 0),
                "after_tokens_est": compression_meta.get("after_tokens_est", 0),
                "hard_budget": compression_meta.get("hard_budget", 0),
                "strategy": compression_meta.get("strategy", "none"),
                "dropped_messages": compression_meta.get("dropped_messages", 0),
                "max_context_tokens": MAX_CONTEXT_TOKENS,
                "extractor_enabled": ENABLE_LLM_CHAIN_EXTRACTOR,
            },
        )

    if return_meta:
        return compressed, compression_meta
    return compressed
