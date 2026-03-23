# 安装 WPS 加载项

## 前提条件

- 已完成 [安装方式](/guide/installation) 中的后端服务部署
- 已安装 WPS Office 桌面版（Windows 或 Linux）

## 安装步骤

### 1. 启动后端服务

双击运行 `wence_ai` 可执行文件（或通过源码启动），确保后端服务已正常运行。

### 2. 安装加载项

在后端服务 QT 界面中，点击 **wence_word_plugin → 安装** 按钮，系统会自动将加载项安装到 WPS 中。

| WPS 加载项界面 | 后端服务 QT 界面 |
|:--:|:--:|
| ![WPS加载项](/wps_addon.png) | ![QT界面](/pyQt.png) |

### 3. 打开 WPS Word

打开 WPS Word，首次加载时可能会弹出信任提示，选择 **信任** 即可。

安装成功后，你可以在 WPS Word 中看到文策 AI 的侧边面板。

## 下一步

请参考 [配置 API Key](/guide/api-config) 完成模型配置后即可开始使用。
