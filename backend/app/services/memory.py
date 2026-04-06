"""
对话记忆管理模块

提供三层记忆机制，注入到 Agent 的 messages 中：
1. 短期记忆 (Short-term)   — ConversationBufferWindowMemory(k=5)，保留最近 k 轮对话原文
2. 总结记忆 (Summary)      — ConversationSummaryMemory，对更早的对话做 LLM 滚动摘要
3. 长期记忆 (Long-term/RAG) — FAISS 向量库语义检索

当前默认配置：长期记忆已临时关闭（见 ENABLE_LONG_TERM_MEMORY）。
"""

from __future__ import annotations

import time
import warnings
from typing import TYPE_CHECKING

# 屏蔽 langchain_classic 的弃用警告（功能正常，仅提示迁移）
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"langchain_classic")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

from app.core.config import get_data_dir

# ============== 配置常量 ==============

SHORT_TERM_K = 5  # 短期记忆保留最近 k 轮 (user+assistant 为一轮)
LONG_TERM_TOP_K = 3  # RAG 检索返回 top-k 条
# 临时开关：默认关闭长期记忆（RAG）注入与存储
ENABLE_LONG_TERM_MEMORY = False

# FAISS 向量库持久化目录
_FAISS_INDEX_DIR = get_data_dir() / "memory_faiss_index"
_FAISS_PKL_FILE = _FAISS_INDEX_DIR / "index.pkl"  # 用 Python 序列化，规避中文路径问题

# ============== 向量库单例 ==============

_vectorstore = None
_embedding_fn = None


def _get_embedding_fn():
    """
    获取嵌入函数。
    当前直接使用 FakeEmbeddings（无需外部 embedding 服务）。
    """
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn

    _embedding_fn = _make_fake_embeddings()
    return _embedding_fn


def _make_fake_embeddings():
    """创建 FakeEmbeddings 作为回退方案。"""
    from langchain_core.embeddings import FakeEmbeddings

    print("[Memory] 使用 langchain FakeEmbeddings（无语义能力，仅基础向量存储）")
    return FakeEmbeddings(size=128)


def _get_vectorstore():
    """获取/初始化 FAISS 向量库"""
    global _vectorstore, _embedding_fn
    if _vectorstore is not None:
        return _vectorstore

    try:
        from langchain_community.vectorstores import FAISS

        embedding = _get_embedding_fn()

        if _FAISS_PKL_FILE.exists():
            # 用 Python 原生文件 I/O 读取，规避 FAISS C++ 不支持中文路径的问题
            data = _FAISS_PKL_FILE.read_bytes()
            _vectorstore = FAISS.deserialize_from_bytes(data, embedding, allow_dangerous_deserialization=True)
            print(f"[Memory] FAISS 向量库已从磁盘加载: {_FAISS_PKL_FILE}")
        else:
            _FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
            _vectorstore = FAISS.from_texts(
                ["[系统初始化] WenCe AI Writing Assistant 长期记忆库已创建"],
                embedding,
                metadatas=[{"session_id": "system", "role": "system", "timestamp": time.time()}],
            )
            _save_vectorstore(_vectorstore)
            print(f"[Memory] FAISS 向量库已初始化: {_FAISS_PKL_FILE}")

        return _vectorstore
    except Exception as e:
        print(f"[Memory] ⚠️ FAISS 向量库初始化失败: {e}")
        return None


def _save_vectorstore(store):
    """用 Python 原生文件 I/O 持久化 FAISS 索引（支持中文路径）。"""
    try:
        _FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
        data = store.serialize_to_bytes()
        _FAISS_PKL_FILE.write_bytes(data)
    except Exception as e:
        print(f"[Memory] ⚠️ FAISS 向量库持久化失败: {e}")


# ============== 短期记忆 (ConversationBufferWindowMemory) ==============


def build_short_term_messages(
    history: list[dict],
    k: int = SHORT_TERM_K,
) -> list[HumanMessage | AIMessage]:
    """
    使用 ConversationBufferWindowMemory 提取最近 k 轮对话。

    Args:
        history: 前端传入的 [{role, content}, ...] 列表
        k: 保留的最近轮数（1 轮 = 1 user + 1 assistant）

    Returns:
        LangChain 消息列表
    """
    if not history:
        return []

    from langchain_classic.memory import ConversationBufferWindowMemory

    memory = ConversationBufferWindowMemory(k=k, return_messages=True)

    # save_context 需要 input/output 对，自动只保留最近 k 轮
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

    Args:
        history: 完整历史消息列表
        llm: LLM 实例（用于生成摘要）
        k: 短期记忆保留轮数（之前的消息做摘要）

    Returns:
        摘要文本，如果无需摘要则返回空字符串
    """
    if not history:
        return ""

    pairs = _pair_history(history)
    if len(pairs) <= k:
        # 总对话不超过短期记忆容量，无需摘要
        return ""

    # 取短期记忆之前的对话对
    older_pairs = pairs[: len(pairs) - k]
    if not older_pairs:
        return ""

    try:
        from langchain_classic.memory import ConversationSummaryMemory

        summary_memory = ConversationSummaryMemory(llm=llm)

        # 逐对加载，ConversationSummaryMemory 自动做渐进式摘要
        for user_msg, ai_msg in older_pairs:
            summary_memory.save_context({"input": user_msg}, {"output": ai_msg})

        summary = summary_memory.load_memory_variables({}).get("history", "")
        if summary:
            print(f"[Memory] ConversationSummaryMemory 生成摘要: {len(summary)} 字")
        return summary
    except Exception as e:
        print(f"[Memory] ⚠️ 生成摘要失败: {e}")
        return ""


# ============== 长期记忆 (RAG) ==============


def store_to_long_term(
    session_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
):
    """将一条消息存入 FAISS 长期向量记忆。"""
    if not ENABLE_LONG_TERM_MEMORY:
        return

    store = _get_vectorstore()
    if store is None:
        return

    # 跳过过短的消息
    if len(content.strip()) < 10:
        return

    doc_metadata = {
        "session_id": str(session_id),
        "role": role,
        "timestamp": time.time(),
    }
    if metadata:
        doc_metadata.update(metadata)

    try:
        store.add_texts(texts=[content], metadatas=[doc_metadata])
        # 持久化到磁盘
        _save_vectorstore(store)
    except Exception as e:
        print(f"[Memory] ⚠️ 存入长期记忆失败: {e}")


def retrieve_from_long_term(
    query: str,
    top_k: int = LONG_TERM_TOP_K,
) -> list[dict]:
    """从 FAISS 长期记忆中检索与 query 语义相关的历史消息。"""
    if not ENABLE_LONG_TERM_MEMORY:
        return []

    store = _get_vectorstore()
    if store is None:
        return []

    try:
        results = store.similarity_search_with_score(query, k=top_k)

        retrieved = []
        for doc, score in results:
            retrieved.append(
                {
                    "content": doc.page_content,
                    "role": doc.metadata.get("role", "unknown"),
                    "session_id": doc.metadata.get("session_id", ""),
                    "score": float(score),
                }
            )
        return retrieved
    except Exception as e:
        print(f"[Memory] ⚠️ 长期记忆检索失败: {e}")
        return []


# ============== 工具函数 ==============


def _pair_history(history: list[dict]) -> list[tuple[str, str]]:
    """
    将 history 列表配对为 (user_msg, assistant_msg) 元组列表。
    ConversationBufferWindowMemory / ConversationSummaryMemory 的
    save_context 需要 input/output 对。
    """
    pairs = []
    i = 0
    valid = [
        h
        for h in history
        if h.get("content") and isinstance(h["content"], str) and h.get("role") in ("user", "assistant")
    ]
    while i < len(valid) - 1:
        if valid[i]["role"] == "user" and valid[i + 1]["role"] == "assistant":
            pairs.append((valid[i]["content"], valid[i + 1]["content"]))
            i += 2
        else:
            i += 1
    return pairs


# ============== 统一记忆注入接口 ==============


def build_memory_messages(
    history: list[dict] | None,
    current_message: str,
    llm: "ChatOpenAI | None" = None,
    session_id: str | None = None,
    enable_summary: bool = True,
    enable_long_term: bool = False,
) -> list[SystemMessage | HumanMessage | AIMessage]:
    """
    构建包含三层记忆的消息列表，供 Agent 注入。

    返回的消息应插入到 system prompt 之后、当前用户消息之前。

    Args:
        history: 前端传入的历史消息列表
        current_message: 当前用户消息（用于 RAG 检索）
        llm: LLM 实例（用于生成摘要，None 时跳过摘要）
        session_id: 会话 ID（用于长期记忆检索）
        enable_summary: 是否启用总结记忆
        enable_long_term: 是否启用长期记忆（受 ENABLE_LONG_TERM_MEMORY 总开关控制）

    Returns:
        按顺序排列的消息列表: [长期记忆上下文, 摘要上下文, 短期对话历史]
    """
    result_messages: list[SystemMessage | HumanMessage | AIMessage] = []

    # 1) 长期记忆 (RAG) — 最先注入，作为背景知识
    if ENABLE_LONG_TERM_MEMORY and enable_long_term and current_message:
        try:
            retrieved = retrieve_from_long_term(query=current_message)
            if retrieved:
                rag_parts = []
                for item in retrieved:
                    rag_parts.append(f"[{item['role']}] {item['content']}")
                rag_context = "\n---\n".join(rag_parts)
                result_messages.append(
                    SystemMessage(
                        content=(
                            "以下是从历史对话中检索到的相关记忆片段，可作为参考背景（不一定与当前请求直接相关）：\n"
                            f"{rag_context}"
                        )
                    )
                )
                print(f"[Memory] 注入 {len(retrieved)} 条长期记忆")
        except Exception as e:
            print(f"[Memory] ⚠️ 长期记忆注入失败: {e}")

    # 2) 总结记忆 — 对短期记忆之前的对话做摘要
    if enable_summary and history and llm:
        try:
            summary = build_summary_memory(history, llm)
            if summary:
                result_messages.append(SystemMessage(content=f"以下是之前对话的摘要（供上下文参考）：\n{summary}"))
        except Exception as e:
            print(f"[Memory] ⚠️ 摘要记忆注入失败: {e}")

    # 3) 短期记忆 — 最近 k 轮原文
    if history:
        short_term = build_short_term_messages(history, k=SHORT_TERM_K)
        if short_term:
            result_messages.extend(short_term)
            print(f"[Memory] 注入 {len(short_term)} 条短期记忆")

    return result_messages


def store_conversation_to_long_term(
    session_id: str,
    user_message: str,
    assistant_message: str,
    model: str | None = None,
    mode: str | None = None,
):
    """
    将一轮对话（user + assistant）存入长期记忆。
    应在 Agent 完成响应后调用。

    Args:
        session_id: 会话 ID
        user_message: 用户消息
        assistant_message: AI 回复
        model: 使用的模型
        mode: 使用的模式
    """
    meta = {}
    if model:
        meta["model"] = model
    if mode:
        meta["mode"] = mode

    store_to_long_term(session_id, "user", user_message, metadata=meta)
    store_to_long_term(session_id, "assistant", assistant_message, metadata=meta)
