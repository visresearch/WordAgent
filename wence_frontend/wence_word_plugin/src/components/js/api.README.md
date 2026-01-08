# API 请求库使用文档

WenCe AI Writing Assistant 后端 API 请求封装库。

## 安装

将 `api.js` 放入项目中，然后导入：

```javascript
import api from './js/api.js'

// 或使用命名导出
import { modifyDocument, chat, chatStream } from './js/api.js'
```

## 配置

默认配置：

```javascript
{
  baseURL: 'http://localhost:3880',
  timeout: 30000,  // 30秒
  headers: {
    'Content-Type': 'application/json'
  }
}
```

修改配置：

```javascript
api.updateConfig({
  baseURL: 'http://your-server.com',
  timeout: 60000
})

// 获取当前配置
const config = api.getConfig()
```

## 核心 API

### 1. modifyDocument(documentJson, userQuestion, options?)

修改文档内容。发送解析后的文档 JSON 和用户问题到后端处理。

**参数：**
- `documentJson` (必需): 由 `parseDocxToJSON()` 解析得到的文档 JSON
- `userQuestion` (必需): 用户的问题或修改指令
- `options` (可选):
  - `extraData`: 额外数据，会合并到请求体中
  - `timeout`: 超时时间（默认 60000ms）

**返回值：**
```javascript
// 成功
{
  success: true,
  data: {
    modifiedJson: {...},  // 修改后的文档 JSON
    message: '...'        // 回复消息
  },
  status: 200
}

// 失败
{
  success: false,
  error: '错误信息',
  status: 400  // 或其他状态码
}
```

**示例：**

```javascript
import { parseDocxToJSON } from './docxJsonConverter.js'
import api from './api.js'

// 获取选中内容的 JSON
const selection = window.Application.Selection.Range
const documentJson = parseDocxToJSON(selection)

// 发送修改请求
const result = await api.modifyDocument(
  documentJson,
  '请把这段文字改成正式的商务语气',
  {
    extraData: {
      mode: 'agent',
      model: 'gpt-4'
    }
  }
)

if (result.success) {
  console.log('修改成功:', result.data.message)
  // 可以使用 result.data.modifiedJson 生成新文档
} else {
  console.error('修改失败:', result.error)
}
```

---

### 2. chat(message, history?, options?)

普通对话聊天。

**参数：**
- `message` (必需): 用户消息
- `history` (可选): 历史消息数组
- `options` (可选):
  - `model`: 模型名称，默认 'gpt-4'
  - `timeout`: 超时时间

**返回值：**
```javascript
// 成功
{
  success: true,
  data: {
    response: '...',  // AI 回复
    ...
  },
  status: 200
}
```

**示例：**

```javascript
const result = await api.chat('你好，请介绍一下你自己')

if (result.success) {
  console.log('AI:', result.data.response)
}
```

---

### 3. chatStream(message, options)

流式聊天，支持 Server-Sent Events (SSE)。

**参数：**
- `message` (必需): 用户消息
- `options`:
  - `onMessage(data)`: 收到消息的回调
  - `onError(error)`: 错误回调
  - `onComplete()`: 完成回调
  - `model`: 模型名称
  - `documentJson`: 文档 JSON（可选）
  - `history`: 历史消息

**返回值：**
```javascript
{
  abort: Function  // 调用此方法可中断请求
}
```

**示例：**

```javascript
let fullResponse = ''

const controller = api.chatStream('写一篇关于AI的文章', {
  model: 'gpt-4',
  
  onMessage(data) {
    fullResponse += data.content || ''
    console.log('收到:', data.content)
  },
  
  onError(error) {
    console.error('错误:', error)
  },
  
  onComplete() {
    console.log('完成:', fullResponse)
  }
})

// 如果需要取消
// controller.abort()
```

---

### 4. healthCheck()

检查后端服务是否可用。

**示例：**

```javascript
const result = await api.healthCheck()

if (result.success) {
  console.log('服务正常')
} else {
  console.error('服务不可用:', result.error)
}
```

---

### 5. getModels()

获取可用的 AI 模型列表。

**示例：**

```javascript
const result = await api.getModels()

if (result.success) {
  console.log('可用模型:', result.data.models)
}
```

---

## 后端 API 接口规范

### POST /api/doc/modify

修改文档内容。

**请求体：**
```json
{
  "documentJson": {
    "text": "...",
    "paragraphs": [...],
    "tables": [...],
    "images": [...]
  },
  "question": "用户的修改指令",
  "timestamp": 1704700000000,
  "mode": "agent",
  "model": "gpt-4"
}
```

**响应：**
```json
{
  "success": true,
  "message": "AI的回复说明",
  "modifiedJson": {
    "text": "...",
    "paragraphs": [...],
    ...
  }
}
```

---

### POST /api/chat

普通聊天。

**请求体：**
```json
{
  "message": "用户消息",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "model": "gpt-4",
  "timestamp": 1704700000000
}
```

**响应：**
```json
{
  "response": "AI回复内容"
}
```

---

### POST /api/chat/stream

流式聊天 (SSE)。

**请求体：**
```json
{
  "message": "用户消息",
  "model": "gpt-4",
  "documentJson": null,
  "history": [],
  "stream": true,
  "timestamp": 1704700000000
}
```

**响应：** Server-Sent Events 格式
```
data: {"content": "你"}
data: {"content": "好"}
data: {"content": "！"}
data: [DONE]
```

---

### GET /api/health

健康检查。

**响应：**
```json
{
  "status": "ok",
  "timestamp": 1704700000000
}
```

---

### GET /api/models

获取模型列表。

**响应：**
```json
{
  "models": [
    { "id": "gpt-4", "name": "GPT-4" },
    { "id": "gpt-3.5", "name": "GPT-3.5 Turbo" }
  ]
}
```

---

## 错误处理

所有 API 方法都返回统一格式：

```javascript
// 成功
{
  success: true,
  data: {...},
  status: 200
}

// 失败
{
  success: false,
  error: '错误描述',
  status: 400,  // HTTP状态码（网络错误时无此字段）
  code: 'TIMEOUT'  // 错误代码（可选）
}
```

错误代码：
- `TIMEOUT`: 请求超时
- `NETWORK_ERROR`: 网络错误

---

## 扩展

使用底层 `request` 方法添加新 API：

```javascript
import { request } from './api.js'

async function customAPI(data) {
  return await request('/api/custom', {
    method: 'POST',
    body: data
  })
}
```
