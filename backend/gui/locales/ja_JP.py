STRINGS = {
    "app": {"name": "WenCe AI"},
    "tray": {"show": "表示", "quit": "終了", "tooltip": "WenCe AI"},
    "nav": {
        "home": "ホーム",
        "dashboard": "ダッシュボード",
        "wps": "WPSアドイン",
        "office": "Officeアドイン",
        "mcp": "MCPサーバー",
        "console": "コンソール",
    },
    "home": {
        "subtitle": "戦略的な執筆、よりスマートな表現",
        "status": {
            "runningChecking": "バックエンド実行中（更新確認中）",
            "runningNoUpdateInfo": "バックエンド実行中（更新情報を取得できません）",
            "runningLatest": "バックエンド実行中（最新です）",
            "newVersion": "新しいバージョンがあります: {tag}、ウェブサイトからダウンロードしてください",
            "updateFailed": "更新確認に失敗しました",
        },
        "version": {"current": "現在のバージョン: {version}", "unknown": "不明"},
        "update": {
            "checking": "更新を確認中...",
            "failed": "更新確認に失敗しました",
            "latest": "最新です",
            "new": "新しいバージョン: {tag}",
        },
        "button": {
            "github": "GitHub",
            "website": "ウェブサイトドキュメント",
            "downloadLatest": "最新バージョンをダウンロード",
        },
        "cards": {
            "crossPlatform": {
                "title": "クロスプラットフォーム",
                "desc": "WPSとMicrosoft Word向けに構築、WindowsとLinuxをサポートし、AI執筆支援の敷居を下げます。",
            },
            "richText": {
                "title": "ネイティブリッチテキスト",
                "desc": "エージェントはWord文書構造を理解し、見出し、本文、太字、フォント、インデント、行間などをサポートします。",
            },
            "workflow": {
                "title": "ツールベースのワークフロー",
                "desc": "ドキュメントツール、MCP、Skillsを活用して長文執筆、調査、複雑な編集を完了します。",
            },
            "open": {
                "title": "オープン＆フレキシブル",
                "desc": "カスタムAPIやローカルサービスをサポート、主流のLLMプロバイダーと互換性があります。",
            },
        },
        "infobar": {
            "newVersion": {
                "title": "新しいバージョンが利用可能",
                "content": "最新バージョン{tag}を検出しました。ウェブサイトからダウンロードしてください。",
            }
        },
    },
    "dashboard": {
        "title": "トークン使用量ダッシュボード",
        "subtitle": "最近のWenCe AIトークン使用量統計",
        "period": {"today": "今日", "7d": "7日間"},
        "metrics": {
            "inputTokens": "入力トークン",
            "outputTokens": "出力トークン",
            "cachedTokens": "キャッシュトークン",
            "cacheHitRate": "キャッシュヒット率",
        },
        "chart": {"trend": "使用量トレンド", "empty": "トークン使用量データがありません"},
        "status": {
            "loading": "読み込み中...",
            "hover": "詳細はチャートにホバーしてください",
            "empty": "使用記録がありません",
            "failed": "データの読み込みに失敗しました。再試行してください",
            "invalid": "無効なトークン使用量データ形式",
        },
        "tooltip": {"input": "入力:", "output": "出力:", "cached": "キャッシュ:"},
    },
    "console": {
        "title": "コンソール",
        "buttons": {"logDir": "ログフォルダ", "clear": "クリア", "bottom": "下部へ"},
        "hint": "アプリ実行中のすべてのログ出力を表示します",
        "tooltips": {"logDir": "ログフォルダを開く", "clear": "ログをクリア", "bottom": "下部へスクロール"},
        "error": {"openLogDir": "ログフォルダを開けませんでした"},
    },
    "wps": {"title": "WPS Wordアドイン", "subtitle": "WPS Officeアドインのインストールを管理"},
    "office": {
        "title": "Microsoft Wordアドイン",
        "subtitle": "Microsoft WordのWeb版とデスクトップ版アドインのインストールを管理",
        "usage": (
            "証明書のインストール:<br/>"
            "1. 「HTTPSサービスを開始」が実行されていることを確認してください。（このページを開くと自動的に開始されます）<br/>"
            "2. 「証明書をインストール」をクリックし、システムダイアログで：証明書のインストール -> ローカルコンピュータ -> すべての証明書を次のストアに配置 -> 参照 -> 信頼されたルート証明機関、その後確定します。<br/>"
            "3. 「ブラウザで開く」をクリックし、セキュリティ警告が表示されなければ証明書のインストールは成功です。それ以外の場合は、バックエンドサービスを再起動して再度試してください。それでも警告が表示される場合は、手動でインストールするか、作者にお問い合わせください。<br/><br/>"
            "Web版の使用方法:<br/>"
            "1. <a href='https://word.cloud.microsoft/' style='color: #2563eb; text-decoration: underline;'>https://word.cloud.microsoft/</a> を開き、Word for the webに入ります。<br/>"
            "2. 移動：ホーム -> アドイン -> その他のアドイン -> マイアドイン -> マイアドインの管理 -> マイアドインのアップロード<br/>"
            "3. ダウンロードしたmanifest.xmlをアップロードします。アドインパネルが表示されない場合は更新してください。<br/><br/>"
            "デスクトップ版の使用方法:<br/>"
            "1. 「manifest.xmlをダウンロード」をクリックし、空のフォルダに保存します。<br/>"
            "2. フォルダを右クリック -> プロパティ -> 共有 -> 共有 -> 全員 -> 共有し、ネットワークパスをメモします。<br/>"
            "3. Microsoft Wordを開きます：ファイル -> オプション -> トラストセンター -> トラストセンターの設定 -> 信頼されたアドインカタログ、ネットワークパスを入力してカタログを追加し、Wordを再起動します。<br/>"
            "4. パネルが表示されない場合：ファイル -> オプション -> リボンのユーザー設定で、開発ツールをメインタブに追加します。Wordの「開発ツール」タブをクリックし、アドイン -> 共有フォルダ -> WenCe AI Assistantを選択します。<br/><br/>"
            "【詳細ガイド: <a href='https://visresearch.github.io/WordAgent/' style='color: #2563eb; text-decoration: underline;'>https://visresearch.github.io/WordAgent/</a>】"
        ),
        "buttons": {
            "download": "manifest.xmlをダウンロード",
            "start": "HTTPSサービスを開始",
            "installCert": "証明書をインストール",
            "openBrowser": "ブラウザで開く",
            "stop": "サービスを停止",
        },
        "status": {"running": "サービス実行中 (https://{host}:{port})", "stopped": "サービスが実行されていません"},
        "infobar": {
            "downloadFailed": {
                "title": "ダウンロード失敗",
                "contentMissing": "gui/resources/manifest.xmlが見つかりません",
            },
            "downloadSuccess": {"title": "ダウンロード成功", "content": "manifest.xmlを保存しました: {path}"},
            "openBrowser": {"title": "ブラウザで開きました"},
            "openBrowserFailed": {"title": "ブラウザを開けませんでした"},
            "certOpened": {"title": "証明書ファイルを開きました", "content": "このページの指示に従ってください"},
            "certFailed": {
                "title": "証明書を開けませんでした",
                "content": "手動で見つけてインストールしてください。パス: {path}",
            },
            "serviceRunning": {"title": "お知らせ", "content": "HTTPSサービスは既に実行中です"},
            "startFailed": {
                "title": "開始に失敗しました",
                "contentMissingDist": "microsoft_word_plugin/distが見つかりません。先にフロントエンドをビルドしてください",
            },
            "startSuccess": {
                "title": "正常に開始しました",
                "content": "HTTPSサービスを開始しました: https://{host}:{port}",
            },
            "stopped": {"title": "停止しました", "content": "HTTPSサービスを停止しました"},
            "stopFailed": {"title": "停止に失敗しました"},
            "notRunning": {"title": "お知らせ", "content": "HTTPSサービスが実行されていません"},
        },
        "dialog": {"saveManifest": "manifest.xmlを保存", "xmlFilter": "XMLファイル (*.xml)"},
    },
    "mcp": {
        "title": "MCPサーバー",
        "subtitle": "Codexなどのクライアントから現在のWPS / Microsoft Word文書を操作できます",
        "endpoint": "接続先：{url}",
        "running": "サーバー稼働中",
        "stopped": "サーバー停止中",
        "backendUnavailable": "バックエンドはまだ準備できていません",
        "start": "起動",
        "stop": "停止",
        "startFailed": "MCPサーバーを起動できませんでした",
        "clients": "最近アクティブなクライアント（{count}）",
        "client": "{name} · {seconds}秒前にリクエスト",
        "noClients": "アクティブなクライアントはありません",
        "activityHint": "このサーバーはステートレスHTTPを使用します。リクエスト後2分間表示されますが、クライアントアプリが開いているかは正確には判定できません。文書ツールを使うにはWPS / Microsoft Wordアドインを開いてください。",
        "configTitle": "MCP JSON 設定",
    },
    "language": {
        "label": "言語",
        "english": "English",
        "chinese": "简体中文",
        "indonesian": "Bahasa Indonesia",
        "japanese": "日本語",
        "korean": "한국어",
        "vietnamese": "Tiếng Việt",
    },
    "common": {"unknownVersion": "不明なバージョン", "save": "保存", "cancel": "キャンセル"},
}
