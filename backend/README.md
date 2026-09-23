# WenCe AI 后端服务

WenCe AI 的本地后端和桌面 GUI 入口，负责启动 FastAPI 服务、加载 WPS / Microsoft Word 插件构建产物，并承接聊天、文档处理、设置、历史记录等能力。

## 项目结构

```text
backend/
├── app/                 # FastAPI 应用、API 路由、服务、数据模型
├── gui/                 # PySide6 桌面 GUI 与插件安装界面
├── evaluation/          # 评估模块
├── tests/               # pytest 测试及测试专用配置
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

## 可选 Python 插件

WPS 设置页的“插件”面板可下载 OCR 插件、安装已发布的 `wordagent-plugin-*` 包或上传 `.whl`，也可查看安装日志并删除插件。每个插件使用用户数据目录下独立的 uv 环境；默认后端依赖和安装包不含 RapidOCR、OpenCV、ONNX Runtime 或 OCR 模型。OCR 插件源码位于 `app/services/plugins/wordagent-plugin-ocr/`，构建主应用时会被排除；发布版按应用版本从 GitHub 下载这份源码并用 uv 安装。

自定义插件需提供 `wordagent.plugins` 入口点。入口对象声明 `name`、`description`、`capabilities`，实现 `run(capability, payload) -> dict`，可选实现 `check()`；插件逻辑在独立 Python 进程中执行。具体示例见 OCR 插件的 README。

## 运行测试

在 `backend/` 目录执行：

```bash
uv sync --extra dev
uv run pytest

# 只运行上下文压缩中间件测试
uv run pytest tests/test_summarization_middleware.py -v
```

`uv run python main.py` 启动应用，不收集或执行 `tests/` 中的测试；`uv run pytest` 才运行测试。文件名中的下划线无需转义。

`tests/conftest.py` 仅在 pytest 中加载：关闭测试进程的 LangSmith 追踪，防止假模型记录混入正式项目，并将测试进程的 `DEBUG` 设置为 `false`。这些配置不影响正常启动。应用中的上下文压缩属于正式功能，达到阈值才触发；追踪中出现压缩中间件节点本身不代表已经生成摘要。

如果终端加载过 ROS Humble 环境，pytest 可能自动发现 ROS 的 `launch_testing` / `launch_ros` 插件，继而报 `ModuleNotFoundError: No module named 'lark'`。本项目已在 `pyproject.toml` 中禁用这两个无关插件，无需安装 ROS 测试依赖，也无需在每次测试前设置环境变量。

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

## 用户澄清（ask_user）

Agent 和 Ask 模式均提供 `ask_user(question, options)`。要求存在影响结果的歧义时，模型通过
LangChain `HumanInTheLoopMiddleware` 暂停；WPS 输入框上方显示选项和自填答案。回答使用
`respond` 决策写入 `ToolMessage`，随后继续同一会话，不会把回答作为新的任务重新执行。

待回答问题保存在 SQLite Checkpointer 中，会话详情的 `pendingQuestion` 字段用于刷新或重启后恢复。
WebSocket `chat` 请求中的 `userResponse.answers` 携带问题 `id` 和 `answer`；服务端检查会话和问题
是否匹配，拒绝空回答、过期回答和重复提交。恢复时沿用暂停前的模型及文档上下文。
此功能要求 `langchain>=1.4.0`。

## LangSmith 监控

可选功能，在 `.env` 中配置：

```bash
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT="WordAgent"
```

## 注意事项

- 后端默认只监听 `127.0.0.1:3880`，供本机 Word / WPS 插件访问。
- GUI 检查更新时先请求 GitHub Release API，失败后通过 `https://gh-proxy.com/` 转发同一 API；每个地址的请求超时为 8 秒。备用服务不可用时仍会显示“更新检查失败”，不影响后端运行。此回退仅用于版本信息，官网和安装包下载链接保持原样。
- WPS 插件安装依赖 WPS Cloud 本地服务，通常监听 `58890` 端口；GUI 会尝试启动 `wpscloudsvr`。
- 如果 WPS 加载项显示旧代码、空白页或旧图标，先关闭 WPS 和调试进程，再清理 WPS CEF 缓存。
