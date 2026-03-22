# 快速开始

文策 AI 提供两种使用方式：**直接下载** 已打包的发行版，或 **本地部署** 源码。

## 方式一：直接下载（推荐）

适合普通用户，开箱即用。

### 1. 下载发行版

前往 [GitHub Releases](https://github.com/visresearch/WordAgent/releases) 页面，下载最新版本的压缩包。

### 2. 解压运行

解压下载的压缩包，双击 `wence_ai` 可执行文件启动后端服务。

### 3. 安装加载项

在后端服务 QT 界面中，点击 **wence_word_plugin → 安装**，系统会自动将加载项安装到你的办公软件中。

### 4. 打开 Word

打开 WPS Word 或 Microsoft Word，信任加载项，即可在 Word 中看到文策 AI 的面板。

### 5. 配置 API Key

在加载项面板中点击 **设置** 按钮，填入你的 LLM API Key 和 Base URL（参考 [使用说明 - 配置 API Key](/guide/usage#配置-api-key)）。

## 方式二：本地部署

适合开发者或需要自定义功能的用户。

### 环境要求

| 依赖 | 版本 |
|---|---|
| Node.js | v22.12.0 |
| wpsjs | 2.2.3 |
| Python | 3.10.12 |
| 系统 | Windows 10/11 或 Ubuntu 22.04 |

### 1. 构建前端加载项

**WPS Word 加载项：**

```bash
cd frontend/wps_word_plugin
pnpm install
pnpm build
```

**Microsoft Word 加载项：**

```bash
cd frontend/microsoft_word_plugin
pnpm install
pnpm build
```

### 2. 运行后端服务

```bash
cd backend
uv venv --python 3.10.12
# Linux
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

uv sync
uv run python main.py
```

### 3. 项目打包（可选）

如果你想将项目打包为可执行文件：

```bash
cd backend/deploy
uv run pyinstaller wence.spec
```

打包生成的可执行文件在 `backend/deploy/dist` 目录下。

## 下一步

配置完成后，请参考 [使用说明](/guide/usage) 了解如何配置 API Key 和使用各项功能。
