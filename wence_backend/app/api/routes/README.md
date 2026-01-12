# WenCe AI 后端 API 文档

> Base URL: `http://localhost:8000/api`

---

## 1. 健康检查

### 1.1 健康检查

- **接口**: `GET /health`
- **描述**: 检查服务是否正常运行

**响应示例**:
```json
{
  "status": "ok",
  "service": "wence-api"
}
```

---

## 2. 聊天接口

### 2.1 流式聊天

- **接口**: `POST /stream`
- **描述**: 流式聊天接口，使用 SSE 返回流式响应
- **Content-Type**: `application/json`
- **Response-Type**: `text/event-stream`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| message | string | 是 | 用户消息 |
| mode | string | 是 | 模式：`agent` 或 `ask` |
| model | string | 否 | 模型 ID，默认 `gpt-4` |
| history | array | 否 | 历史消息列表，默认 `[]` |
| documentJson | object | 否 | 文档 JSON 数据 |
| timestamp | integer | 否 | 时间戳 |

**请求示例**:
```json
{
  "message": "帮我优化这段文字",
  "mode": "agent",
  "model": "gpt-4o",
  "history": [],
  "documentJson": {
    "text": "示例文本",
    "paragraphs": []
  }
}
```

**响应格式** (SSE):
```
data: {"type": "text", "content": "好的，"}

data: {"type": "text", "content": "我来帮您处理。"}

data: {"type": "json", "content": {...}}

data: [DONE]
```

---

## 3. 模型接口

### 3.1 获取可用模型列表

- **接口**: `GET /models`
- **描述**: 获取可用模型列表（聚合多平台 + 白名单过滤）

**响应参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否成功 |
| models | array | 模型列表 |
| models[].id | string | 模型 ID |
| models[].name | string | 模型显示名称 |
| models[].provider | string | 提供商 |
| models[].description | string | 描述 |

**响应示例**:
```json
{
  "success": true,
  "models": [
    {
      "id": "auto",
      "name": "Auto",
      "provider": "WenCe AI",
      "description": "自动选择最佳模型"
    },
    {
      "id": "gpt-4o",
      "name": "GPT-4o",
      "provider": "OpenAI",
      "description": ""
    },
    {
      "id": "glm-4.5",
      "name": "GLM-4.5",
      "provider": "智谱AI",
      "description": ""
    }
  ]
}
```

### 3.2 刷新模型缓存

- **接口**: `POST /models/refresh`
- **描述**: 强制刷新模型缓存

**响应示例**:
```json
{
  "success": true,
  "message": "已刷新，共 10 个可用模型"
}
```

---

## 4. 历史记录接口

### 4.1 获取指定文档的聊天历史

- **接口**: `GET /history/{doc_id}`
- **描述**: 获取指定文档的聊天历史记录

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| doc_id | string | 是 | 文档唯一标识符 |

**查询参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| limit | integer | 否 | 返回消息数量限制（默认 50，最大 200） |
| offset | integer | 否 | 偏移量（默认 0） |

**响应参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否成功 |
| messages | array | 消息列表 |
| error | string | 错误信息（失败时返回） |

**响应示例**:
```json
{
  "success": true,
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "帮我优化这段文字",
      "documentJson": null,
      "selectionContext": null,
      "model": "gpt-4o",
      "mode": "agent",
      "createdAt": "2026-01-12T10:30:00"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "好的，我来帮您优化...",
      "documentJson": {...},
      "selectionContext": null,
      "model": "gpt-4o",
      "mode": "agent",
      "createdAt": "2026-01-12T10:30:05"
    }
  ],
  "error": null
}
```

### 4.2 保存聊天消息

- **接口**: `POST /history/save`
- **描述**: 保存聊天消息到历史记录

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| docId | string | 是 | 文档唯一标识符 |
| docName | string | 否 | 文档名称 |
| role | string | 是 | 消息角色：`user` 或 `assistant` |
| content | string | 是 | 消息内容 |
| documentJson | object | 否 | AI 生成的文档 JSON |
| selectionContext | object | 否 | 选区上下文 |
| model | string | 否 | 使用的模型 |
| mode | string | 否 | 使用的模式 |

**请求示例**:
```json
{
  "docId": "doc-123456",
  "docName": "实习报告.docx",
  "role": "user",
  "content": "帮我优化这段文字",
  "documentJson": null,
  "selectionContext": {
    "text": "选中的文本",
    "start": 0,
    "end": 100
  },
  "model": "gpt-4o",
  "mode": "agent"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "消息已保存",
  "error": null
}
```

### 4.3 清空指定文档的聊天历史

- **接口**: `DELETE /history/{doc_id}`
- **描述**: 清空指定文档的所有聊天历史记录

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| doc_id | string | 是 | 文档唯一标识符 |

**响应示例（成功）**:
```json
{
  "success": true,
  "message": "历史记录已清空",
  "error": null
}
```

**响应示例（文档不存在）**:
```json
{
  "success": false,
  "message": null,
  "error": "文档不存在"
}
```

### 4.4 清空所有文档的聊天历史

- **接口**: `DELETE /history`
- **描述**: 清空所有文档的所有聊天历史记录

**响应示例**:
```json
{
  "success": true,
  "message": "已清空所有历史记录，共删除 128 条消息",
  "error": null
}
```

### 4.5 获取所有文档列表

- **接口**: `GET /documents`
- **描述**: 获取所有有聊天记录的文档列表

**查询参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| limit | integer | 否 | 返回数量限制（默认 100，最大 500） |

**响应参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否成功 |
| documents | array | 文档列表 |
| documents[].docId | string | 文档唯一标识符 |
| documents[].docName | string | 文档名称 |
| documents[].createdAt | string | 创建时间 (ISO 8601) |
| documents[].updatedAt | string | 更新时间 (ISO 8601) |
| error | string | 错误信息（失败时返回） |

**响应示例**:
```json
{
  "success": true,
  "documents": [
    {
      "docId": "doc-123456",
      "docName": "实习报告.docx",
      "createdAt": "2026-01-10T08:00:00",
      "updatedAt": "2026-01-12T10:30:00"
    },
    {
      "docId": "doc-789012",
      "docName": "毕业论文.docx",
      "createdAt": "2026-01-08T14:00:00",
      "updatedAt": "2026-01-11T16:45:00"
    }
  ],
  "error": null
}
```

---

## 5. 通用响应模型

### CommonResponse

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否成功 |
| message | string | 成功消息（可选） |
| error | string | 错误信息（可选） |

---

## 6. 错误处理

所有接口在发生错误时返回统一格式：

```json
{
  "success": false,
  "message": null,
  "error": "错误描述信息"
}
```

---

## 7. 接口总览

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/stream` | 流式聊天 |
| GET | `/models` | 获取可用模型列表 |
| POST | `/models/refresh` | 刷新模型缓存 |
| GET | `/history/{doc_id}` | 获取指定文档的聊天历史 |
| POST | `/history/save` | 保存聊天消息 |
| DELETE | `/history/{doc_id}` | 清空指定文档的聊天历史 |
| DELETE | `/history` | 清空所有文档的聊天历史 |
| GET | `/documents` | 获取所有文档列表 |
