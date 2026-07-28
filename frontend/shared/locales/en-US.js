export default {
  common: {
    add: 'Add', cancel: 'Cancel', clear: 'Clear', close: 'Close', confirm: 'Confirm', delete: 'Delete',
    disabled: 'Disabled', edit: 'Edit', enabled: 'Enabled', loading: 'Loading...', none: 'None',
    refresh: 'Refresh', remove: 'Remove', retry: 'Retry', copy: 'Copy', save: 'Save', saving: 'Saving...',
    unknown: 'Unknown', unknownError: 'Unknown error', pleaseRetry: 'Please try again later', testing: 'Testing...'
  },
  language: {
    label: 'Interface language', chinese: '简体中文', english: 'English'
  },
  windows: { assistant: 'WenCe AI Assistant', settings: 'Settings', about: 'About', debug: 'Debug panel' },
  nav: { chat: 'AI chat', history: 'Chat history', settings: 'Settings', about: 'About', debug: 'Debug' },
  settings: {
    tabs: { general: 'General', model: 'Models', personalization: 'Personalization', mcp: 'MCP', skill: 'Skills', data: 'Data' },
    generalTitle: 'General settings', generalDesc: 'Configure basic application behavior',
    modelTitle: 'Model settings', modelDesc: 'Configure AI providers and models',
    personalizationTitle: 'Personalization', personalizationDesc: 'Customize assistant behavior and response parameters',
    mcpTitle: 'MCP servers', mcpDesc: 'Manage MCP server names and JSON configurations, with connection testing',
    skillTitle: 'Skill management', skillDesc: 'Manage local skills: upload, enable, open folders, and delete',
    save: 'Save settings', saving: 'Saving...', saved: 'Settings saved.', saveFailed: 'Save failed. Please try again.'
  },
  general: {
    title: 'Basic settings', subtitle: 'Configure startup behavior and display modes', language: 'Interface language',
    simplifiedChinese: '简体中文', english: 'English',
    showPanel: 'Show the AI panel at startup', proofread: 'Proofreading display mode', proofreadMode: 'Proofreading display mode',
    redBlue: 'Red/blue mode', redblue: 'Red/blue mode', redBlueDesc: 'Mark deletions in light blue and additions in light red',
    redblueDesc: 'Mark deletions in light blue and additions in light red',
    revision: 'Track changes mode', revisionDesc: 'Use Word track changes to mark edits', proxy: 'Network proxy',
    proxyTitle: 'Network proxy', proxyDesc: 'Configure the proxy server for HTTP/HTTPS requests',
    proxySubtitle: 'Configure the proxy server for HTTP/HTTPS requests', enableProxy: 'Enable proxy',
    host: 'Proxy address (IP)', proxyHost: 'Proxy address (IP)', port: 'Port',
    proxyHint: 'HTTP and HTTPS requests use this proxy. HTTP proxies are supported; SOCKS proxies are not.'
  },
  skill: {
    title: 'Skill management', subtitle: 'Upload a ZIP containing SKILL.md and install it in the local skills directory',
    upload: 'Upload skill ZIP', uploading: 'Uploading...', tip: 'ZIP only; the archive must contain SKILL.md',
    zipHint: 'ZIP only; the archive must contain SKILL.md',
    loading: 'Loading skills...', empty: 'No skills yet. Use “Upload skill ZIP” to add one.', unnamed: 'Unnamed skill',
    toggle: 'Enable or disable skill', openFolder: 'Open skill folder', delete: 'Delete', loadFailed: 'Failed to load skills',
    zipOnly: 'Only ZIP archives are supported', uploadZipOnly: 'Only ZIP archives are supported', uploadSuccess: 'Skill uploaded', uploadFailed: 'Failed to upload skill',
    updateFailed: 'Failed to update skill status', deleteConfirm: 'Delete skill: {name}?', deleteSuccess: 'Skill deleted',
    deleteFailed: 'Failed to delete skill', openFailed: 'Failed to open skill folder',
    builtinDeleteDisabled: 'Built-in skills cannot be deleted'
  },
  model: {
    title: 'AI provider configuration', subtitle: 'Manage AI providers and models', configured: 'Configured providers',
    availableCount: '{count} available models', addProvider: 'Add provider', newProvider: 'New provider', modelCount: '{count} models',
    name: 'Name', namePlaceholder: 'For example: openai', apiType: 'API type', openaiCompatible: 'OpenAI compatible',
    fetchModels: 'Fetch model list', fetch: 'Fetch model list', fetching: 'Fetching...', collapseAvailable: 'Hide available models', collapse: 'Hide available models',
    availableModels: 'Available models ({count})', clickToAdd: 'Click + to add a model', addHint: 'Click + to add a model', addModel: 'Add model', added: 'Added',
    addedModels: 'Added models ({count})', remove: 'Remove', noModels: 'No models. Fetch the model list first.',
    empty: 'No providers configured. Use “Add provider” to begin.', deleteConfirm: 'Delete this provider?',
    credentialsRequired: 'Enter the API key and base URL first', fetchFailed: 'Failed to fetch models: {error}', checkConfig: 'Check the configuration'
  },
  mcp: {
    title: 'MCP server configuration', subtitle: 'Click a server card to expand and edit it', add: 'Add server', addServer: 'Add server',
    empty: 'No MCP servers yet. Use “Add server” to begin.', unnamed: 'Unnamed server', toggle: 'Enable or disable MCP server',
    name: 'Server name', serverName: 'Server name', namePlaceholder: 'For example: local-filesystem', config: 'Server configuration (JSON)',
    configPlaceholder: 'Enter the MCP server JSON configuration', testing: 'Testing...', test: 'Test connection', testConnection: 'Test connection',
    objectRequired: 'The configuration must be a JSON object, not an array or primitive', serversEmpty: 'mcpServers cannot be empty',
    serverObjectRequired: 'Each mcpServers configuration must be an object', jsonError: 'Invalid JSON: {error}',
    nameRequired: 'Enter the server name first', configRequired: 'Enter the server configuration first', fixJson: 'Fix the JSON configuration first',
    success: 'Connected', failed: 'Connection failed'
  },
  personalization: {
    title: 'Custom instructions', instructions: 'Custom instructions', subtitle: 'Set a global AI prompt used in every conversation',
    instructionsDesc: 'Set a global AI prompt used in every conversation', globalPrompt: 'Global prompt',
    promptHint: 'Applied to every conversation to help the assistant understand your needs',
    promptPlaceholder: 'For example: You are a professional writing assistant. Respond concisely and professionally...',
    chars: '{count} characters', quickTemplates: 'Quick templates', temperature: 'LLM temperature', temperatureDesc: 'Adjust AI creativity and randomness',
    precise: 'Precise (0-0.33)', preciseDesc: 'More deterministic and consistent; suited to factual tasks', balanced: 'Balanced (0.33-0.67)',
    balancedDesc: 'Balances accuracy and creativity for most tasks', creative: 'Creative (0.67-1)', creativeDesc: 'More varied and imaginative; suited to brainstorming',
    clearConfirm: 'Clear the custom instructions?', overwriteConfirm: 'Applying a template will replace the current instructions. Continue?',
    templates: {
      academicName: 'Academic writing', academicDesc: 'Formal and rigorous academic style', academicPrompt: 'You are a professional academic writing assistant. Use formal, rigorous language with clear logic and accurate terminology.',
      creativeName: 'Creative writing', creativeDesc: 'Imaginative creative style', creativePrompt: 'You are a creative writing assistant. Use vivid language and encourage original ideas and perspectives.',
      businessName: 'Business documents', businessDesc: 'Concise, professional business style', businessPrompt: 'You are a professional business writing assistant. Produce clear, concise documents, reports, and emails with prominent key points.',
      casualName: 'Everyday communication', casualDesc: 'Relaxed and friendly style', casualPrompt: 'You are a friendly, approachable writing assistant. Use natural, relaxed, and readable language.'
    }
  },
  data: {
    title: 'Data management', subtitle: 'Manage application data and storage', cache: 'Clear cache', clearCache: 'Clear cache',
    cacheDesc: 'Remove cached files from project/temp and project/uploads to free disk space', clearCacheDesc: 'Remove cached files from project/temp and project/uploads to free disk space',
    cacheLocation: 'Cache location', cacheSize: 'Cache size', scan: 'Scan cache', scanning: 'Scanning...', clear: 'Clear cache', clearing: 'Clearing...',
    memory: 'Long-term memory', memoryDesc: 'Manage persistent AI memory, ordered from oldest to newest', enableMemory: 'Enable long-term memory',
    memoryPlaceholder: 'Long-term AI memory appears here. You can edit and save it...', memoryHint: 'Memories are chronological; the newest entries are at the bottom.',
    reload: 'Reload', saveMemory: 'Save memory', deleteAll: 'Delete all data', deleteAllDesc: 'Remove all chat history and cached application data',
    irreversible: 'Warning: this action cannot be undone', warning: 'Warning: this action cannot be undone', deleteIncludes: 'Deleting all data removes:', chats: 'All chat history',
    cachedDocs: 'Cached document data', sessionState: 'Session state', confirmTitle: 'Delete all data?',
    confirmDesc: 'This permanently deletes all data, including chats, cache, and settings. It cannot be undone.',
    confirmBody: 'This permanently deletes all data, including chats, cache, and settings. It cannot be undone.', typeDelete: 'Type DELETE to confirm:',
    typeDeletePlaceholder: 'Type DELETE', deletePlaceholder: 'Type DELETE', confirmDelete: 'Delete permanently', deleting: 'Deleting...', calculating: 'Calculating...', noCache: 'No cache',
    cacheSummary: '{size} ({count} files)', clearConfirm: 'Clear all files in the cache directories?', cleared: 'Cleared {count} cached files',
    clearFailed: 'Failed to clear cache: {error}', deleted: 'All data was deleted.', deleteFailed: 'Delete failed: {error}',
    memoryLoadFailed: 'Failed to load long-term memory: {error}', memorySaved: 'Long-term memory saved.', memorySaveFailed: 'Failed to save long-term memory: {error}',
    memoryToggled: 'Long-term memory {state}', memoryEnabled: 'enabled', memoryDisabled: 'disabled',
    toggleFailed: 'Failed to save the memory setting: {error}'
  },
  session: {
    title: 'Chat history', newChat: 'New chat', empty: 'No chat history', newConversation: 'New conversation', noMessages: 'No messages',
    rename: 'Rename', renameTitle: 'Rename conversation', renamePlaceholder: 'Enter a new name', deleteTitle: 'Delete conversation',
    deleteBody: 'Delete this conversation? This action cannot be undone.'
  },
  chat: {
    attachment: 'Attachment', removeFile: 'Remove file', chars: '{count} chars', clearSelection: 'Clear selection',
    allowThinking: 'Thinking on', disableThinking: 'Thinking off', thinkingToggle: 'Enable or disable deep thinking',
    addFile: 'Add files', addSelection: 'Add selection', send: 'Send', stop: 'Stop',
    agentPlaceholder: 'Describe what to build next', askPlaceholder: 'Enter a question', planPlaceholder: 'Describe the goal or question to investigate',
    chooseModel: 'Select a model', deleteParagraphs: 'Tracked deletion of {count} paragraphs', aiOperation: 'AI revisions: {actions}',
    context: 'Context: {current}k / {max}k tokens ({percentage}%)', unnamedFile: 'Unnamed file',
    unsupportedFiles: 'Unsupported files: {files}. Supported formats: png, jpg, jpeg, pdf, docx, txt, md.',
    paragraphRange: 'Paragraphs {start} - {end}', showHistory: 'Show chat history', whatCanIDo: 'What can I do?',
    documentation: 'Documentation', selectionRef: 'Referenced selections ({count})', fileRef: 'Referenced files ({count})',
    unknownFile: 'Unknown file', preparing: 'AI is preparing', thinking: 'Deep thinking', thinkingDone: 'Deep thinking (complete)',
    collapseMcp: 'Collapse MCP details', expandMcp: 'Expand MCP details', callMcp: 'Calling MCP tool: {name}',
    arguments: 'Arguments:', noArguments: 'No arguments', toolOutput: 'Tool output:', noOutput: '(No output)',
    outputDocument: 'Insert into document', copyImage: 'Copy image', saveImage: 'Save image', selection: 'Selection',
    copyImageFailed: 'Copy failed. Try saving the image from its context menu.',
    mcpWaiting: 'Waiting for tool output...', unknownArguments: 'Arguments unavailable', imageTableSelection: '[Image and table selection]',
    imageSelection: '[Image selection]', tableSelection: '[Table selection]', networkTimeout: 'The network connection timed out and was closed.',
    networkError: 'Network error: {error}. Make sure the backend service is running on localhost:3880.',
    networkInterruptedReconnecting: 'The connection was interrupted and this request failed. Reconnecting automatically; please resend shortly.',
    readingDocumentById: 'Reading document (paragraph IDs {start} - {end})',
    readingDocument: 'Reading document (paragraphs {start} - {end})', searchingDocument: 'Searching document...',
    generatingDocument: 'Generating document', documentInsertFailed: 'Document insertion failed. Check the target position and document permissions.',
    deletePreview: 'AI created tracked deletions (paraIDs: {ids})', generatedPending: 'AI generated {summary}; awaiting confirmation',
    wpsUnavailable: 'The WPS API is unavailable', openDocumentFirst: 'Open a Word document first', messageMissing: 'Message not found',
    undoFailed: 'Undo failed: {error}', selectionUnavailable: 'Could not read the selection. Select content in WPS Writer first.',
    selectionRangeUnavailable: 'Could not determine the selection range', selectContentFirst: 'Select text, an image, or a table in the document first.',
    selectionFailed: 'Could not process the selected content: {error}', insertFailed: 'Insertion failed. Make sure a Word document is open.', unnamedDocument: 'Untitled document',
    searchComplete: 'Search complete', documentReadComplete: 'Document read complete', prepareDelete: 'Applying tracked deletions to paragraph IDs ({ids})',
    deleteComplete: 'Deletion complete', insertBreakSuccess: 'Document break inserted', insertBreakFailed: 'Failed to insert document break: {error}', createDocumentPending: 'Creating a new blank DOCX document', createDocumentSuccess: 'A new blank DOCX document was created and opened', createDocumentFailed: 'Failed to create a new DOCX document: {error}', documentGenerated: 'Document generated', errorLabel: 'Error: {error}',
    paragraphCount: '{count} paragraphs', tableCount: '{count} tables', pendingAddition: 'Pending addition',
    input: {
      attachment: 'Attachment', removeFile: 'Remove file', paragraphRange: 'Paragraphs {start} - {end}', clearSelection: 'Clear selection',
      confirm: 'Confirm', cancel: 'Cancel', modelsLoading: 'Loading...', thinkingAria: 'Enable or disable deep thinking',
      thinkingOn: 'Thinking on', thinkingOff: 'Thinking off', addFile: 'Add files', addSelection: 'Add selection', send: 'Send', stop: 'Stop',
      agentPlaceholder: 'Describe what to build next', askPlaceholder: 'Enter a question', planPlaceholder: 'Describe the goal or question to investigate',
      chooseModel: 'Select a model', deleteParagraphs: 'Tracked deletion of {count} paragraphs', aiOperation: 'AI revisions: {actions}',
      context: 'Context: {current}k / {max}k tokens ({percentage}%)', unnamedFile: 'Unnamed file',
      unsupportedFiles: 'Unsupported files: {files}. Supported formats: png, jpg, pdf, docx, txt, md.'
    },
    messages: {
      showHistory: 'Show chat history', empty: 'What can I do?', docs: 'Documentation', selections: 'Referenced selections ({count})',
      files: 'Referenced files ({count})', unknownFile: 'Unknown file', preparing: 'AI is preparing', thinking: 'Deep thinking',
      thinkingDone: 'Deep thinking (complete)', collapseMcp: 'Collapse MCP details', expandMcp: 'Expand MCP details',
      mcpCall: 'Calling MCP tool: {name}', parameters: 'Parameters:', noParameters: 'No parameters', output: 'Tool output:', noOutput: '(No output)',
      copy: 'Copy', insert: 'Insert into Word', retry: 'Retry', undo: 'Undo'
    },
    session: {
      newChat: 'New chat', title: 'Chat history', empty: 'No chat history', rename: 'Rename', delete: 'Delete',
      renameTitle: 'Rename conversation', renamePlaceholder: 'Enter a conversation name', deleteTitle: 'Delete conversation',
      deleteConfirm: 'Delete this conversation? This action cannot be undone.'
    }
  },
  about: {
    name: 'WenCe AI Assistant', product: 'WenCe AI Assistant', version: 'Version', pluginType: 'Add-in type', wpsPlugin: 'WPS Writer add-in', wordPlugin: 'Microsoft Word add-in',
    developer: 'Developer', developerName: 'Riyue Xingchen', links: 'Links', repository: 'GitHub repository', website: 'Project website',
    docs: 'Documentation', issues: 'Report an issue', sponsor: 'Sponsor the author', github: 'GitHub repository', unknownVersion: 'Unknown version'
  },
  debug: {
    title: 'Debug panel', hint: 'Press F12 to open developer tools', parse: 'Parse document content', parseSelection: 'Parse selection',
    showDocuments: 'Show open file names', openDocuments: 'Open documents ({count})', deleteParagraphs: 'Delete paragraphs by index',
    deletePlaceholder: 'Enter start and end paragraph indices (0-based), for example: 3, 7', clear: 'Clear', jsonToDoc: 'JSON to document',
    jsonPlaceholder: 'Paste JSON here...', apply: 'Apply to document', export: 'Export', copy: 'Copy to clipboard',
    download: 'Download JSON', deleteAction: 'Delete paragraphs', result: 'Parsed result:', paragraphs: 'Paragraphs: {count}', tables: 'Tables: {count}', images: 'Images: {count}', chars: 'Characters: {count}'
  }
};
