"""
纯 LangChain 流式输出测试（不用 LangGraph）
演示如何用 LangChain 实现简单高效的流式输出
"""
import asyncio
import sys
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 添加父目录到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings

# ----------------------------
# 1️⃣ 配置 LLM
# ----------------------------
llm = ChatOpenAI(
    model="qwen2.5:7b",
    base_url=settings.OLLAMA_BASE_URL,
    api_key=settings.OLLAMA_API_KEY,
    temperature=0.7,
)

# ----------------------------
# 2️⃣ 测试流式输出（推荐）
# ----------------------------
async def test_astream():
    """使用 astream() 异步流式输出"""
    print("=" * 60)
    print("🚀 测试1: astream() - 异步流式输出")
    print("=" * 60)
    
    messages = [
        SystemMessage(content="你是一个诗人"),
        HumanMessage(content="写一首关于编程的短诗")
    ]
    
    accumulated = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            accumulated += chunk.content
    
    print("\n" + "=" * 60)
    print(f"✅ 输出完成，共 {len(accumulated)} 字符")
    print("=" * 60 + "\n")


# ----------------------------
# 3️⃣ 测试流式输出 + Tool Calling
# ----------------------------
async def test_astream_with_tools():
    """流式输出 + 工具调用"""
    from langchain_core.tools import tool
    
    @tool
    def get_weather(city: str) -> str:
        """获取城市天气"""
        return f"{city}今天晴天，25度"
    
    llm_with_tools = llm.bind_tools([get_weather])
    
    print("=" * 60)
    print("🚀 测试2: astream() + Tool Calling")
    print("=" * 60)
    
    messages = [HumanMessage(content="北京天气怎么样？")]
    
    async for chunk in llm_with_tools.astream(messages):
        # 文字内容
        if chunk.content:
            print(chunk.content, end="", flush=True)
        
        # 工具调用
        if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
            print(f"\n[Tool Call] {chunk.tool_calls}")
    
    print("\n" + "=" * 60)
    print("✅ 流式输出 + 工具调用完成")
    print("=" * 60 + "\n")


# ----------------------------
# 4️⃣ 测试 astream_events（更细粒度）
# ----------------------------
async def test_astream_events():
    """使用 astream_events 获取更多细节"""
    print("=" * 60)
    print("🚀 测试3: astream_events() - 事件流")
    print("=" * 60)
    
    messages = [HumanMessage(content="简短说明什么是AI")]
    
    async for event in llm.astream_events(messages, version="v2"):
        event_type = event.get("event")
        
        if event_type == "on_chat_model_start":
            print("\n[开始] 模型开始生成...\n")
        
        elif event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and chunk.content:
                print(chunk.content, end="", flush=True)
        
        elif event_type == "on_chat_model_end":
            print("\n\n[结束] 模型生成完成")
    
    print("=" * 60 + "\n")


# ----------------------------
# 5️⃣ 对比：非流式输出
# ----------------------------
async def test_invoke():
    """非流式输出（一次性返回）"""
    print("=" * 60)
    print("🔸 对比: invoke() - 非流式（一次性返回）")
    print("=" * 60)
    
    messages = [HumanMessage(content="简短说明什么是AI")]
    response = await llm.ainvoke(messages)
    
    print(response.content)
    print("=" * 60 + "\n")


# ----------------------------
# 6️⃣ 运行所有测试
# ----------------------------
async def main():
    print("\n🎯 LangChain 流式输出测试\n")
    
    # 测试1：基础流式
    await test_astream()
    
    # 测试2：流式 + 工具
    await test_astream_with_tools()
    
    # 测试3：事件流
    await test_astream_events()
    
    # 测试4：非流式对比
    await test_invoke()
    
    print("✨ 所有测试完成！\n")
    print("💡 结论：纯 LangChain 流式输出简单高效，无需 LangGraph")


if __name__ == "__main__":
    asyncio.run(main())
