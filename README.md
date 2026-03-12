# WordAgent

中南大学计算机学院毕业设计——基于多智能体的AI辅助写作系统“文策AI”

> 文策AI：让写作有策略，让表达更智能

![](./docs/WenceAI.png)

## 项目概述

本项目是一个基于(多)智能体的AI辅助写作系统，用户在 **办公软件(如WPS、Microsoft Word)** 中安装 **加载项** 后，可以通过自然语言与AI智能体进行交互，获取写作建议、内容生成、结构优化等服务。生成文档Agent的核心就是生成 **“结构化Word文档”**。

系统采用FastAPI构建后端API，前端WPS加载项与后端利用流式接口通信，使前端流式显示LLM输出的内容，实现无缝的写作辅助体验。

前端采用Vue3和JavaScript开发，前端主要设计了一个DocxJson双向转化器模块，能够将带格式的Word文档内容与JSON格式进行相互转换。
这个json schema格式类似于web开发中的html和css格式，将word文章的段落和文本块的style属性都进行了抽象和结构化，方便智能体理解和生成。

后端采用Python语言，利用langchain和langraph框架实现智能体的设计和协作，用chatOpenAI接口实现SSE流式输出和工具调用，利用pySide6设计了一个简单的后端服务界面，方便安装加载项和查看终端日志。

对比市面上已有的AI辅助写作工具，文策AI的优势在于：

1. 以国民级办公软件为载体，让普通用户无门槛获得优质的AI写作辅助体验。
2. 对比常见的在Word中的AI写作工具，本项目智能体能够理解Word文章结构，能够自主联网搜集资料信息，生成符合Word文档结构的内容，能够根据用户需求进行文章结构修改和内容修改。
3. 采用多智能体协作架构，多智能体扮演不同专家角色，协同完成写作任务，以生成有深度的长文章为目标。
4. 本项目使用的大模型服务APIKey来自于用户自己，目前支持世界上大多数主流的LLM服务商，用户可以根据自己的需求选择不同的LLM服务商和不同的模型。

## 项目预览

|WPS加载项界面|后端服务QT界面|
|--|--|
|![](./docs/wps_addon.png)|![](./docs/pyQt.png)|

## 系统架构

为了能够更好地满足用户需求，保证系统生成文章的稳定性和深度，本项目设计了两种智能体架构：

### Single Agent loop架构

#### 整体架构图

![](./docs/single_agent_loop.png)

### Multi Agent 架构

## 快速开始

### 环境配置

- node v22.12.0
- wpsjs 2.2.3
- python 3.10.12

### 构建前端WPS加载项

```bash
cd frontend/wps_word_plugin
pnpm intsall
pnpm build
```

### 运行后端服务

```bash
cd backend
uv venv --python 3.10.12
uv sync
uv run python main.py
```

### 项目软件打包

```bash

```

如果你不想自己打包，可以直接下载release中的打包的可执行文件进行体验。

## 关于作者

与我交流：https://cmcblog.netlify.app/about/

## 开源协议

Apache License 2.0
