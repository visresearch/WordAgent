# 启动 Microsoft Word 加载项

## 前提条件

- 已完成 [安装方式](/guide/installation) 中的后端服务部署
- 拥有 Microsoft 365 账户并可使用 Word 网页版

## 使用方式

Microsoft Word 加载项以**在线模式**运行，通过 HTTPS 连接后端服务。

### 1. 启动后端服务

双击运行 `wence_ai` 可执行文件（或通过源码启动），确保后端服务已正常运行。

### 2. 打开 Word 网页版

访问 [Microsoft 365 Word](https://www.office.com/)，登录你的 Microsoft 账户并打开或新建一个 Word 文档。

### 3. 加载加载项

1. 在 Word 网页版菜单栏点击 **插入 → 加载项**
2. 选择 **上传我的加载项**
3. 上传项目中 `frontend/microsoft_word_plugin` 目录下构建生成的 `manifest.xml` 文件
4. 上传成功后，在加载项面板中即可看到文策 AI

### 4. 开始使用

在加载项面板中即可看到文策 AI 的界面，使用方式与 WPS 加载项一致。

::: tip 提示
Microsoft Word 在线加载项需要后端服务启用 HTTPS。如果你使用的是本地部署方式，请确保后端服务已配置好 HTTPS 证书。
:::

## 下一步

请参考 [配置 API Key](/guide/api-config) 完成模型配置后即可开始使用。
