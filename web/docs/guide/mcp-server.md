# 外部 Agent 文档 MCP Server

文策 AI 提供文档 MCP Server，让 Codex 等支持 MCP 的外部 Agent 调用 WPS / Microsoft Word 的文档工具。外部 Agent 负责理解任务和选择工具，文策 AI 通过已打开的加载项侧栏执行文档读取与编辑。

| 用法 | 配置入口 | 调用方向 |
|---|---|---|
| [接入第三方 MCP](/guide/mcp) | 加载项 **设置 → MCP** | 文策 AI 内置智能体调用搜索、图表等外部工具 |
| 文档 MCP Server | 文策 AI 桌面程序 **MCP 服务器** | Codex 等外部 Agent 调用文策 AI 的文档工具 |

## 启动服务

1. 启动文策 AI 桌面程序，并保持后端运行。
2. 打开要处理的 WPS / Microsoft Word 文档，展开文策 AI 加载项侧栏。
3. 在桌面程序中进入 **MCP 服务器** 页面，点击 **运行**，确认服务状态为“运行中”。
4. 将页面显示的连接地址添加到外部客户端，传输类型选择 **Streamable HTTP**。

![文策 AI 文档 MCP Server 管理界面](/mcp-server.png)

默认连接地址为：

```text
http://127.0.0.1:3880/mcp/
```

如果后端地址或端口经过修改，以桌面程序显示的连接地址为准。外部客户端需要能够访问运行文策 AI 的本机服务。

点击 **停止** 会停用文档 MCP 接口；再次使用时点击 **运行**。调用期间需保持后端、办公软件和目标文档的加载项侧栏运行。

## 配置 Codex

在已安装 Codex CLI 的本机终端中添加服务：

```bash
codex mcp add wordagent --url http://127.0.0.1:3880/mcp/
codex mcp list
```

也可以在 `~/.codex/config.toml` 中添加以下配置。Windows 对应 `%USERPROFILE%\.codex\config.toml`：

```toml
[mcp_servers.wordagent]
url = "http://127.0.0.1:3880/mcp/"
```

Codex CLI 和 IDE 扩展共享 MCP 配置；保存后重新打开会话，IDE 扩展按其界面提示重启。Codex 终端会话可通过 `/mcp` 查看已启用的服务。配置方式参考 [OpenAI 官方 MCP 文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。

连接后，可以让 Codex 执行：

```text
通过 wordagent MCP 读取当前 Word 文档，将“实习目的”修改成 5 点，
保留原有标题和段落样式。先读取或搜索获取段落 ID，修改后重新读取确认结果。
```

## 配置其他客户端

支持 `mcpServers` JSON 配置的客户端可使用桌面程序展示的配置：

```json
{
  "mcpServers": {
    "wordagent": {
      "url": "http://127.0.0.1:3880/mcp/"
    }
  }
}
```

若客户端需要手动选择传输类型，请选 Streamable HTTP。不同客户端的字段格式可能不同，连接地址使用同一个 `/mcp/` 端点。

## 可调用的文档工具

| 工具 | 作用 |
|---|---|
| `read_document` | 按段落索引或段落 ID 读取文档，支持 `full` 和 `lightweight` 模式 |
| `search_document` | 按文本或样式查询文档，定位目标段落 |
| `edit_document` | 替换指定段落正文，保留其段落样式 |
| `delete_document` | 按起止 paraID 连续删除内容及完整表格 |
| `generate_document` | 插入带格式的结构化内容，`insertParaID: 0` 表示文档开头 |
| `insert_break` | 在指定段落后插入换行、分页或下一页分节符 |
| `create_document` | 创建并打开新的空白 DOCX 文档 |

### 指定 WPS 或 Microsoft Word

工具参数中的 `host: "wps"` 指向 WPS，`host: "word"` 指向 Microsoft Word。只有一种宿主连接时可以省略 `host`；两种宿主同时连接时必须明确指定。

例如，调用 `read_document` 读取 Microsoft Word 文档：

```json
{
  "host": "word",
  "docId": 0,
  "mode": "full"
}
```

Microsoft Word 的 `docId` 仅支持 `0`，代表加载项侧栏所属文档。请只保留目标文档的侧栏；多个 Word 侧栏连接时，服务会要求关闭多余侧栏。WPS 的 `docId: 0` 表示当前活动文档，非零值可指定已打开的文档。

### 编辑流程与样式

编辑前先使用 `read_document` 或 `search_document` 获取当前 `paraID`，修改后重新读取。`edit_document` 的 `runs` 如包含 `rStyle` 样式 ID，需通过 `styles` 参数传入完整读取返回的样式字典；省略 `rStyle` 时保留现有字符格式。

Microsoft Word 的 `create_document` 会打开新文档。后续调用前需关闭旧文档侧栏，再在新文档中打开加载项，才能让文档工具作用于新文档。

外部 Agent 的写入工具由加载项直接执行，不进入内置聊天页的待确认流程。外部客户端管理自己的模型、推理参数和工具调用策略；文策 AI [模型参数面板](/guide/api-config#编辑-llm-模型参数) 中的配置用于内置 Agent / Ask 对话。

## 查看运行状态

桌面程序显示服务状态与 **最近活跃客户端**。客户端发出 MCP 请求后，会在列表中显示约 2 分钟；该列表表示近期活动，不能精确判断客户端是否仍保持打开。

若工具提示“插件页面未连接”，请打开目标文档的加载项侧栏。若 MCP 请求返回 HTTP 503，请检查 **MCP 服务器** 页面是否已点击 **运行**，以及后端是否正常启动。

表格删除统一使用 `delete_document`，例如 `{"host":"wps","docId":0,"startParaID":145448706,"endParaID":130618599}`。两个 ID 必须取自当前读取结果，表示文档顺序中的首末段落，并非数值区间；省略 `endParaID` 仅删除一个段落。整表可直接使用表格对象的 `paraID` / `endParaID`。范围只覆盖部分表格时会拒绝，不会自动扩大删除范围。旧的 `paraIDs` 列表参数已移除。
