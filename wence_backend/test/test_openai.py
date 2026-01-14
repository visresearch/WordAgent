"""
测试 OpenAI API 连接
"""

import asyncio

from openai import AsyncOpenAI

# # 配置
# API_KEY = "sk-l4ET3MWX8vsqAVqv0tXt5o1bbc7sh5L1fDV7oV66oDPrxLlQ"
# BASE_URL = "https://api.chatanywhere.tech"
# MODEL = "gpt-5"

API_KEY = ""
BASE_URL = "http://localhost:11434/v1"
# MODEL = "qwen2.5:7b"  # 或 deepseek-r1:7b
MODEL = "deepseek-r1:7b"  # 或 deepseek-r1:7b


async def test_stream():
    """测试流式响应"""
    print("=" * 50)
    print("测试 OpenAI 流式 API")
    print(f"API Base: {BASE_URL}")
    print(f"Model: {MODEL}")
    print("=" * 50)

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

    try:
        print("\n发送请求中...\n")
        print("AI 回复: ", end="", flush=True)

        stream = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "你是一个友好的助手"},
                {"role": "user", "content": "你好，请简单介绍一下自己，用2-3句话"},
            ],
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)

        print("\n\n" + "=" * 50)
        print("✅ 测试成功！流式 API 工作正常")
        print("=" * 50)

    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        print(f"错误类型: {type(e).__name__}")


if __name__ == "__main__":
    asyncio.run(test_stream())
