STRINGS = {
    "app": {"name": "WenCe AI"},
    "tray": {"show": "Show", "quit": "Quit WenCe AI", "tooltip": "WenCe AI"},
    "nav": {
        "home": "Home",
        "dashboard": "Dashboard",
        "wps": "WPS Add-in",
        "office": "Office Add-in",
        "mcp": "MCP Server",
        "console": "Console",
    },
    "home": {
        "subtitle": "Strategic writing, smarter expression",
        "status": {
            "runningChecking": "Backend running (checking for updates)",
            "runningNoUpdateInfo": "Backend running (unable to fetch update info)",
            "runningLatest": "Backend running (up to date)",
            "newVersion": "New version available: {tag}, please download from website",
            "updateFailed": "Update check failed",
        },
        "version": {"current": "Current version: {version}", "unknown": "Unknown version"},
        "update": {
            "checking": "Checking for updates...",
            "failed": "Update check failed",
            "latest": "Up to date",
            "new": "New version: {tag}",
        },
        "button": {"github": "GitHub", "website": "Website Docs", "downloadLatest": "Download Latest Version"},
        "cards": {
            "crossPlatform": {
                "title": "Cross-Platform",
                "desc": "Built for WPS and Microsoft Word, supporting Windows and Linux for low-barrier AI writing assistance.",
            },
            "richText": {
                "title": "Native Rich Text",
                "desc": "Agent understands Word document structure, supporting headings, body, bold, fonts, indents, line spacing and more.",
            },
            "workflow": {
                "title": "Tool-based Workflow",
                "desc": "Complete long-form writing, research and complex editing via document tools, MCP and Skills.",
            },
            "open": {
                "title": "Open & Flexible",
                "desc": "Supports custom APIs or local services, compatible with most mainstream LLM providers.",
            },
        },
        "infobar": {
            "newVersion": {
                "title": "New Version Available",
                "content": "Latest version {tag} detected, please download from website.",
            }
        },
    },
    "dashboard": {
        "title": "Token Usage Dashboard",
        "subtitle": "Recent WenCe AI token usage statistics",
        "period": {"today": "Today", "7d": "7 Days"},
        "metrics": {
            "inputTokens": "Input Tokens",
            "outputTokens": "Output Tokens",
            "cachedTokens": "Cached Tokens",
            "cacheHitRate": "Cache Hit Rate",
        },
        "chart": {"trend": "Usage Trend", "empty": "No Token Usage Data"},
        "status": {
            "loading": "Loading...",
            "hover": "Hover chart for details",
            "empty": "No usage records",
            "failed": "Failed to load data, please retry",
            "invalid": "Invalid token usage data format",
        },
        "tooltip": {"input": "Input:", "output": "Output:", "cached": "Cached:"},
    },
    "console": {
        "title": "Console",
        "buttons": {"logDir": "Log Folder", "clear": "Clear", "bottom": "Bottom"},
        "hint": "Shows all log output during app runtime",
        "tooltips": {"logDir": "Open log folder", "clear": "Clear logs", "bottom": "Scroll to bottom"},
        "error": {"openLogDir": "Failed to open log folder"},
    },
    "wps": {"title": "WPS Word Add-in", "subtitle": "Manage WPS Office add-in installation"},
    "office": {
        "title": "Microsoft Word Add-in",
        "subtitle": "Manage Microsoft Word web and desktop add-in installation",
        "usage": (
            "Install certificate:<br/>"
            '1. Ensure "Start HTTPS Service" is running. (Auto-starts when you open this page)<br/>'
            '2. Click "Install Certificate", then in the system dialog: Install Certificate -&gt; Local Machine -&gt; Place all certificates in the following store -&gt; Browse -&gt; Trusted Root Certification Authorities, then confirm.<br/>'
            '3. Click "Open in Browser", if no security warning appears, certificate is installed; otherwise restart backend and try again. If still warning, install manually or contact author.<br/><br/>'
            "Web version:<br/>"
            "1. Open <a href='https://word.cloud.microsoft/' style='color: #2563eb; text-decoration: underline;'>https://word.cloud.microsoft/</a> and enter Word for the web.<br/>"
            "2. Go to: Home -&gt; Add-ins -&gt; More Add-ins -&gt; My Add-ins -&gt; Manage My Add-ins -&gt; Upload My Add-in<br/>"
            "3. Upload the downloaded manifest.xml. Refresh if add-in panel doesn't appear.<br/><br/>"
            "Desktop version:<br/>"
            '1. Click "Download manifest.xml" and save to an empty folder.<br/>'
            "2. Right-click folder -&gt; Properties -&gt; Sharing -&gt; Share -&gt; Everyone -&gt; Share and note the network path.<br/>"
            "3. Open Microsoft Word: File -&gt; Options -&gt; Trust Center -&gt; Trust Center Settings -&gt; Trusted Add-in Catalogs, enter network path and Add Catalog, restart Word.<br/>"
            "4. If panel doesn't appear: File -&gt; Options -&gt; Customize Ribbon, add Developer to Main Tabs. Click Developer -&gt; Add-ins -&gt; Shared Folder -&gt; WenCe AI Assistant.<br/><br/>"
            "【Detailed guide: <a href='https://visresearch.github.io/WordAgent/' style='color: #2563eb; text-decoration: underline;'>https://visresearch.github.io/WordAgent/</a>】"
        ),
        "buttons": {
            "download": "Download manifest.xml",
            "start": "Start HTTPS Service",
            "installCert": "Install Certificate",
            "openBrowser": "Open in Browser",
            "stop": "Stop Service",
        },
        "status": {"running": "Service running (https://{host}:{port})", "stopped": "Service not running"},
        "infobar": {
            "downloadFailed": {"title": "Download Failed", "contentMissing": "gui/resources/manifest.xml not found"},
            "downloadSuccess": {"title": "Download Successful", "content": "manifest.xml saved to: {path}"},
            "openBrowser": {"title": "Opened in Browser"},
            "openBrowserFailed": {"title": "Failed to Open Browser"},
            "certOpened": {
                "title": "Certificate File Opened",
                "content": "Please follow the instructions on this page",
            },
            "certFailed": {"title": "Failed to open certificate, please find and install manually, path: {path}"},
            "serviceRunning": {"title": "Notice", "content": "HTTPS service is already running"},
            "startFailed": {
                "title": "Failed to Start",
                "contentMissingDist": "microsoft_word_plugin/dist not found, please build frontend first",
            },
            "startSuccess": {
                "title": "Started Successfully",
                "content": "HTTPS service started: https://{host}:{port}",
            },
            "stopped": {"title": "Stopped", "content": "HTTPS service stopped"},
            "stopFailed": {"title": "Failed to Stop"},
            "notRunning": {"title": "Notice", "content": "HTTPS service not running"},
        },
        "dialog": {"saveManifest": "Save manifest.xml", "xmlFilter": "XML Files (*.xml)"},
    },
    "mcp": {
        "title": "MCP Server",
        "subtitle": "Allow clients such as Codex to use tools for the current WPS / Microsoft Word document",
        "endpoint": "Endpoint: {url}",
        "running": "Server running",
        "stopped": "Server stopped",
        "backendUnavailable": "Backend service is not ready",
        "start": "Run",
        "stop": "Stop",
        "startFailed": "Failed to start MCP server",
        "clients": "Recently active clients ({count})",
        "client": "{name} · request {seconds}s ago",
        "noClients": "No active clients",
        "activityHint": "This server uses stateless HTTP. Clients appear for 2 minutes after a request; whether the client application is still open cannot be determined exactly. Open the WPS / Microsoft Word add-in pane to use document tools.",
        "configTitle": "MCP JSON configuration",
    },
    "language": {
        "label": "Language",
        "english": "English",
        "chinese": "简体中文",
        "indonesian": "Bahasa Indonesia",
        "japanese": "Japanese",
        "korean": "Korean",
        "vietnamese": "Vietnamese",
    },
    "common": {"unknownVersion": "Unknown version", "save": "Save", "cancel": "Cancel"},
}
