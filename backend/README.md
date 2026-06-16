# WenCe AI 后端服务

WenCe AI 的本地后端和桌面 GUI 入口，负责启动 FastAPI 服务、加载 WPS / Microsoft Word 插件构建产物，并承接聊天、文档处理、设置、历史记录等能力。

## 项目结构

```text
backend/
├── app/                 # FastAPI 应用、API 路由、服务、数据模型
├── gui/                 # PySide6 桌面 GUI 与插件安装界面
├── evaluation/          # 评估模块
├── wence_data/          # 本地运行数据目录，已被 git 忽略
├── main.py              # 桌面版入口：同时启动 API 和 GUI
├── pyproject.toml       # Python 依赖与工具配置
└── uv.lock              # uv 锁定文件
```

打包相关文件已经迁移到仓库根目录的 `packaging/`：

```text
packaging/
├── pyinstaller/package.spec
├── linux/build-deb.sh
└── windows/
    ├── build-installer.ps1
    └── wence_ai.iss
```

## 快速开始

```bash
cd backend
uv sync
uv run python main.py
```

默认服务地址是 `http://127.0.0.1:3880`。`main.py` 会启动 API 服务和桌面 GUI；GUI 中可安装 WPS 插件和 Microsoft Word 插件。

## 前端构建依赖

打包前需要先构建两个前端插件，否则 PyInstaller 会找不到需要收进去的 `dist` 目录：

```bash
cd frontend/wps_word_plugin
pnpm install
pnpm build

cd ../microsoft_word_plugin
pnpm install
pnpm build
```

构建后：

- WPS 插件输出到 `frontend/wps_word_plugin/dist`，后端开发环境挂载为 `/jsplugindir/`。
- Microsoft Word 插件输出到 `frontend/microsoft_word_plugin/dist`，GUI 安装界面会在本地 HTTPS `localhost:3000` 上提供静态文件。

## 打包发布

先构建通用 PyInstaller 应用目录：

```bash
cd backend
uv run pyinstaller ../packaging/pyinstaller/package.spec --clean --noconfirm
```

`package.spec` 会从 `APP_VERSION` 环境变量读取版本号；GitHub Actions 的 tag 构建会自动注入版本号，并写入打包运行时 `.env`，供 GUI 和 API 展示。

通用应用目录输出在 `backend/dist/wence_ai`。平台发行包由 `packaging/` 下的脚本生成：

| 运行环境 | 打包方式 | 输出文件 |
|---------|---------|---------|
| Linux | fpm | `backend/package/wence_ai-linux-x86_64.deb` |
| Linux | full zip | `backend/package/wence_ai-linux-x86_64-full.zip` |
| Windows | Inno Setup | `backend/package/wence_ai-windows-x86_64-installer.exe` |
| Windows | full zip | `backend/package/wence_ai-windows-x86_64-full.zip` |

GitHub Actions 会自动完成前端构建、PyInstaller 构建、平台安装包构建和 release 上传。

## 代码规范

```bash
uv tool install ruff@latest

ruff check
ruff format
```

## 评估模块

详见 [evaluation/README.md](evaluation/README.md)。

## LangSmith 监控

可选功能，在 `.env` 中配置：

```bash
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT="WordAgent"
```

## 注意事项

- 后端默认只监听 `127.0.0.1:3880`，供本机 Word / WPS 插件访问。
- WPS 插件安装依赖 WPS Cloud 本地服务，通常监听 `58890` 端口；GUI 会尝试启动 `wpscloudsvr`。
- 如果 WPS 加载项显示旧代码、空白页或旧图标，先关闭 WPS 和调试进程，再清理 WPS CEF 缓存。
