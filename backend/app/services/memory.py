"""
对话记忆管理模块

提供两层记忆机制，注入到 Agent 的 messages 中：
1. 短期记忆 (Short-term)   — ConversationBufferWindowMemory(k=5)，保留最近 k 轮对话原文
2. 总结记忆 (Summary)      — ConversationSummaryMemory，对更早的对话做 LLM 滚动摘要
"""

from __future__ import annotations

import os
import warnings
from typing import TYPE_CHECKING, Any

warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"langchain_classic")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

# ============== 配置常量 ==============

SHORT_TERM_K = 5  # 短期记忆保留最近 k 轮 (user+assistant 为一轮)

# 已移除：LONG_TERM_TOP_K 和 ENABLE_LONG_TERM_MEMORY


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

# 上下文压缩配置（用于 LLMChainExtractor 语义压缩）
ENABLE_LLM_CHAIN_EXTRACTOR = os.environ.get("WORDAGENT_ENABLE_LLM_CHAIN_EXTRACTOR", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
EXTRACTOR_KEEP_RECENT_MESSAGES = _get_env_int("WORDAGENT_EXTRACTOR_KEEP_RECENT_MESSAGES", 4)
EXTRACTOR_MAX_SOURCE_MESSAGES = _get_env_int("WORDAGENT_EXTRACTOR_MAX_SOURCE_MESSAGES", 16)


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


def _estimate_messages_tokens(messages: list[SystemMessage | HumanMessage | AIMessage]) -> int:
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


def _truncate_message(msg: SystemMessage | HumanMessage | AIMessage, max_chars: int):
    """Return same message type with truncated content if needed."""
    content = _extract_message_text(getattr(msg, "content", ""))
    new_text = _truncate_text(content, max_chars)

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


def _compress_with_llm_chain_extractor(
    messages: list[SystemMessage | HumanMessage | AIMessage],
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
    messages: list[SystemMessage | HumanMessage | AIMessage],
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

    print(f"[Memory] 压缩调试: convo_msgs={len(convo_msgs)}, selected={len(selected)}, dropped={dropped}, system_msgs={len(system_msgs)}")

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
) -> tuple[list, dict[str, Any]]:
    """
    检测消息列表 token 数是否超过上限，超过则压缩。
    返回 (压缩后消息, 元数据)。
    元数据包含 triggered=True 时表示触发了压缩。
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

    return _fit_memory_messages_to_budget(converted, llm=llm, query=query, max_context_tokens=max_context_tokens)


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

    # [已移除] 长期记忆 (RAG) 注入段
    # 之前的代码：retrieve_from_long_term() → 不再执行

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


# ============== [已废弃] 长期记忆存储接口 ==============
# 以下函数已删除：store_conversation_to_long_term()
# 如有其他模块依赖，请使用 stub 函数保持兼容


def store_conversation_to_long_term(
    session_id: str,
    user_message: str,
    assistant_message: str,
    model: str | None = None,
    mode: str | None = None,
):
    """
    [已废弃] 长期记忆存储功能已移除。

    此函数保留为 stub 以避免破坏依赖此接口的代码。
    调用此函数将无任何效果。
    """
    # 已移除 FAISS 长期记忆存储逻辑
    # 如需对话历史管理，请依赖 build_memory_messages 中的短期/总结记忆
    pass


def retrieve_from_long_term(
    query: str,
    top_k: int = 3,
) -> list[dict]:
    """
    [已废弃] 长期记忆检索功能已移除。

    此函数保留为 stub 以避免破坏依赖此接口的代码。
    始终返回空列表。
    """
    return []


def store_to_long_term(
    session_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    """
    [已废弃] 长期记忆存储功能已移除。

    此函数保留为 stub 以避免破坏依赖此接口的代码。
    调用此函数将无任何效果。
    """
    pass
