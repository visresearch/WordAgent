# Microsoft Word 插件

文策 AI 的 Microsoft Word Office Add-in，基于 Vue 3 + Webpack + Office.js 构建。插件通过 `http://localhost:3880` 调用本地后端服务，开发和安装清单默认使用 HTTPS `localhost:3000`。

## 目录说明

```text
frontend/microsoft_word_plugin/
├── src/                # taskpane、commands 和 Vue 组件
├── assets/             # Office 加载项图标与静态资源
├── manifest.xml        # Office Add-in 清单
├── webpack.config.js   # Webpack 与 dev server 配置
└── package.json
```

## 安装依赖

```bash
pnpm install
```

项目通过 `pnpm-workspace.yaml` 的 `allowBuilds`（pnpm 10.26+）记录依赖安装脚本策略：允许 `keytar` 安装原生模块，跳过无需执行的脚本。请保留此文件，避免 pnpm 11 因未配置的脚本报 `ERR_PNPM_IGNORED_BUILDS`。升级依赖后若出现新的脚本提示，应检查对应脚本再更新配置。

## 开发调试

启动并旁加载插件：

```bash
pnpm start
```

停止调试：

```bash
pnpm stop
```

如只需要启动开发服务器：

```bash
pnpm dev-server
```

开发服务器默认地址为 `https://localhost:3000/`，端口来自 `package.json` 的 `config.dev_server_port`。首次调试时 Office 工具会处理本地开发证书。

调试时请同时启动后端：

```bash
cd ../../backend
uv run python main.py
```

## 构建发布

```bash
pnpm build
```

构建产物输出到 `dist/`，其中包含 `taskpane.html`、`commands.html`、`manifest.xml` 和 assets。PyInstaller 打包时会把 `frontend/microsoft_word_plugin/dist` 收进应用目录中的 `msoffice/`。

打包后的桌面 GUI 会在本地 HTTPS `localhost:3000` 提供该 `dist` 目录，并提供 manifest 下载/安装入口。

## 清单校验与代码检查

```bash
pnpm validate
pnpm lint
pnpm lint:fix
pnpm prettier
```

## 供外部 Agent 调用的文档 MCP

在后端 GUI 的「MCP 服务器」页面点击「运行」，并在目标 Word 文档中打开文策加载项侧栏。侧栏在 Office 就绪后自动连接后端，断线后自动重连。

Microsoft Word 与 WPS 共用同一个 Streamable HTTP 地址：

```json
{
  "mcpServers": {
    "wordagent": {
      "url": "http://127.0.0.1:3880/mcp/"
    }
  }
}
```

工具为 `read_document`、`search_document`、`edit_document`、`delete_document`、`generate_document`、`insert_break`、`create_document`。工具参数使用 `host: "word"` 指定 Microsoft Word，`host: "wps"` 指定 WPS；只有一种宿主连接时可以省略。两种宿主同时连接时必须指定，指定的宿主未连接时会返回错误。

Word 的 `docId` 仅支持 `0`，代表加载项侧栏所属文档。请仅保留目标 Word 文档的侧栏；多个 Word 侧栏连接时后端会拒绝调用并提示关闭多余侧栏。先读取或搜索获得 `paraID` 再编辑，文档变更后重新读取。例如：

```json
{"host": "word", "docId": 0, "mode": "full"}
```

以上为 `read_document` 的参数。`edit_document` 中如使用 `rStyle` 引用，需通过其 `styles` 参数传入完整读取返回的样式字典；省略 `rStyle` 则保留现有字符格式。`generate_document` 的 `document.styles` 规则与内置 Agent 一致，`insertParaID: 0` 表示文档开头。

`create_document` 会打开新文档。后续调用前请关闭旧文档侧栏，再在新文档打开加载项；原侧栏仍绑定原文档。

内部桥接地址是 `ws://127.0.0.1:3880/api/mcp/bridge?host=word`，与 WPS 共用路径和端口。外部 Agent 应连接 `/mcp/`。

## 常见问题

- 如果 Word 插件页面打不开，请确认本地 HTTPS `localhost:3000` 服务已经启动，或在桌面 GUI 中启动 Microsoft Word 插件安装服务。
- 如果插件提示网络错误，请确认后端服务运行在 `localhost:3880`。
- 如果 manifest 修改后没有生效，先执行 `pnpm stop`，关闭 Word，再重新 `pnpm start`。
