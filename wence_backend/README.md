# WenCe AI 后端服务

智能写作助手后端 API 服务，基于 FastAPI + LangChain + LangGraph + SQLite构建。

## 快速开始

```bash
uv sync
uv run python main.py
```

## 代码规范

```bash
# Install Ruff globally.
uv tool install ruff@latest

ruff check   # Lint all files in the current directory.
ruff format  # Format all files in the current directory.
```

## 文档



## 打包发布

```bash
cd wence_backend/deploy
uv run pyinstaller wence.spec
```

打包生成的可执行文件在`wence_backend/deploy/dist`目录下

| 运行环境 | 输出文件 | 文件名示例 |
|---------|---------|-----------|
| Linux | ELF 二进制文件 | `wence-ai` (无扩展名) |
| Windows | PE 可执行文件 | `wence-ai.exe` |
| macOS | Mach-O 可执行文件 | `wence-ai` (无扩展名) |

## 项目结构

```
wence_backend/
├── app/
│   ├── agent_langchain.py   # 纯 LangChain Agent（流式输出）
│   ├── agent.py              # LangGraph Agent（结构化）
│   ├── api/                  # API 路由
│   ├── core/                 # 核心配置
│   ├── models/               # 数据模型
│   └── services/             # 服务层
├── test/                     # 测试文件
├── pyproject.toml            # 项目配置（uv）
├── requirements.txt          # Python 依赖
├── wence.spec                # PyInstaller 配置
├── build_linux.sh            # Linux 打包脚本
├── build_windows.ps1         # Windows 打包脚本
└── BUILD.md                  # 打包详细文档
```

## 技术栈

- **Web 框架**: FastAPI
- **AI**: LangChain + OpenAI API
- **数据库**: SQLite + SQLAlchemy
- **打包**: PyInstaller + uv

