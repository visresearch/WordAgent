# WenCe AI 后端服务

智能写作助手后端 API 服务，基于 FastAPI + LangChain + LangGraph 构建。

## 项目结构

```
backend/
├── app/
│   ├── api/           # API 路由
│   ├── core/          # 核心配置
│   ├── services/      # 业务服务
│   │   └── agent/    # Agent 核心逻辑
│   └── models/            # 数据库
├── evaluation/        # 评估模块
├── deploy/            # 打包部署
└── main.py           # 入口文件
```

## 快速开始

```bash
cd backend
uv sync
uv run python main.py
```

## 代码规范

```bash
uv tool install ruff@latest

ruff check   # Lint
ruff format  # Format
```

## 评估模块

详见 [evaluation/README.md](evaluation/README.md)

## 打包发布

```bash
cd backend/deploy
uv run pyinstaller package.spec
```

`package.spec` 会从 `APP_VERSION` 环境变量读取版本号；发布构建中由 Git tag 注入该环境变量，并写入打包运行时 `.env`，供 GUI 和 API 展示当前版本号。

输出在 `backend/deploy/dist` 目录。

| 运行环境 | 输出文件 |
|---------|---------|
| Linux | `wence-ai` |
| Windows | `wence-ai.exe` |
| macOS | `wence-ai` |

## LangSmith 监控

可选功能，在 `.env` 中配置：

```bash
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT="WordAgent"
```

## 注意事项

- 需要 WPS Cloud 服务运行（端口 58890），否则无法显示加载项列表
- 如遇加载项异常，杀掉 `wpscloudsvr` 进程后重启后端服务

```bash
ps -aux | grep wpscloud
```
