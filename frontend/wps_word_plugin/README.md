# WPS Word 插件

文策 AI 的 WPS 文字加载项，基于 Vue 3 + Vite + WPS JS API 构建。插件通过 `http://localhost:3880` 调用本地后端服务。

## 目录说明

```text
frontend/wps_word_plugin/
├── src/              # 插件页面与业务逻辑
├── public/           # 静态资源
├── manifest.xml      # WPS 加载项清单，构建时复制到 dist
├── vite.config.js    # Vite 配置
└── package.json
```

## 安装依赖

```bash
pnpm install
```

## 开发调试

启动 Vite 开发服务：

```bash
pnpm dev
```

`pnpm dev` 使用 `vite --port 3889`。如需用 WPS 官方调试工具，可使用项目依赖中的 `wpsjs`：

```bash
pnpm exec wpsjs debug
```

调试时请同时启动后端：

```bash
cd ../../backend
uv run python main.py
```

## 构建发布

```bash
pnpm build
```

构建产物输出到 `dist/`。后端开发环境会把该目录挂载到：

```text
http://127.0.0.1:3880/jsplugindir/
```

PyInstaller 打包时会把 `frontend/wps_word_plugin/dist` 收进应用目录中的 `frontend/`，供打包后的 GUI 安装页使用。

## 代码检查与格式化

```bash
pnpm lint
pnpm format
```

## 常见问题

- 如果 WPS 加载项仍显示旧代码、空页面或旧图标，关闭 WPS 和 `wpsjs debug` 后清理 CEF 缓存：

```bash
rm -rf ~/.local/share/Kingsoft/wps/addons/data/linux-x64/cef/1.25/jsapi/cache
rm -rf ~/.local/share/Kingsoft/wps/addons/data/linux-x64/cef/cache/wpsoffice
rm -rf ~/.local/share/Kingsoft/wps/addons/data/linux-x64/cef/globalcache
```

- 如果加载项没有显示，在 WPS 中打开 `工具 -> 加载项`，找到对应链接加载项并启用，然后重启 WPS。
- 如果插件提示网络错误，请确认后端服务运行在 `localhost:3880`。

## 开发文档

- [WPS 开放平台](https://open.wps.cn/)
- [WPSJS API 文档](https://qn.cache.wpscdn.cn/encs/doc/office_v19/index.htm)
- [WPSJS API 文档（新版）](https://open.wps.cn/previous/docs/client/wpsLoad)
