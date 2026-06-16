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

## 常见问题

- 如果 Word 插件页面打不开，请确认本地 HTTPS `localhost:3000` 服务已经启动，或在桌面 GUI 中启动 Microsoft Word 插件安装服务。
- 如果插件提示网络错误，请确认后端服务运行在 `localhost:3880`。
- 如果 manifest 修改后没有生效，先执行 `pnpm stop`，关闭 Word，再重新 `pnpm start`。
