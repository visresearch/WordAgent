export default {
  common: {
    add: '追加', cancel: 'キャンセル', clear: 'クリア', close: '閉じる', confirm: '確認', delete: '削除',
    disabled: '無効', edit: '編集', enabled: '有効', loading: '読み込み中...', none: 'なし',
    refresh: 'リフレッシュ', remove: '削除', retry: '再試行', copy: 'コピー', save: '保存', saving: '保存中...',
    unknown: '不明', unknownError: '不明なエラー', pleaseRetry: '後でもう一度お試しください', testing: 'テスト中...'
  },
  language: {
    label: 'インターフェース言語', chinese: '简体中文', english: 'English', indonesian: 'Bahasa Indonesia', japanese: '日本語', korean: '韓国語', vietnamese: 'ベトナム語'
  },
  windows: { assistant: '文策AI', settings: '設定', about: 'About', debug: 'デバッグパネル' },
  nav: { chat: 'AIチャット', history: 'チャット履歴', settings: '設定', about: 'About', debug: 'デバッグ' },
  settings: {
    tabs: { general: '一般', model: 'モデル', personalization: 'パーソナライズ', mcp: 'MCP', skill: 'スキル', data: 'データ' },
    generalTitle: '一般設定', generalDesc: 'アプリケーションの基本的な動作を構成',
    modelTitle: 'モデル設定', modelDesc: 'AIプロバイダーとモデルを管理',
    personalizationTitle: 'パーソナライズ', personalizationDesc: 'アシスタントの動作と応答パラメータをカスタマイズ',
    mcpTitle: 'MCPサーバー', mcpDesc: 'MCPサーバーの名前とJSON構成を管理し、接続テストを行う',
    skillTitle: 'スキル管理', skillDesc: 'ローカルスキルを管理：アップロード、有効化、フォルダーを開く、削除',
    save: '設定を保存', saving: '保存中...', saved: '設定が保存されました。', saveFailed: '保存に失敗しました。もう一度お試しください。'
  },
  general: {
    title: '基本設定', subtitle: '起動動作と表示モードを構成', language: 'インターフェース言語',
    simplifiedChinese: '简体中文', english: 'English', indonesian: 'Bahasa Indonesia', japanese: '日本語', korean: '韓国語', vietnamese: 'ベトナム語',
    showPanel: '起動時にAIパネルを表示', proofread: '校正表示モード', proofreadMode: '校正表示モード',
    redBlue: '赤青モード', redblue: '赤青モード', redBlueDesc: '削除箇所は淡い青、追加箇所は淡い赤でマーク',
    redblueDesc: '削除箇所は淡い青、追加箇所は淡い赤でマーク',
    revision: '変更履歴モード', revisionDesc: 'Wordの変更履歴を使用して編集をマーク', proxy: 'ネットワークプロキシ',
    proxyTitle: 'ネットワークプロキシ', proxyDesc: 'HTTP/HTTPSリクエストのためのプロキシサーバーを構成',
    proxySubtitle: 'ネットワークプロキシ', enableProxy: 'プロキシを有効化',
    host: 'プロキシアドレス (IP)', proxyHost: 'プロキシアドレス (IP)', port: 'ポート',
    proxyHint: 'HTTPとHTTPSのリクエストはこのプロキシを使用します。HTTPプロキシはサポートされていますが、SOCKSプロキシはサポートされていません。'
  },
  skill: {
    title: 'スキル管理', subtitle: 'SKILL.mdを含むZIPファイルをアップロードし、ローカルスキルディレクトリにインストール',
    upload: 'スキルZIPをアップロード', uploading: 'アップロード中...', tip: 'ZIPのみ対応；アーカイブにはSKILL.mdが含まれる必要があります',
    zipHint: 'ZIPのみ対応；アーカイブにはSKILL.mdが含まれる必要があります',
    loading: 'スキルの読み込み中...', empty: 'スキルがまだありません。「スキルZIPをアップロード」を使用して追加してください。', unnamed: '名前なしのスキル',
    toggle: 'スキルを有効/無効化', openFolder: 'スキルフォルダーを開く', delete: '削除', loadFailed: 'スキルの読み込みに失敗',
    zipOnly: 'ZIPアーカイブのみサポートされています', uploadZipOnly: 'ZIPアーカイブのみサポートされています', uploadSuccess: 'スキルがアップロードされました', uploadFailed: 'スキルのアップロードに失敗',
    updateFailed: 'スキルステータスの更新に失敗', deleteConfirm: 'スキルを削除しますか？ {name}', deleteSuccess: 'スキルが削除されました',
    deleteFailed: 'スキルの削除に失敗', openFailed: 'スキルフォルダーを開けません',
    builtinDeleteDisabled: '組み込みスキルは削除できません'
  },
  model: {
    title: 'AIプロバイダー構成', subtitle: 'AIプロバイダーとモデルを管理', configured: '構成済みプロバイダー',
    availableCount: '{count} 個の利用可能モデル', addProvider: 'プロバイダーを追加', newProvider: '新規プロバイダー', modelCount: '{count} 個のモデル',
    name: '名前', namePlaceholder: '例: openai', apiType: 'APIタイプ', openaiCompatible: 'OpenAI互換',
    fetchModels: 'モデルリストを取得', fetch: 'モデルリストを取得', fetching: '取得中...', collapseAvailable: '利用可能モデルを隠す', collapse: '利用可能モデルを隠す',
    availableModels: '利用可能モデル ({count})', clickToAdd: '＋をクリックしてモデルを追加', addHint: '＋をクリックしてモデルを追加', addModel: 'モデルを追加', added: '追加済み',
    addedModels: '追加済みモデル ({count})', remove: '削除', noModels: 'モデルがありません。まずモデルリストを取得してください。',
    empty: 'プロバイダーが構成されていません。「プロバイダーを追加」を使用してください。', deleteConfirm: 'このプロバイダーを削除しますか？',
    credentialsRequired: '先にAPIキーとベースURLを入力してください', fetchFailed: 'モデルの取得に失敗: {error}', checkConfig: '構成を確認'
  },
  mcp: {
    title: 'MCPサーバー構成', subtitle: 'サーバーカードをクリックして展開し編集', add: 'サーバーを追加', addServer: 'サーバーを追加',
    empty: 'MCPサーバーがまだありません。「サーバーを追加」を使用してください。', unnamed: '名前なしのサーバー', toggle: 'MCPサーバーを有効/無効化',
    name: 'サーバー名', serverName: 'サーバー名', namePlaceholder: '例: local-filesystem', config: 'サーバー構成 (JSON)',
    configPlaceholder: 'MCPサーバーのJSON構成を入力', testing: 'テスト中...', test: '接続テスト', testConnection: '接続テスト',
    objectRequired: '構成はオブジェクトである必要があります（配列またはプリミティブではありません）', serversEmpty: 'mcpServersは空にできません',
    serverObjectRequired: '各mcpServers構成はオブジェクトである必要があります', jsonError: '無効なJSON: {error}',
    nameRequired: 'サーバー名を入力してください', configRequired: 'サーバー構成を入力してください', fixJson: 'JSON構成を修正してください',
    success: '接続成功', failed: '接続失敗'
  },
  personalization: {
    title: 'カスタム指示', instructions: 'カスタム指示', subtitle: '会話のすべてで使用されるグローバルAIプロンプトを設定',
    instructionsDesc: '会話のすべてで使用されるグローバルAIプロンプトを設定', globalPrompt: 'グローバルプロンプト',
    promptHint: 'アシスタントがご要望を理解するのを助けるため、会話のすべてに適用されます',
    promptPlaceholder: '例: あなたはプロフェッショナルな執筆アシスタントです。簡潔で専門的な応答を心がけてください...',
    chars: '{count} 文字', quickTemplates: 'クイックテンプレート', temperature: 'LLM温度', temperatureDesc: 'AIの創造性とランダムネスを調整',
    precise: '正確 (0-0.33)', preciseDesc: 'より決定的で一貫性があり、事実に適したタスクに適する', balanced: 'バランス (0.33-0.67)',
    balancedDesc: '正確さと創造性のバランスを取り、ほとんどのタスクに適する', creative: '創造的 (0.67-1)', creativeDesc: 'より多様で想像力があり、ブレインストーミングに適した',
    clearConfirm: 'カスタム指示をクリアしますか？', overwriteConfirm: 'テンプレートを適用すると、現在の指示が置き換えられます。続行しますか？',
    templates: {
      academicName: '学術執筆', academicDesc: '公式で厳密な学術スタイル', academicPrompt: 'あなたはプロフェッショナルな学術執筆アシスタントです。明確な論理と正確な用語を使用し、公式かつ厳密な言葉で書きます。',
      creativeName: '創造的執筆', creativeDesc: '想像力豊かな創造的スタイル', creativePrompt: 'あなたは創造的な執筆アシスタントです。鮮やかな言葉を使い、オリジナルのアイデアと視点を促進します。',
      businessName: 'ビジネス文書', businessDesc: '簡潔で専門的なビジネススタイル', businessPrompt: 'あなたはプロフェッショナルなビジネス執筆アシスタントです。重要なポイントが明確な簡潔な文書、レポート、メールを作成します。',
      casualName: '日常会話', casualDesc: 'リラックスしてフレンドリーなスタイル', casualPrompt: 'あなたはフレンドリーで親しみやすい執筆アシスタントです。自然でリラックスして読みやすい言葉を使います。'
    }
  },
  data: {
    title: 'データ管理', subtitle: 'アプリケーションデータとストレージを管理', cache: 'キャッシュをクリア', clearCache: 'キャッシュをクリア',
    cacheDesc: 'project/temp と project/uploads からキャッシュファイルを削除してディスクスペースを確保', clearCacheDesc: 'project/temp と project/uploads からキャッシュファイルを削除してディスクスペースを確保',
    cacheLocation: 'キャッシュ場所', cacheSize: 'キャッシュサイズ', scan: 'スキャン', scanning: 'スキャン中...', clear: 'キャッシュをクリア', clearing: 'クリア中...',
    memory: '長期記憶', memoryDesc: '古いから新しい順に並べた永続的なAI記憶を管理', enableMemory: '長期記憶を有効化',
    memoryPlaceholder: 'ここに長期AI記憶が表示されます。編集して保存できます...', memoryHint: '記憶は時系列で並べられ、最新のエントリが下部にあります。',
    reload: 'リロード', saveMemory: '記憶を保存', deleteAll: 'すべてのデータを削除', deleteAllDesc: 'チャット履歴とキャッシュされたアプリケーションデータをすべて削除',
    irreversible: '警告: この操作は取り消せません', warning: '警告: この操作は取り消せません', deleteIncludes: 'すべてのデータを削除すると、以下が削除されます:', chats: 'すべてのチャット履歴',
    cachedDocs: 'キャッシュされたドキュメントデータ', sessionState: 'セッション状態', confirmTitle: 'すべてのデータを削除しますか？',
    confirmDesc: 'チャット、キャッシュ、設定を含むすべてのデータを永久に削除します。これは取り消せません。',
    confirmBody: 'チャット、キャッシュ、設定を含むすべてのデータを永久に削除します。これは取り消せません。', typeDelete: '確認のためDELETEを入力:',
    typeDeletePlaceholder: 'DELETEを入力', deletePlaceholder: 'DELETEを入力', confirmDelete: '永久に削除', deleting: '削除中...', calculating: '計算中...', noCache: 'キャッシュなし',
    cacheSummary: '{size} ({count} ファイル)', clearConfirm: 'キャッシュディレクトリのすべてのファイルをクリアしますか？', cleared: '{count} 個のキャッシュファイルを削除しました',
    clearFailed: 'キャッシュのクリアに失敗: {error}', deleted: 'すべてのデータが削除されました。', deleteFailed: '削除に失敗: {error}',
    memoryLoadFailed: '長期記憶の読み込みに失敗: {error}', memorySaved: '長期記憶が保存されました。', memorySaveFailed: '長期記憶の保存に失敗: {error}',
    memoryToggled: '長期記憶 {state}', memoryEnabled: '有効化', memoryDisabled: '無効化',
    toggleFailed: '記憶設定の保存に失敗: {error}'
  },
  session: {
    title: 'チャット履歴', newChat: '新規チャット', empty: 'チャット履歴がありません', newConversation: '新規会話', noMessages: 'メッセージがありません',
    rename: '名前を変更', renameTitle: '会話を名前を変更', renamePlaceholder: '新しい名前を入力', deleteTitle: '会話を削除',
    deleteBody: 'この会話を削除しますか？ この操作は取り消せません。'
  },
  chat: {
    attachment: '添付ファイル', removeFile: 'ファイルを削除', chars: '{count} 文字', clearSelection: '選択をクリア',
    allowThinking: '深い考える', disableThinking: '深い考えるオフ', thinkingToggle: '深い考えるを有効/無効化',
    addFile: 'ファイルを追加', addSelection: '選択を追加', send: '送信', stop: '停止',
    agentPlaceholder: '次に構築するものを説明', askPlaceholder: '質問を入力',
    chooseModel: 'モデルを選択', deleteParagraphs: '{count} 段落を削除', aiOperation: 'AI改訂: {actions} (保留中の確認)', revisionCount: '{count} 件の変更',
    acceptRevision: '採用', rejectRevision: '却下',
    context: 'コンテキスト: {current}k / {max}k トークン ({percentage}%)', unnamedFile: '名前なしのファイル',
    unsupportedFiles: 'サポートされていないファイル: {files}。サポート形式: png, jpg, jpeg, pdf, docx, txt, md。',
    paragraphRange: '段落 {start} - {end}', showHistory: 'チャット履歴を表示', whatCanIDo: '何をできる？',
    documentation: 'ドキュメント', selectionRef: '参照選択 ({count})', fileRef: '参照ファイル ({count})',
    unknownFile: '不明なファイル', preparing: 'AIが準備中', thinking: '深い考える', thinkingDone: '深い考える (完了)',
    contextCompactionStarted: '🗜️ コンテキストを自動的に圧縮中', contextCompactionCompleted: '✅ コンテキストの圧縮完了',
    collapseMcp: 'MCP詳細を折りたたむ', expandMcp: 'MCP詳細を展開', callMcp: 'MCPツールを呼び出し中: {name}',
    arguments: '引数:', noArguments: '引数なし', toolOutput: 'ツール出力:', noOutput: '(出力なし)',
    outputDocument: 'ドキュメントに挿入', copyImage: '画像をコピー', saveImage: '画像を保存', selection: '選択',
    copyImageFailed: 'コピーに失敗しました。コンテキストメニューから画像を保存してください。',
    mcpWaiting: 'ツール出力を待機中...', unknownArguments: '引数利用不可', imageTableSelection: '[画像と表の選択]',
    imageSelection: '[画像選択]', tableSelection: '[表選択]', networkTimeout: 'ネットワーク接続がタイムアウトし、閉じられました。',
    networkError: 'ネットワークエラー: {error}。バックエンドサービスがlocalhost:3880で実行されていることを確認してください。',
    networkInterruptedReconnecting: '接続が切断され、このリクエストが失敗しました。自動的に再接続していますので、しばらくしてから再送してください。',
    readingDocumentById: 'ドキュメントを読み込み中 (段落ID {start} - {end})',
    readingDocument: 'ドキュメントを読み込み中 (段落 {start} - {end})', searchingDocument: 'ドキュメント検索中...',
    generatingDocument: 'ドキュメント生成中', documentInsertFailed: 'ドキュメントの挿入に失敗しました。ターゲット位置とドキュメントの権限を確認してください。',
    deletePreview: '{ids} を削除', generatedPending: '{summary} が生成されました',
    wpsUnavailable: 'WPS APIが利用不可です', openDocumentFirst: 'Wordドキュメントを開いてください', messageMissing: 'メッセージが見つかりません',
    undoFailed: '元に戻しに失敗: {error}', selectionUnavailable: '選択内容を読み取れません。WPS Writerでコンテンツを選択してください。',
    selectionRangeUnavailable: '選択範囲を特定できません', selectContentFirst: 'ドキュメントでテキスト、画像、または表を選択してください。',
    selectionFailed: '選択内容の処理に失敗: {error}', insertFailed: '挿入に失敗しました。Wordドキュメントが開かれていることを確認してください。', unnamedDocument: '名前なしのドキュメント',
    searchComplete: '検索完了', documentReadComplete: 'ドキュメント読み込み完了', prepareDelete: '段落ID ({ids}) に対する追跡削除を適用中',
    deleteComplete: '削除完了', insertBreakSuccess: 'ドキュメント改行を挿入', insertBreakFailed: 'ドキュメント改行の挿入に失敗: {error}', createDocumentPending: '新しい空のDOCXドキュメントを作成中', createDocumentSuccess: '新しい空のDOCXドキュメントが作成され、開かれました', createDocumentFailed: '新しいDOCXドキュメントの作成に失敗: {error}', documentGenerated: 'ドキュメントが生成されました', errorLabel: 'エラー: {error}',
    paragraphCount: '{count} 段落', tableCount: '{count} 表', summarySeparator: ', ', actionSeparator: ', ', pendingAddition: '保留中の追加',
    input: {
      attachment: '添付ファイル', removeFile: 'ファイルを削除', paragraphRange: '段落 {start} - {end}', clearSelection: '選択をクリア',
      confirm: '確認', cancel: 'キャンセル', modelsLoading: '読み込み中...', thinkingAria: '深い考えるを有効/無効化',
      thinkingOn: '深い考えるオン', thinkingOff: '深い考えるオフ', addFile: 'ファイルを追加', addSelection: '選択を追加', send: '送信', stop: '停止',
      agentPlaceholder: '次に構築するものを説明', askPlaceholder: '質問を入力',
      chooseModel: 'モデルを選択', deleteParagraphs: '{count} 段落を削除', aiOperation: 'AI改訂: {actions} (保留中の確認)',
      context: 'コンテキスト: {current}k / {max}k トークン ({percentage}%)', unnamedFile: '名前なしのファイル',
      unsupportedFiles: 'サポートされていないファイル: {files}。サポート形式: png, jpg, pdf, docx, txt, md。'
    },
    messages: {
      showHistory: 'チャット履歴を表示', empty: '何をできる？', docs: 'ドキュメント', selections: '参照選択 ({count})',
      files: '参照ファイル ({count})', unknownFile: '不明なファイル', preparing: 'AIが準備中', thinking: '深い考える',
      thinkingDone: '深い考える (完了)', collapseMcp: 'MCP詳細を折りたたむ', expandMcp: 'MCP詳細を展開',
      mcpCall: 'MCPツールを呼び出し中: {name}', parameters: '引数:', noParameters: '引数なし', output: 'ツール出力:', noOutput: '(出力なし)',
      copy: 'コピー', insert: 'Wordに挿入', retry: '再試行', undo: '元に戻す'
    },
    session: {
      newChat: '新規チャット', title: 'チャット履歴', empty: 'チャット履歴がありません', rename: '名前を変更', delete: '削除',
      renameTitle: '会話を名前を変更', renamePlaceholder: '会話の名前を入力', deleteTitle: '会話を削除',
      deleteConfirm: 'この会話を削除しますか？ この操作は取り消せません。'
    }
  },
  about: {
    name: '文策AI', product: '文策AI', version: 'Version', pluginType: 'Add-in type', wpsPlugin: 'WPS Writer add-in', wordPlugin: 'Microsoft Word add-in',
    developer: 'Developer', developerName: 'Riyue Xingchen', links: 'Links', repository: 'GitHub repository', website: 'Project website',
    docs: 'Documentation', issues: 'Report an issue', sponsor: 'Sponsor the author', github: 'GitHub repository', unknownVersion: 'Unknown version'
  },
  debug: {
    title: 'デバッグパネル', hint: '開発者ツールを開くにはF12を押す', parse: 'ドキュメント内容を解析', parseSelection: '選択を解析',
    showDocuments: '開いているファイル名を表示', openDocuments: '開いているドキュメント ({count})', deleteParagraphs: 'インデックスによる段落削除',
    deletePlaceholder: '例: 3, 7 のように、0から始まる段落インデックスを入力', clear: 'クリア', jsonToDoc: 'JSONをドキュメントに',
    jsonPlaceholder: 'ここにJSONを貼り付け...', apply: 'ドキュメントに適用', export: 'エクスポート', copy: 'クリップボードにコピー',
    download: 'JSONをダウンロード', deleteAction: '段落を削除', result: '解析結果:', paragraphs: '段落: {count}', tables: '表: {count}', images: '画像: {count}', chars: '文字数: {count}'
  }
};
