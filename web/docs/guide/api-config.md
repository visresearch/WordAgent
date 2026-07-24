# 配置大模型服务

文策 AI 需要连接支持工具调用的 LLM 服务。API Key、Base URL 和模型配置保存在本机，不会上传到文策 AI 的服务器。

## 推荐服务商

| 服务商 | 推荐模型 | 获取地址 |
|---|---|---|
| DeepSeek 官方 | **DeepSeek V4 Pro（推荐）** | [platform.deepseek.com](https://platform.deepseek.com/) |
| 阿里云百炼 | Qwen 3.6 Plus | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/) |
| OpenRouter | 多种 OpenAI 兼容模型 | [openrouter.ai](https://openrouter.ai/) |

模型必须支持 Tool Calling。不同服务商展示的模型名称和模型 ID 可能不同，请以服务商控制台和“获取模型列表”的实际结果为准。

## 使用 DeepSeek V4 Pro 配置

以下以 **DeepSeek 官方 API 提供的 DeepSeek V4 Pro** 为例：

1. 启动文策 AI 后端，并在 WPS Word 或 Microsoft Word 中打开文策 AI 面板。
2. 点击 **设置 → 大模型 → 添加提供商**。
3. 填写提供商配置：
   - **名称**：`DeepSeek`
   - **API Key**：填写从 [DeepSeek 官方平台](https://platform.deepseek.com/api_keys) 获取的密钥
   - **Base URL**：`https://api.deepseek.com`
   - **API 类型**：选择 **OpenAI 兼容**
4. 点击 **获取模型列表**。
5. 在返回的模型中找到 **DeepSeek V4 Pro**，点击添加并打开启用开关。
6. 点击页面底部的 **保存设置**。
7. 返回聊天页，在模型下拉列表中选择 `DeepSeek / DeepSeek V4 Pro`。

![](/model_setting.png)

::: tip 使用官方接口
请从 DeepSeek 官方平台创建 API Key，并使用官方 Base URL `https://api.deepseek.com`。不需要配置第三方中转服务。
:::

## 配置其他模型

其他 OpenAI 兼容服务商使用相同步骤，只需替换名称、API Key、Base URL 和模型。Claude 原生接口请选择 **Anthropic** API 类型；DeepSeek 官方、Qwen 及其他 OpenAI 兼容接口选择 **OpenAI 兼容**。

## 配置后没有模型

- 确认 API Key 和 Base URL 没有多余空格。
- 确认 Base URL 是 API 地址，而不是服务商网站首页。
- 点击 **获取模型列表** 后，还需要将模型添加到“已添加模型”并启用。
- 保存设置后返回聊天页刷新模型列表。
- 如果服务商不支持模型列表接口，请确认其兼容协议和接口文档。
