# 安装方式

文策 AI 现在提供三种安装方式：**安装包安装（推荐）**、**Zip 免安装解压运行**，以及面向开发者的 **本地源码部署**。

## 方式一：安装包安装（推荐）

适合大多数用户。安装后可以从系统菜单或桌面快捷方式启动，升级和卸载也更方便。

### 1. 下载发行版

前往 [GitHub Releases](https://github.com/visresearch/WordAgent/releases) 页面，下载与你系统匹配的最新安装包：

| 系统 | 推荐文件 |
|---|---|
| Windows 10/11 | `wence_ai-windows-x86_64-installer.exe` |
| Ubuntu 22.04 / Debian 系发行版 | `wence_ai-linux-x86_64.deb` |

### 2. 安装应用

**Windows：**

双击运行 `wence_ai-windows-x86_64-installer.exe`，按安装向导完成安装。

**Linux：**

在下载目录执行：

```bash
sudo dpkg -i ./wence_ai-linux-x86_64.deb
```

### 3. 启动文策 AI

安装完成后，启动 **WenCe AI / 文策 AI** 桌面程序。程序会启动本地后端服务，并提供安装 Word 加载项的图形界面。

### 4. 安装加载项

在桌面程序中进入加载项安装页面，点击对应的安装按钮，系统会自动将加载项安装到你的办公软件中。

### 5. 打开 Word 并配置 API Key

打开 WPS Word 或 Microsoft Word，信任加载项后即可看到文策 AI 面板。首次使用时，在面板中点击 **设置**，填入你的 LLM API Key 和 Base URL（参考 [配置 API Key](/guide/api-config)）。

## 方式二：Zip 免安装运行

适合不想安装到系统、临时试用，或没有安装权限的用户。

### 1. 下载 Zip 包

在 [GitHub Releases](https://github.com/visresearch/WordAgent/releases) 下载对应系统的完整压缩包：

| 系统 | 推荐文件 |
|---|---|
| Windows 10/11 | `wence_ai-windows-x86_64-full.zip` |
| Ubuntu 22.04 / Debian 系发行版 | `wence_ai-linux-x86_64-full.zip` |

### 2. 解压并运行

将 Zip 包解压到一个固定目录，然后运行目录中的 `wence_ai` 可执行文件。

Windows 用户如果看到安全提示，请确认文件来自官方 Release 页面后选择继续运行。

### 3. 安装加载项和配置模型

程序启动后，后续步骤与安装包方式相同：在桌面程序中安装加载项，然后到 Word 面板中配置 API Key。

## 方式三：本地源码部署

适合开发者或需要自定义功能的用户。

### 环境要求

| 依赖 | 版本 |
|---|---|
| Node.js | v22.12.0 |
| wpsjs | 2.2.3 |
| Python | 3.11.14 |
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
uv venv --python 3.11.14
# Linux
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

uv sync
uv run python main.py
```

### 3. 项目打包（可选）

如果你想自己构建发行包，可以使用项目内的打包脚本：

```bash
# 通用 PyInstaller 构建
cd backend
uv run pyinstaller ../packaging/pyinstaller/package.spec --clean --noconfirm
```

Linux `.deb` 安装包：

```bash
bash packaging/linux/build-deb.sh
```

Windows 安装包：

```powershell
.\packaging\windows\build-installer.ps1
```

## 下一步

安装完成后，请参考 [安装 WPS 加载项](/guide/wps-plugin) 或 [启动 Microsoft Word 加载项](/guide/msword-plugin) 开始使用。
