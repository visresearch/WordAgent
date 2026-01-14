"""检查智谱AI返回的模型ID"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("ZHIPU_API_KEY"), base_url="https://open.bigmodel.cn/api/paas/v4/")

models = client.models.list()

print("智谱AI 返回的模型列表：")
print("-" * 50)
for m in models.data:
    print(f"  {m.id}")
