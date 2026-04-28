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

## 打包发布

```bash
cd backend/deploy
uv run pyinstaller wence.spec
```

打包生成的可执行文件在`backend/deploy/dist`目录下

| 运行环境 | 输出文件 | 文件名示例 |
|---------|---------|-----------|
| Linux | ELF 二进制文件 | `wence-ai` (无扩展名) |
| Windows | PE 可执行文件 | `wence-ai.exe` |
| macOS | Mach-O 可执行文件 | `wence-ai` (无扩展名) |

## LangSmith

另外，本项目支持使用Langsmith监控Agent运行流程

修改.env.example文件为.env，将自己的Langsmith API Key填入

```bash
# LangSmith 监控配置（可选，不配置不影响项目运行）
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT="WordAgent"
```

打开Langsmith官网面板：https://smith.langchain.com/

> .env.example中的参数均为调试好的默认参数

## LangGraph Dev

本项目还集成了langsmith studio的LangGraph Dev功能，可以可视化调试Agent的执行流程，查看每一步的输入输出和调用的工具。

在.env文件中设置`LANGGRAPH_DEV_MODE=single`，然后运行后端服务，运行

```bash
uv run langgraph dev
```

打开Langsmith官网studio面板，可以可视化看到Agent的执行流程图。

## 提交代码

删掉tag重新提交

```bash
# 删除本地和远程的 tag
git tag -d v0.3.0
git push github --delete v0.3.0

# 修改完代码后重新打 tag 并推送
git add . && git commit -m "chore：修改CLCI"
git tag v0.3.0
git push github && git push github --tags
```

## 注意事项

在58890端口会运行一个wpscloudsrv的服务，要启动，不然看不到wps加载项列表

如果发现WPS加载项不对劲，明明正在启动，但是仍然在WPS中无法显示，可以杀掉这个wpscloudsvr服务进程，重启wenceAI后端服务，wpscloudsvr会自动重启的。

```bash
ps -aux | grep wpscloud
```

```bash
cmc        45969  0.1  0.5 2317780 171624 pts/1  Sl+  13:33   0:00 /opt/kingsoft/wps-office/office6/wpscloudsvr /jsapihttpserver ksowpscloudsvr://start=RelayHttpServer
```