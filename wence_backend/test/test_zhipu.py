"""
测试 ChatZhipuAI (GLM-4.7) 流式输出
使用 langchain_community.chat_models.ChatZhipuAI
"""

import asyncio
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage, SystemMessage

# ----------------------------
# 配置 GLM-4.7
# ----------------------------
ZHIPU_API_KEY = "41b690b26fe74fa18d57ad823d79f271.W14hEicmUiCvwrJZ"

llm = ChatZhipuAI(
    model="glm-4.7",
    api_key=ZHIPU_API_KEY,
    temperature=0.7,
    streaming=True,
)


# ----------------------------
# 测试1: 流式输出
# ----------------------------
async def test_stream():
    print("=" * 60)
    print("🚀 测试: ChatZhipuAI GLM-4.7 流式输出")
    print("=" * 60)

    messages = [
        SystemMessage(content="你是一个诗人"),
        HumanMessage(content="写一首关于编程的短诗"),
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
# 测试2: 非流式输出
# ----------------------------
async def test_invoke():
    print("=" * 60)
    print("🔸 测试: ChatZhipuAI GLM-4.7 非流式输出")
    print("=" * 60)

    messages = [
        HumanMessage(content="简短说明什么是人工智能"),
    ]
    response = await llm.ainvoke(messages)
    print(response.content)

    print("=" * 60 + "\n")


# ----------------------------
# 运行测试
# ----------------------------
async def main():
    print("\n🎯 ChatZhipuAI GLM-4.7 测试\n")
    await test_stream()
    await test_invoke()
    print("✨ 所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
