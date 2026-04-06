# 配置 API Key

文策 AI 需要连接 LLM 大模型服务才能工作，你需要提供自己的 API Key。

## 获取 API Key

目前推荐使用以下服务商（运行稳定）：

| 服务商 | 推荐模型 | 获取地址 |
|---|---|---|
| 阿里云百炼 | Qwen 3.6 Plus | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/) |
| 2Coding | 多种模型 | [2coding.com](https://2coding.com/) |
| OpenRouter | 多种模型 | [openrouter.ai](https://openrouter.ai/) |

## 填写配置

1. 启动后端服务后，打开 Word 中的文策 AI 加载项面板
2. 点击面板中的 **设置**（齿轮图标）按钮
3. 填写以下信息：
   - **API Key**：你从服务商处获取的 API 密钥
   - **Base URL**：服务商的 API 地址（如阿里云百炼为 `https://dashscope.aliyuncs.com/compatible-mode/v1`）
   - **API类型**：根据你要使用的模型选择对应的API类型(如Qwen 3.6 Plus选择 `OpenAPI 兼容`，Claude Sonnet 4.6选择 `Anthropic`)。
4. 点击 **获取模型列表** 按钮，选择你要使用的模型（如 Qwen 3.6 Plus）
5. 在已添加的模型列表中，把刚刚添加的模型点击切换启用按钮
6. 点击 **保存** 完成配置，方可在聊天面板中看到刚刚添加的模型。

![](/model_setting.png)

::: tip 提示
API Key 保存在本地，不会上传到任何服务器。
:::
