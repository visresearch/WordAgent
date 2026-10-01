STRINGS = {
    "app": {"name": "文策AI"},
    "tray": {"show": "显示", "quit": "退出文策AI", "tooltip": "文策AI"},
    "nav": {
        "home": "主页",
        "dashboard": "仪表盘",
        "wps": "WPS 加载项",
        "office": "Office 加载项",
        "mcp": "MCP 服务器",
        "console": "终端",
    },
    "home": {
        "subtitle": "让写作有策略，让表达更智能",
        "status": {
            "runningChecking": "后端服务运行中（正在检查更新）",
            "runningNoUpdateInfo": "后端服务运行中（未能获取更新信息）",
            "runningLatest": "后端服务运行中（已是最新版本）",
            "newVersion": "发现新版本：{tag}，请前往官网下载安装",
            "updateFailed": "更新检查失败",
        },
        "version": {"current": "当前版本：{version}", "unknown": "未知版本"},
        "update": {
            "checking": "正在检查更新...",
            "failed": "更新检查失败",
            "latest": "已是最新版本",
            "new": "有最新版本：{tag}",
        },
        "button": {"github": "GitHub", "website": "官网文档", "downloadLatest": "前往下载最新版本"},
        "cards": {
            "crossPlatform": {
                "title": "跨平台适配",
                "desc": "以 WPS 和 Microsoft Word 为载体，同时支持 Windows 和 Linux，让用户低门槛获得 AI 写作辅助体验。",
            },
            "richText": {
                "title": "原生富文本生成",
                "desc": "智能体理解 Word 文档结构，支持标题、正文、加粗、字体、缩进、行距等样式生成与编辑。",
            },
            "workflow": {
                "title": "工具化工作流",
                "desc": "通过文档工具、MCP 和 Skill 完成长文写作、资料查询与复杂编辑任务。",
            },
            "open": {
                "title": "自由开放",
                "desc": "支持自定义 API 或本地服务，兼容多数主流 LLM 服务商，模型选择更灵活。",
            },
        },
        "infobar": {"newVersion": {"title": "发现新版本", "content": "检测到最新版本 {tag}，请前往官网下载安装。"}},
    },
    "dashboard": {
        "title": "Token 使用仪表盘",
        "subtitle": "统计最近 文策AI token使用情况",
        "period": {"today": "当天", "7d": "7 天"},
        "metrics": {
            "inputTokens": "输入 Token",
            "outputTokens": "输出 Token",
            "cachedTokens": "缓存命中 Token",
            "cacheHitRate": "缓存命中率",
        },
        "chart": {"trend": "使用趋势", "empty": "暂无 Token 使用数据"},
        "status": {
            "loading": "正在加载…",
            "hover": "悬停图表可查看明细",
            "empty": "暂无使用记录",
            "failed": "数据读取失败，请稍后重试",
            "invalid": "Token 使用数据格式无效",
        },
        "tooltip": {"input": "输入：", "output": "输出：", "cached": "缓存命中："},
    },
    "console": {
        "title": "终端",
        "buttons": {"logDir": "日志文件夹", "clear": "清空", "bottom": "底部"},
        "hint": "显示应用运行过程中的所有日志输出",
        "tooltips": {"logDir": "打开日志文件夹", "clear": "清空日志", "bottom": "滚动到底部"},
        "error": {"openLogDir": "打开日志文件夹失败"},
    },
    "wps": {"title": "WPS Word加载项", "subtitle": "管理 WPS Office 加载项的安装与卸载"},
    "office": {
        "title": "Microsoft Word 加载项",
        "subtitle": "管理 Microsoft Word 网页版和客户端加载项的安装与启用",
        "usage": (
            "安装证书：<br/>"
            "1. 确保“启动 HTTPS 服务”。（进入本页面会自动启动）<br/>"
            "2. 点击“安装证书”按钮，在系统弹出的证书界面依次点击：安装证书-&gt;本地计算机-&gt;将所有的证书都放入下列存储-&gt;浏览-&gt;受信任的根证书颁发机构，然后一路确定即可。<br/>"
            "3. 点击“用浏览器打开”，如果没有不安全提示，代表证书安装成功；否则，重启后端服务软件再次点击“用浏览器打开”，如果依然有不安全提示，说明证书安装失败，请询问作者或自行安装证书。<br/><br/>"
            "网页版使用方法：<br/>"
            "1. 打开 <a href='https://word.cloud.microsoft/' style='color: #2563eb; text-decoration: underline;'>https://word.cloud.microsoft/</a> 并进入 Word 网页版。<br/>"
            "2. 进入：开始-&gt;加载项-&gt;更多加载项-&gt;我的加载项-&gt;管理我的加载项-&gt;上传我的加载项<br/>"
            "3. 上传下载好的 manifest.xml，完成加载。如果加载项界面未显示，请刷新页面。<br/><br/>"
            "客户端使用方法：<br/>"
            "1. 点击“下载 manifest.xml”保存一个空文件夹中。<br/>"
            "2. 右键属性这个文件夹，进入“共享”选项卡，点击“共享”，选择“Everyone”，点击“共享”并记下网络路径。<br/>"
            "3. 打开 Microsoft Word 客户端，进入：文件-&gt;选项-&gt;信任中心-&gt;信任中心设置-&gt;受信任的加载项目录，在“目录URL”中输入网络路径并点击添加目录，重启Word完成加载。<br/>"
            "4. 如果加载项界面未显示，进入：文件-&gt;选项-&gt;自定义功能区，将开发工具添加到“主选项卡”中。点击Word上方的“开发工具”选项卡，点击加载项-&gt;共享文件夹-&gt;文策AI助手，即可使用加载项。<br/><br/>"
            "【详细图文教程请访问 <a href='https://visresearch.github.io/WordAgent/' style='color: #2563eb; text-decoration: underline;'>https://visresearch.github.io/WordAgent/</a>】"
        ),
        "buttons": {
            "download": "下载 manifest.xml",
            "start": "启动 HTTPS 服务",
            "installCert": "安装证书",
            "openBrowser": "用浏览器打开",
            "stop": "关闭服务",
        },
        "status": {"running": "服务状态：运行中（https://{host}:{port}）", "stopped": "服务状态：未启动"},
        "infobar": {
            "downloadFailed": {"title": "下载失败", "contentMissing": "未找到 gui/resources/manifest.xml"},
            "downloadSuccess": {"title": "下载成功", "content": "manifest.xml 已保存到：{path}"},
            "openBrowser": {"title": "已在浏览器中打开"},
            "openBrowserFailed": {"title": "打开浏览器失败"},
            "certOpened": {"title": "已打开证书文件", "content": "请按照本界面提示操作"},
            "certFailed": {"title": "打开证书失败，请手动找到证书文件并安装，证书路径：{path}"},
            "serviceRunning": {"title": "提示", "content": "HTTPS 服务已在运行"},
            "startFailed": {
                "title": "启动失败",
                "contentMissingDist": "未找到 microsoft_word_plugin/dist，请先构建前端",
            },
            "startSuccess": {"title": "启动成功", "content": "HTTPS 服务已启动：https://{host}:{port}"},
            "stopped": {"title": "已关闭", "content": "HTTPS 服务已停止"},
            "stopFailed": {"title": "关闭失败"},
            "notRunning": {"title": "提示", "content": "HTTPS 服务未启动"},
        },
        "dialog": {"saveManifest": "保存 manifest.xml", "xmlFilter": "XML 文件 (*.xml)"},
    },
    "mcp": {
        "title": "MCP 服务器",
        "subtitle": "让 Codex 等客户端调用当前 WPS / Microsoft Word 文档工具",
        "endpoint": "连接地址：{url}",
        "running": "服务状态：运行中",
        "stopped": "服务状态：未启动",
        "backendUnavailable": "后端服务尚未就绪",
        "start": "运行",
        "stop": "停止",
        "startFailed": "MCP 服务器启动失败",
        "clients": "最近活跃客户端（{count}）",
        "client": "{name} · {seconds} 秒前有请求",
        "noClients": "暂无活跃客户端",
        "activityHint": "此服务使用无状态 HTTP；客户端发出请求后会显示 2 分钟，无法精确判断客户端程序是否仍打开。调用文档工具时还需打开 WPS / Microsoft Word 加载项侧栏。",
        "configTitle": "MCP JSON 配置",
    },
    "language": {
        "label": "界面语言",
        "english": "English",
        "chinese": "简体中文",
        "indonesian": "Bahasa Indonesia",
        "japanese": "日语",
        "korean": "韩语",
        "vietnamese": "越南语",
    },
    "common": {"unknownVersion": "未知版本", "save": "保存", "cancel": "取消"},
}
