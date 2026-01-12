# SQLite 数据库查询指南

## 进入数据库

```bash
cd /home/cmc/develop/wence_ai/wence_backend/data
sqlite3 wence_ai.db
```

## 基础命令

| 命令 | 说明 |
|------|------|
| `.tables` | 查看所有表 |
| `.schema` | 查看所有表结构 |
| `.schema 表名` | 查看指定表结构 |
| `.headers on` | 显示列名 |
| `.mode column` | 列对齐显示 |
| `.mode table` | 表格显示（更美观） |
| `.quit` 或 `.exit` | 退出 |

## 常用查询

### 1. 设置显示格式（每次进入后执行）

```sql
.headers on
.mode table
```

### 2. 查看所有文档

```sql
SELECT * FROM documents;
```

### 3. 查看所有聊天记录

```sql
SELECT * FROM chat_messages;
```

### 4. 查看聊天记录（简化版，不显示长内容）

```sql
SELECT 
    id,
    document_id,
    role,
    substr(content, 1, 50) as content_preview,
    model,
    mode,
    created_at
FROM chat_messages;
```

### 5. 查看指定文档的聊天记录

```sql
-- 通过 doc_id 查询
SELECT m.id, m.role, substr(m.content, 1, 80) as content, m.created_at
FROM chat_messages m
JOIN documents d ON m.document_id = d.id
WHERE d.doc_id = 'doc_2qkwiu';
```

### 6. 统计每个文档的消息数量

```sql
SELECT 
    d.doc_id,
    d.doc_name,
    COUNT(m.id) as message_count
FROM documents d
LEFT JOIN chat_messages m ON d.id = m.document_id
GROUP BY d.id;
```

### 7. 查看最近 10 条消息

```sql
SELECT 
    m.id,
    d.doc_name,
    m.role,
    substr(m.content, 1, 60) as content,
    m.model,
    m.created_at
FROM chat_messages m
JOIN documents d ON m.document_id = d.id
ORDER BY m.created_at DESC
LIMIT 10;
```

### 8. 查看包含文档 JSON 的消息

```sql
SELECT id, role, substr(content, 1, 50), model
FROM chat_messages
WHERE document_json IS NOT NULL AND document_json != 'null';
```

### 9. 按模型统计使用次数

```sql
SELECT model, COUNT(*) as count
FROM chat_messages
GROUP BY model
ORDER BY count DESC;
```

## 数据管理

### 删除指定文档的所有聊天记录

```sql
DELETE FROM chat_messages 
WHERE document_id = (SELECT id FROM documents WHERE doc_id = 'your_doc_id');
```

### 删除所有数据（谨慎！）

```sql
DELETE FROM chat_messages;
DELETE FROM documents;
```

### 清空表并重置自增ID

```sql
DELETE FROM chat_messages;
DELETE FROM sqlite_sequence WHERE name='chat_messages';

DELETE FROM documents;
DELETE FROM sqlite_sequence WHERE name='documents';
```

## 表结构说明

### documents 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| doc_id | VARCHAR | 文档唯一标识（前端生成的 hash） |
| doc_name | VARCHAR | 文档名称 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### chat_messages 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| document_id | INTEGER | 关联的文档 ID |
| role | VARCHAR | 角色（user/assistant） |
| content | TEXT | 消息内容 |
| document_json | TEXT | 生成的文档 JSON（可选） |
| selection_context | TEXT | 选区上下文 JSON（可选） |
| model | VARCHAR | 使用的模型 |
| mode | VARCHAR | 模式（agent/ask） |
| created_at | DATETIME | 创建时间 |

## 导出数据

### 导出为 SQL

```bash
sqlite3 wence_ai.db .dump > backup.sql
```

### 导出为 CSV

```sql
.headers on
.mode csv
.output messages.csv
SELECT * FROM chat_messages;
.output stdout
```

## 恢复数据

```bash
sqlite3 wence_ai.db < backup.sql
```
