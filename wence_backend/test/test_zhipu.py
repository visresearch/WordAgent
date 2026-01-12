import os
from dotenv import load_dotenv
from zai import ZhipuAiClient

# 加载 .env 文件
load_dotenv()

# 从环境变量获取 API Key
client = ZhipuAiClient(api_key=os.getenv("ZHIPU_API_KEY"))

# 创建流式聊天完成请求
response = client.chat.completions.create(
    model="glm-4.7",
    messages=[
        {
            "role": "system",
            "content": "你是一个有用的AI助手。"
        },
        {
            "role": "user",
            "content": "你好，请介绍一下自己。"
        }
    ],
    temperature=0.6,
    stream=True  # 开启流式输出
)

# 流式获取回复
for chunk in response:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)

print()  # 换行