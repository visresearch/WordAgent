# WenCe AI 后端服务

智能写作助手后端 API 服务，基于 FastAPI + LangChain 构建。

## 快速开始

```bash
uv sync
uv run python main.py
```

```bash
black . --exclude '/(\.venv|build|dist)/'
```

## 文档



## 打包发布

### Linux

```bash
# 构建 DEB + AppImage
./build_linux.sh all

# 只构建 DEB
./build_linux.sh deb

# 只构建 AppImage
./build_linux.sh appimage
```

### Windows

```powershell
# 构建 EXE + Installer
.\build_windows.ps1 -Type all

# 只构建 EXE
.\build_windows.ps1 -Type exe

# 只构建 Installer
.\build_windows.ps1 -Type installer
```

详细说明请查看 [BUILD.md](BUILD.md)。

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

## 开发

```bash
# 运行测试
pytest

# 代码格式化
black .

# 类型检查
mypy app/
```

## License

MIT
