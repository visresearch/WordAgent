# 安装方式

文策 AI 支持 Windows、Linux 和 macOS。普通用户推荐下载系统安装包，也可以使用免安装压缩包；开发者可从源码运行。

## 方式一：安装包安装（推荐）

### 1. 下载发行版

前往 [GitHub Releases](https://github.com/visresearch/WordAgent/releases)，下载与你的系统和架构匹配的文件：

| 系统 | 推荐文件 | 说明 |
|---|---|---|
| Windows 10/11 x86_64 | `wence_ai-windows-x86_64-installer.exe` | Windows 安装向导 |
| Ubuntu 22.04 / Debian x86_64 | `wence_ai-linux-x86_64.deb` | Debian 安装包 |
| macOS 10.15+ Apple Silicon | `wence_ai-macos-arm64.dmg` | macOS 磁盘映像 |

当前 macOS 发行包为 ARM64，仅适用于 Apple Silicon（M 系列芯片）。Intel Mac 请使用源码方式，或等待对应架构的发行包。

### 2. 安装应用

**Windows**

双击 `wence_ai-windows-x86_64-installer.exe`，按安装向导完成安装。

**Linux**

在下载目录执行：

```bash
sudo dpkg -i ./wence_ai-linux-x86_64.deb
```

如果系统提示缺少依赖，再执行：

```bash
sudo apt-get install -f
```

**macOS**

1. 双击打开 `wence_ai-macos-arm64.dmg`。
2. 将 **WenCe AI.app** 拖入 **Applications** 文件夹。
3. 从“应用程序”打开 WenCe AI。

当前应用未经过 Apple App Store 分发。如果 macOS 阻止首次启动，请在 Finder 中右键应用并选择 **打开**；仍被阻止时，前往 **系统设置 → 隐私与安全性**，确认允许打开来自 GitHub Release 的应用。

### 3. 启动并安装加载项

启动 **WenCe AI / 文策 AI** 桌面程序。程序会启动本地后端，并提供 WPS Word 与 Microsoft Word 加载项入口。

- WPS 用户参考 [安装 WPS Word 加载项](/guide/wps-plugin)。
- Microsoft Word 用户参考 [启动 Microsoft Word 加载项](/guide/msword-plugin)。

加载项可见后，按照 [配置大模型服务](/guide/api-config) 添加 DeepSeek V4 Pro。

## 方式二：免安装压缩包

在 [GitHub Releases](https://github.com/visresearch/WordAgent/releases) 下载对应的完整包：

| 系统 | 文件 |
|---|---|
| Windows 10/11 x86_64 | `wence_ai-windows-x86_64-full.zip` |
| Ubuntu 22.04 x86_64 | `wence_ai-linux-x86_64-full.zip` |
| macOS 10.15+ Apple Silicon | `wence_ai-macos-arm64-app.zip` |

Windows 和 Linux 用户解压后运行目录中的 `wence_ai`。macOS 用户解压得到 **WenCe AI.app**，将其移动到“应用程序”后打开。首次启动受到系统拦截时，按上面的 macOS 安全提示处理。

::: warning 不要直接在压缩包内运行
请先完整解压，并将程序放到固定目录。否则内置加载项、Skill 和其他资源可能无法正确读取。
:::

## 方式三：本地源码部署

### 环境要求

| 依赖 | 版本或平台 |
|---|---|
| Node.js | 22.12.0 |
| pnpm | 9 或兼容版本 |
| wpsjs | 2.2.3（仅构建 WPS 加载项需要） |
| Python | 3.11.14 |
| 系统 | Windows 10/11、Ubuntu 22.04 或 macOS 10.15+ |

### 1. 构建前端加载项

WPS Word 加载项：

```bash
cd frontend/wps_word_plugin
pnpm install
pnpm build
```

Microsoft Word 加载项：

```bash
cd frontend/microsoft_word_plugin
pnpm install
pnpm build
```

### 2. 运行后端

```bash
cd backend
uv venv --python 3.11.14
uv sync
uv run python main.py
```

`uv run` 会直接使用项目虚拟环境，通常不需要手动激活 `.venv`。

### 3. 构建发行包（可选）

先生成通用 PyInstaller 应用目录：

```bash
cd backend
uv run pyinstaller ../packaging/pyinstaller/package.spec --clean --noconfirm
```

再在对应系统执行包装脚本：

```bash
# Linux .deb
bash packaging/linux/build-deb.sh

# macOS .app.zip 和 .dmg
bash packaging/darwin/build-packages.sh
```

Windows 安装包需在 PowerShell 中构建：

```powershell
.\packaging\windows\build-installer.ps1
```

## 下一步

完成安装后，继续阅读 [快速开始](/guide/quick-start) 或直接进入 [配置大模型服务](/guide/api-config)。
