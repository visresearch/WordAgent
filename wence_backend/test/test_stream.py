"""
LangGraph 流式输出测试 - 使用 astream_events() 捕获 token
演示如何在 LangGraph 中获取实时流式输出
"""
import asyncio
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage

# ----------------------------
# 1️⃣ 定义状态
# ----------------------------
class State(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

# ----------------------------
# 2️⃣ 配置 LLM（流式输出）
# ----------------------------
llm = ChatOpenAI(
    model="gpt-4o",
    base_url="https://api.chatanywhere.tech",
    api_key="sk-l4ET3MWX8vsqAVqv0tXt5o1bbc7sh5L1fDV7oV66oDPrxLlQ",  # 替换成你的 API key
    streaming=True,  # 🔥 关键：启用流式
    temperature=0.7,
)

# ----------------------------
# 3️⃣ 定义 Graph Node（异步版本，支持流式）
# ----------------------------
async def chat_node(state: State) -> State:
    """
    调用 LLM 处理消息（异步流式）
    ⚠️ 注意：必须是异步函数，且用 astream() 才能产生流式事件
    """
    messages = state["messages"]
    
    # 必须用 astream() 才能让 astream_events() 捕获到流式 token
    content = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            content += chunk.content
    
    # 构造完整的消息
    from langchain_core.messages import AIMessage
    response = AIMessage(content=content)
    return {"messages": [response]}

# ----------------------------
# 4️⃣ 构建 StateGraph
# ----------------------------
def create_graph():
    graph = StateGraph(State)
    graph.add_node("chat", chat_node)
    graph.set_entry_point("chat")
    graph.add_edge("chat", END)
    return graph.compile()

# ----------------------------
# 5️⃣ 测试函数：使用 astream_events 捕获流式 token
# ----------------------------
async def test_stream():
    app = create_graph()
    
    # 初始状态
    initial_state = {
        "messages": [
            SystemMessage(content="你是一个友好的助手"),
            HumanMessage(content="请用流式方式输出一首关于春天的诗")
        ]
    }
    
    print("=" * 50)
    print("🚀 开始流式输出")
    print("=" * 50)
    
    accumulated = ""
    
    # 使用 astream_events 捕获所有事件
    async for event in app.astream_events(initial_state, version="v2"):
        event_type = event.get("event")
        
        # 捕获 LLM 流式输出的每个 token
        if event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                print(chunk.content, end="", flush=True)
                accumulated += chunk.content
    
    print("\n" + "=" * 50)
    print("✅ 流式输出完成")
    print(f"📝 总共输出了 {len(accumulated)} 个字符")
    print("=" * 50)

# ----------------------------
# 6️⃣ 测试函数：不使用流式（对比）
# ----------------------------
async def test_no_stream():
    app = create_graph()
    
    initial_state = {
        "messages": [
            SystemMessage(content="你是一个友好的助手"),
            HumanMessage(content="请简短回答：什么是AI？")
        ]
    }
    
    print("\n" + "=" * 50)
    print("🔸 非流式输出（一次性返回）")
    print("=" * 50)
    
    result = await app.ainvoke(initial_state)
    final_message = result["messages"][-1]
    print(final_message.content)
    print("=" * 50)

# ----------------------------
# 7️⃣ 运行测试
# ----------------------------
async def main():
    print("\n🎯 测试1：流式输出（打字机效果）\n")
    await test_stream()
    
    print("\n🎯 测试2：非流式输出（对比）\n")
    await test_no_stream()
    
    print("\n✨ 所有测试完成！\n")

if __name__ == "__main__":
    asyncio.run(main())

