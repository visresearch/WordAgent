export default {
  common: {
    add: '添加', cancel: '取消', clear: '清空', close: '关闭', confirm: '确定', delete: '删除',
    disabled: '已关闭', edit: '编辑', enabled: '已开启', loading: '加载中...', none: '无',
    refresh: '刷新', remove: '移除', retry: '重试', copy: '复制', save: '保存', saving: '保存中...',
    unknown: '未知', unknownError: '未知错误', pleaseRetry: '请稍后重试', testing: '测试中...'
  },
  language: {
    label: '界面语言', chinese: '简体中文', english: 'English'
  },
  windows: { assistant: '文策 AI 助手', settings: '设置', about: '关于', debug: '调试面板' },
  nav: { chat: 'AI 对话', history: '历史会话', settings: '设置', about: '关于', debug: '调试' },
  settings: {
    tabs: { general: '通用', model: '大模型', personalization: '个性化', mcp: 'MCP', skill: 'Skill', data: '数据管理' },
    generalTitle: '通用设置', generalDesc: '配置应用的基础行为',
    modelTitle: '大模型设置', modelDesc: '配置 AI 模型提供商和模型',
    personalizationTitle: '个性化设置', personalizationDesc: '自定义您的 AI 助手行为和响应参数',
    mcpTitle: 'MCP 服务器管理', mcpDesc: '管理 MCP 服务器名称和 JSON 配置，支持连接测试',
    skillTitle: 'Skill 管理', skillDesc: '查看和管理本地 Skill，支持上传、启用、打开文件夹和删除',
    save: '保存设置', saving: '保存中...', saved: '设置已保存！', saveFailed: '保存失败，请重试'
  },
  general: {
    title: '基础设置', subtitle: '配置应用的启动行为和显示模式', language: '界面语言',
    simplifiedChinese: '简体中文', english: 'English',
    showPanel: '启动时显示 AI 面板', proofread: '校对显示模式', proofreadMode: '校对显示模式',
    redBlue: '红蓝模式', redblue: '红蓝模式', redBlueDesc: '使用浅蓝色标记删除内容，浅红色标记新增内容',
    redblueDesc: '使用浅蓝色标记删除内容，浅红色标记新增内容',
    revision: '修订模式', revisionDesc: '使用 Word 修订功能标记修改内容', proxy: '网络代理',
    proxyTitle: '网络代理', proxyDesc: '配置 HTTP/HTTPS 请求的代理服务器',
    proxySubtitle: '配置 HTTP/HTTPS 请求的代理服务器', enableProxy: '启用代理',
    host: '代理地址 (IP)', proxyHost: '代理地址 (IP)', port: '端口',
    proxyHint: '提示：HTTP 和 HTTPS 请求将统一使用此代理。仅支持 HTTP 代理协议，不支持 SOCKS。'
  },
  skill: {
    title: 'Skill 管理', subtitle: '上传包含 SKILL.md 的 zip 压缩包，系统会自动解压到本地 skills 目录',
    upload: '上传 Skill 压缩包', uploading: '上传中...', tip: '仅支持 zip，且压缩包中需包含 SKILL.md',
    zipHint: '仅支持 ZIP，且压缩包中需包含 SKILL.md',
    loading: '正在加载 Skill 列表...', empty: '还没有 Skill，点击上方“上传 Skill 压缩包”开始配置。',
    unnamed: '未命名 Skill', toggle: '启用/禁用 Skill', openFolder: '打开 Skill 文件夹', delete: '删除',
    loadFailed: '加载 Skill 失败', zipOnly: '仅支持上传 zip 压缩包', uploadZipOnly: '仅支持上传 ZIP 压缩包', uploadSuccess: 'Skill 上传成功',
    uploadFailed: '上传 Skill 失败', updateFailed: '更新 Skill 状态失败', deleteConfirm: '确认删除 Skill：{name}？',
    deleteSuccess: 'Skill 删除成功', deleteFailed: '删除 Skill 失败', openFailed: '打开 Skill 文件夹失败',
    builtinDeleteDisabled: '内置 Skill 不能删除'
  },
  model: {
    title: '大模型服务商配置', subtitle: '管理 AI 服务提供商和模型设置', configured: '已配置的提供商',
    availableCount: '{count} 个可用模型', addProvider: '添加提供商', newProvider: '新提供商', modelCount: '{count} 个模型',
    name: '名称', namePlaceholder: '例如：openai', apiType: 'API 类型', openaiCompatible: 'OpenAI 兼容',
    fetchModels: '获取模型列表', fetch: '获取模型列表', fetching: '获取中...',
    collapseAvailable: '收起可用列表', collapse: '收起可用列表',
    availableModels: '可用模型 ({count})', clickToAdd: '点击 + 添加模型', addHint: '点击 + 添加模型', addModel: '添加模型', added: '已添加',
    addedModels: '已添加的模型 ({count})', remove: '移除', noModels: '暂无模型，请点击“获取模型列表”',
    empty: '暂无配置的提供商，点击上方“添加提供商”开始配置', deleteConfirm: '确定要删除此提供商吗？',
    credentialsRequired: '请先填写 API Key 和 Base URL', fetchFailed: '获取模型失败：{error}', checkConfig: '请检查配置'
  },
  mcp: {
    title: 'MCP 服务器配置', subtitle: '点击服务器卡片可展开编辑，不会打开新窗口', add: '添加服务器', addServer: '添加服务器',
    empty: '还没有 MCP 服务器，点击上方“添加服务器”开始配置。', unnamed: '未命名服务器',
    toggle: '启用/禁用 MCP 服务器', name: '服务器名称', serverName: '服务器名称', namePlaceholder: '例如：local-filesystem',
    config: '服务器配置 (JSON)', configPlaceholder: '请输入 MCP 服务器 JSON 配置', testing: '测试中...', test: '测试连接', testConnection: '测试连接',
    objectRequired: '配置必须是 JSON 对象（不能是数组或基础类型）', serversEmpty: 'mcpServers 不能为空对象',
    serverObjectRequired: 'mcpServers 中的服务器配置必须是对象', jsonError: 'JSON 格式错误：{error}',
    nameRequired: '请先填写服务器名称', configRequired: '请先填写服务器配置', fixJson: '请先修复 JSON 配置',
    success: '连接成功', failed: '连接失败'
  },
  personalization: {
    title: '自定义指令', instructions: '自定义指令', subtitle: '设置 AI 的全局提示词，影响所有对话',
    instructionsDesc: '设置 AI 的全局提示词，影响所有对话', globalPrompt: '全局提示词',
    promptHint: '在每次对话中都会被应用，帮助 AI 更好地理解你的需求',
    promptPlaceholder: '例如：你是一位专业的写作助手，擅长学术写作和文档编辑。请用简洁、专业的语言回答问题...',
    chars: '{count} 字符', quickTemplates: '快速模板', temperature: 'LLM 温度', temperatureDesc: '调整 AI 的创造性和随机性',
    precise: '精确模式 (0-0.33)', preciseDesc: '输出更确定、一致，适合事实性任务', balanced: '平衡模式 (0.33-0.67)',
    balancedDesc: '平衡准确性和创造性，适合大多数场景', creative: '创意模式 (0.67-1)', creativeDesc: '输出更随机、富有创造力，适合头脑风暴',
    clearConfirm: '确定要清空自定义指令吗？', overwriteConfirm: '应用模板将覆盖当前的自定义指令，是否继续？',
    templates: {
      academicName: '学术写作', academicDesc: '专业、严谨的学术风格', academicPrompt: '你是一位专业的学术写作助手，擅长撰写和编辑学术论文。请使用正式、严谨的学术语言，注重逻辑性和准确性。',
      creativeName: '创意写作', creativeDesc: '富有想象力的创作风格', creativePrompt: '你是一位富有创造力的写作助手，擅长创意写作和文学创作。请使用生动、形象的语言并鼓励创新思维。',
      businessName: '商务文档', businessDesc: '简洁、专业的商务风格', businessPrompt: '你是一位专业的商务写作助手，擅长撰写商务文档、报告和邮件。请确保内容清晰、简洁且重点突出。',
      casualName: '日常交流', casualDesc: '轻松、友好的对话风格', casualPrompt: '你是一位友好、平易近人的写作助手。请使用轻松、自然且易读的语言。'
    }
  },
  data: {
    title: '数据管理', subtitle: '管理应用数据和存储', cache: '清除缓存', clearCache: '清除缓存',
    cacheDesc: '清除 project/temp 与 project/uploads 下的缓存文件，释放磁盘空间', clearCacheDesc: '清除 project/temp 与 project/uploads 下的缓存文件，释放磁盘空间',
    cacheLocation: '缓存位置', cacheSize: '缓存大小', scan: '扫描缓存', scanning: '扫描中...', clear: '清除缓存', clearing: '清除中...',
    memory: '长期记忆', memoryDesc: '管理 AI 的持久化记忆，影响 AI 对您的长期理解（越靠上越旧，越靠下越新）',
    enableMemory: '启用长期记忆', memoryPlaceholder: '这里显示 AI 的长期记忆内容，您可以手动编辑后保存...',
    memoryHint: '提示：记忆按时间顺序排列，最新的记忆在底部。您可以删除不需要的记忆条目。', reload: '重新加载',
    saveMemory: '保存记忆', deleteAll: '删除所有数据', deleteAllDesc: '清除应用中的所有聊天记录和缓存数据',
    irreversible: '警告：此操作不可撤销', warning: '警告：此操作不可撤销', deleteIncludes: '删除所有数据将会清除：', chats: '所有聊天历史记录',
    cachedDocs: '缓存的文档数据', sessionState: '会话状态信息', confirmTitle: '确认删除所有数据？',
    confirmDesc: '此操作将永久删除所有数据，包括聊天记录、缓存和设置。此操作无法撤销。',
    confirmBody: '此操作将永久删除所有数据，包括聊天记录、缓存和设置。此操作无法撤销。', typeDelete: '请输入 DELETE 以确认：',
    typeDeletePlaceholder: '输入 DELETE', deletePlaceholder: '输入 DELETE', confirmDelete: '确认删除', deleting: '删除中...', calculating: '计算中...', noCache: '无缓存',
    cacheSummary: '{size}（{count} 个文件）', clearConfirm: '确定要清除缓存目录下的所有文件吗？', cleared: '已成功清除 {count} 个缓存文件',
    clearFailed: '清除缓存失败：{error}', deleted: '所有数据已成功删除！', deleteFailed: '删除失败：{error}',
    memoryLoadFailed: '加载长期记忆失败：{error}', memorySaved: '长期记忆保存成功！', memorySaveFailed: '保存长期记忆失败：{error}',
    memoryToggled: '长期记忆已{state}', memoryEnabled: '开启', memoryDisabled: '关闭',
    toggleFailed: '保存长期记忆开关失败：{error}'
  },
  session: {
    title: '历史会话', newChat: '新聊天', empty: '暂无历史会话', newConversation: '新对话', noMessages: '暂无消息',
    rename: '重命名', renameTitle: '重命名会话', renamePlaceholder: '输入新名称', deleteTitle: '确认删除',
    deleteBody: '确定要删除这个会话吗？此操作无法撤销。'
  },
  chat: {
    attachment: '附件', removeFile: '移除文件', chars: '{count} 字', clearSelection: '清除选区',
    allowThinking: '允许思考', disableThinking: '禁止思考', thinkingToggle: '启用或禁用深度思考',
    addFile: '添加文件', addSelection: '添加选区', send: '发送', stop: '终止',
    agentPlaceholder: '描述下一步要构建的内容', askPlaceholder: '输入要咨询的问题', planPlaceholder: '概述需要研究的目标或问题',
    chooseModel: '请选择模型', deleteParagraphs: '已修订删除 {count} 个段落', aiOperation: 'AI 修订：{actions}',
    context: '上下文：{current}k / {max}k tokens（{percentage}%）', unnamedFile: '未命名文件',
    unsupportedFiles: '以下文件格式不支持：{files}。仅支持 png、jpg、jpeg、pdf、docx、txt、md。',
    paragraphRange: '段落 {start} - {end}', showHistory: '显示历史聊天记录', whatCanIDo: '我能做什么',
    documentation: '使用文档', selectionRef: '引用选区 ({count})', fileRef: '引用文件 ({count})',
    unknownFile: '未知文件', preparing: '🧠 AI 正在准备中', thinking: '深度思考', thinkingDone: '深度思考（已结束）',
    collapseMcp: '收起 MCP 详情', expandMcp: '展开 MCP 详情', callMcp: '调用 MCP 工具：{name}',
    arguments: '参数：', noArguments: '无参数', toolOutput: '工具输出：', noOutput: '（无输出）',
    outputDocument: '输出到文档', copyImage: '复制图片', saveImage: '保存图片', selection: '选区',
    copyImageFailed: '复制失败，请尝试右键保存图片',
    mcpWaiting: '等待工具输出...', unknownArguments: '参数未知', imageTableSelection: '[图片+表格选区]',
    imageSelection: '[图片选区]', tableSelection: '[表格选区]', networkTimeout: '网络连接超时，已自动断开',
    networkError: '网络错误：{error}。请确保后端服务运行在 localhost:3880',
    networkInterruptedReconnecting: '网络连接已中断，本次请求已失败。正在自动恢复连接，请稍后重新发送。',
    readingDocumentById: '正在读取文档（段落 ID {start} - {end}）',
    readingDocument: '正在读取文档（段落 {start} - {end}）', searchingDocument: '正在搜索文档...',
    generatingDocument: '正在生成文档', documentInsertFailed: '文档插入失败，请检查目标位置和文档写入权限',
    deletePreview: 'AI 已生成删除修订（paraID：{ids}）', generatedPending: 'AI 已生成（{summary}，待确认）',
    wpsUnavailable: 'WPS API 不可用', openDocumentFirst: '请先打开一个 Word 文档', messageMissing: '消息不存在',
    undoFailed: '撤销失败：{error}', selectionUnavailable: '无法获取选区，请确保已在 WPS Word 中选中内容',
    selectionRangeUnavailable: '无法获取选区范围', selectContentFirst: '请先在文档中选中内容（可为文本、图片或表格）',
    selectionFailed: '处理选中内容时出错：{error}', insertFailed: '插入失败，请确保已打开 Word 文档', unnamedDocument: '未命名文档',
    searchComplete: '搜索完成', documentReadComplete: '文档读取完成', prepareDelete: '正在修订删除段落 ID（{ids}）',
    deleteComplete: '删除完成', insertBreakSuccess: '文档分隔符已插入', insertBreakFailed: '插入文档分隔符失败：{error}', createDocumentPending: '📄 正在创建新的空白 DOCX 文档', createDocumentSuccess: '📄 新的空白 DOCX 文档已创建并打开', createDocumentFailed: '创建新 DOCX 文档失败：{error}', documentGenerated: '文档已生成', errorLabel: '错误：{error}',
    paragraphCount: '{count} 个段落', tableCount: '{count} 个表格', pendingAddition: '待添加内容',
    input: {
      attachment: '附件', removeFile: '移除文件', paragraphRange: '段落 {start} - {end}', clearSelection: '清除选区',
      confirm: '确定', cancel: '取消', modelsLoading: '加载中...', thinkingAria: '启用或禁用深度思考',
      thinkingOn: '允许思考', thinkingOff: '禁止思考', addFile: '添加文件', addSelection: '添加选区', send: '发送', stop: '终止',
      agentPlaceholder: '描述下一步要构建的内容', askPlaceholder: '输入要咨询的问题', planPlaceholder: '概述需要研究的目标或问题',
      chooseModel: '请选择模型', deleteParagraphs: '已修订删除 {count} 个段落', aiOperation: 'AI 修订：{actions}',
      context: '上下文：{current}k / {max}k tokens（{percentage}%）', unnamedFile: '未命名文件', unsupportedFiles: '以下文件格式不支持：{files}。仅支持 png、jpg、pdf、docx、txt、md。'
    },
    messages: {
      showHistory: '显示历史聊天记录', empty: '我能做什么', docs: '使用文档', selections: '引用选区 ({count})',
      files: '引用文件 ({count})', unknownFile: '未知文件', preparing: '🧠 AI 正在准备中', thinking: '深度思考',
      thinkingDone: '深度思考（已结束）', collapseMcp: '收起 MCP 详情', expandMcp: '展开 MCP 详情',
      mcpCall: '调用 MCP 工具：{name}', parameters: '参数：', noParameters: '无参数', output: '工具输出：', noOutput: '（无输出）',
      copy: '复制', insert: '插入到 Word', retry: '重试', undo: '撤销'
    },
    session: {
      newChat: '新对话', title: '聊天记录', empty: '暂无聊天记录', rename: '重命名', delete: '删除',
      renameTitle: '重命名会话', renamePlaceholder: '输入会话名称', deleteTitle: '确认删除',
      deleteConfirm: '确定要删除这个会话吗？此操作无法撤销。'
    }
  },
  about: {
    name: '文策 AI 助手', product: '文策 AI 助手', version: '版本号', pluginType: '插件类型', wpsPlugin: 'WPS 文字加载项', wordPlugin: 'Microsoft Word 加载项',
    developer: '开发者', developerName: '日月星辰', links: '相关链接', repository: 'GitHub 仓库', website: '项目官网',
    docs: '使用文档', issues: '问题反馈', sponsor: '赞助作者', github: 'GitHub 仓库', unknownVersion: '未知版本'
  },
  debug: {
    title: '调试面板', hint: '按 F12 可以打开调试器', parse: '文档内容解析', parseSelection: '解析选中内容',
    showDocuments: '显示所有文件名', openDocuments: '已打开文档（{count}）', deleteParagraphs: '按索引删除段落',
    deletePlaceholder: '输入起始和结束段落索引（0-based），如：3, 7', clear: '清空', jsonToDoc: 'JSON 转文档',
    jsonPlaceholder: '粘贴 JSON 到此处...', apply: '应用到文档', export: '导出操作', copy: '复制到剪贴板',
    download: '下载 JSON 文件', deleteAction: '删除段落', result: '解析结果：', paragraphs: '段落：{count}', tables: '表格：{count}', images: '图片：{count}', chars: '字数：{count}'
  }
};
