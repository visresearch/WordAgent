# 启动 Microsoft Word 加载项

## 前提条件

- 已完成 [文策 AI 安装](/guide/installation)。
- 可使用 Microsoft Word 桌面版或 [Word 网页版](https://word.cloud.microsoft/)。
- 桌面版建议使用 Office 2019/2021 或 Microsoft 365 的最新版本。

Microsoft Word 加载项通过 HTTPS 连接本机的文策 AI 后端。使用期间需要保持文策 AI 和 HTTPS 服务运行。

## 1. 启动 HTTPS 服务并信任证书

打开文策 AI 桌面程序，进入 Microsoft Word 页面：

1. 点击 **安装证书**。
2. 点击 **启动 HTTPS 服务**。
3. 点击 **用浏览器打开**，确认浏览器能够正常打开本地页面。

![](/MSoffice_pyQt.png)

Windows 用户在证书向导中将证书放入“受信任的根证书颁发机构”：

<div style="display:flex; gap:12px; flex-wrap:nowrap; align-items:flex-start;">
  <img src="/cert1.png" alt="证书安装步骤 1" style="flex:1 1 0; min-width:0; max-width:100%; height:auto;" />
  <img src="/cert2.png" alt="证书安装步骤 2" style="flex:1 1 0; min-width:0; max-width:100%; height:auto;" />
</div>

![](/cert3.png)

macOS 用户点击证书后会打开“钥匙串访问”。将证书加入当前用户钥匙串，打开证书的“信任”设置，将“使用此证书时”设为“始终信任”，然后重新启动 Word。

## 2. 下载 manifest

在同一页面点击 **下载 manifest.xml**，将文件保存到本地。后续根据使用方式选择 Word 网页版、Windows 桌面版或 macOS 桌面版。

## 3. Word 网页版

1. 打开 [Word 网页版](https://word.cloud.microsoft/) 并登录 Microsoft 365。
2. 进入 **开始 → 加载项 → 更多加载项 → 我的加载项 → 管理我的加载项 → 上传我的加载项**。
3. 上传刚才下载的 `manifest.xml`。
4. 如果侧边栏没有立即显示，刷新 Word 页面。

![](/MSoffice_web.png)

## 4. Windows 桌面版

1. 将 `manifest.xml` 放进一个单独文件夹。
2. 在文件夹的 **属性 → 共享 → 共享** 中添加 `Everyone`，记录网络路径。

![](/share_folder.png)

3. 在 Word 中进入 **文件 → 选项 → 信任中心 → 信任中心设置 → 受信任的加载项目录**。
4. 添加上一步的网络路径，勾选“显示在菜单中”，然后重启 Word。

![](/trusted_center.png)

5. 如果功能区没有“开发工具”，在 **文件 → 选项 → 自定义功能区** 中启用它。

![](/custom_ribbon.png)

6. 打开 **开发工具 → 加载项 → 共享文件夹 → 文策 AI 助手**。

![](/load_addin.png)

## 5. macOS 桌面版

1. 完全退出 Microsoft Word。
2. 在终端创建 Word 的侧载目录：

```bash
mkdir -p ~/Library/Containers/com.microsoft.Word/Data/Documents/wef
```

3. 将下载的 `manifest.xml` 复制到该目录。例如文件位于“下载”目录时：

```bash
cp ~/Downloads/manifest.xml ~/Library/Containers/com.microsoft.Word/Data/Documents/wef/manifest.xml
```

4. 重新打开 Word，在 **插入/开始 → 加载项 → 我的加载项** 中打开 **文策 AI 助手**。

如果加载项不存在，确认 manifest 文件名和目录正确，并确保 Word 在复制文件时已完全退出。

## 6. 开始使用

加载项出现后，进入 [配置大模型服务](/guide/api-config)，添加并选择 DeepSeek V4 Pro。
