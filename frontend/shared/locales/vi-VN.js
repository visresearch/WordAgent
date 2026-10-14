export default {
  common: {
    add: 'Thêm', cancel: 'Hủy', clear: 'Xóa', close: 'Đóng', confirm: 'Xác nhận', delete: 'Xóa',
    disabled: 'Vô hiệu', edit: 'Chỉnh sửa', enabled: 'Kích hoạt', loading: 'Đang tải...', none: 'Không',
    refresh: 'Làm mới', remove: 'Xóa', retry: 'Thử lại', copy: 'Sao chép', save: 'Lưu', saving: 'Đang lưu...',
    unknown: 'Không xác định', unknownError: 'Lỗi không xác định', pleaseRetry: 'Vui lòng thử lại sau', testing: 'Đang kiểm tra...'
  },
  language: {
    label: 'Ngôn ngữ giao diện', chinese: '简体中文', english: 'English', indonesian: 'Bahasa Indonesia', japanese: '日本語', korean: '한국어', vietnamese: 'Tiếng Việt'
  },
  windows: { assistant: '文策AI', settings: 'Cài đặt', about: 'About', debug: 'Bảng điều khiển gỡ lỗi' },
  nav: { chat: 'Trò chuyện AI', history: 'Lịch sử trò chuyện', settings: 'Cài đặt', about: 'About', debug: 'Gỡ lỗi' },
  settings: {
    tabs: { general: 'Chung', model: 'Mô hình', personalization: 'Cá nhân hóa', mcp: 'MCP', skill: 'Kỹ năng', data: 'Dữ liệu' },
    generalTitle: 'Cài đặt chung', generalDesc: 'Cấu hình hành vi cơ bản của ứng dụng',
    modelTitle: 'Cài đặt mô hình', modelDesc: 'Quản lý nhà cung cấp và mô hình AI',
    personalizationTitle: 'Cá nhân hóa', personalizationDesc: 'Tùy chỉnh hành vi trợ lý và các tham số phản hồi',
    mcpTitle: 'MCP servers', mcpDesc: 'Quản lý tên máy chủ MCP và cấu hình JSON, kèm kiểm tra kết nối',
    skillTitle: 'Quản lý kỹ năng', skillDesc: 'Quản lý kỹ năng cục bộ: tải lên, bật, mở thư mục, và xóa',
    save: 'Lưu cài đặt', saving: 'Đang lưu...', saved: 'Cài đặt đã được lưu.', saveFailed: 'Lưu thất bại. Vui lòng thử lại.'
  },
  general: {
    title: 'Cài đặt cơ bản', subtitle: 'Cấu hình hành vi khởi động và chế độ hiển thị', language: 'Ngôn ngữ giao diện',
    simplifiedChinese: '简体中文', english: 'English', indonesian: 'Bahasa Indonesia', japanese: '日本語', korean: '한국어', vietnamese: 'Tiếng Việt',
    showPanel: 'Hiển thị bảng AI khi khởi động', proofread: 'Chế độ hiển thị proofreading', proofreadMode: 'Chế độ hiển thị proofreading',
    redBlue: 'Chế độ đỏ/xanh', redblue: 'Chế độ đỏ/xanh', redBlueDesc: 'Đánh dấu xóa bằng xanh nhạt và thêm bằng đỏ nhạt',
    redblueDesc: 'Đánh dấu xóa bằng xanh nhạt và thêm bằng đỏ nhạt',
    revision: 'Chế độ theo dõi thay đổi', revisionDesc: 'Sử dụng track changes của Word để đánh dấu chỉnh sửa', proxy: 'Proxy mạng',
    proxyTitle: 'Proxy mạng', proxyDesc: 'Cấu hình máy chủ proxy cho các yêu cầu HTTP/HTTPS',
    proxySubtitle: 'Cấu hình máy chủ proxy cho các yêu cầu HTTP/HTTPS', enableProxy: 'Bật proxy',
    host: 'Địa chỉ proxy (IP)', proxyHost: 'Địa chỉ proxy (IP)', port: 'Cổng',
    proxyHint: 'Các yêu cầu HTTP và HTTPS sử dụng proxy này. Hỗ trợ proxy HTTP; proxy SOCKS không được hỗ trợ.'
  },
  skill: {
    title: 'Quản lý kỹ năng', subtitle: 'Tải lên ZIP chứa SKILL.md và cài đặt vào thư mục kỹ năng cục bộ',
    upload: 'Tải lên ZIP kỹ năng', uploading: 'Đang tải lên...', tip: 'Chỉ hỗ trợ ZIP; lưu trữ phải chứa SKILL.md',
    zipHint: 'Chỉ hỗ trợ ZIP; lưu trữ phải chứa SKILL.md',
    loading: 'Đang tải danh sách kỹ năng...', empty: 'Chưa có kỹ năng nào. Sử dụng "Tải lên ZIP kỹ năng" để thêm.', unnamed: 'Kỹ năng không tên',
    toggle: 'Bật hoặc tắt kỹ năng', openFolder: 'Mở thư mục kỹ năng', delete: 'Xóa', loadFailed: 'Tải kỹ năng thất bại',
    zipOnly: 'Chỉ hỗ trợ lưu trữ ZIP', uploadZipOnly: 'Chỉ hỗ trợ lưu trữ ZIP', uploadSuccess: 'Kỹ năng đã được tải lên', uploadFailed: 'Tải lên kỹ năng thất bại',
    updateFailed: 'Cập nhật trạng thái kỹ năng thất bại', deleteConfirm: 'Xóa kỹ năng: {name}?', deleteSuccess: 'Kỹ năng đã bị xóa',
    deleteFailed: 'Xóa kỹ năng thất bại', openFailed: 'Mở thư mục kỹ năng thất bại',
    builtinDeleteDisabled: 'Kỹ năng tích hợp không thể xóa'
  },
  model: {
    title: 'Cấu hình nhà cung cấp AI', subtitle: 'Quản lý nhà cung cấp và mô hình AI', configured: 'Nhà cung cấp đã cấu hình',
    availableCount: '{count} mô hình có sẵn', addProvider: 'Thêm nhà cung cấp', newProvider: 'Nhà cung cấp mới', modelCount: '{count} mô hình',
    name: 'Tên', namePlaceholder: 'Ví dụ: openai', apiType: 'Loại API', openaiCompatible: 'Tương thích OpenAI',
    fetchModels: 'Lấy danh sách mô hình', fetch: 'Lấy danh sách mô hình', fetching: 'Đang lấy...', collapseAvailable: 'Ẩn các mô hình có sẵn', collapse: 'Ẩn các mô hình có sẵn',
    availableModels: 'Mô hình có sẵn ({count})', clickToAdd: 'Nhấn + để thêm mô hình', addHint: 'Nhấn + để thêm mô hình', addModel: 'Thêm mô hình', added: 'Đã thêm',
    addedModels: 'Mô hình đã thêm ({count})', remove: 'Xóa', noModels: 'Không có mô hình. Vui lòng lấy danh sách mô hình trước.',
    empty: 'Chưa có nhà cung cấp nào được cấu hình. Sử dụng "Thêm nhà cung cấp" để bắt đầu.', deleteConfirm: 'Xóa nhà cung cấp này?',
    credentialsRequired: 'Nhập trước API key và base URL', fetchFailed: 'Lấy mô hình thất bại: {error}', checkConfig: 'Kiểm tra cấu hình'
  },
  mcp: {
    title: 'Cấu hình máy chủ MCP', subtitle: 'Nhấn vào thẻ máy chủ để mở rộng và chỉnh sửa', add: 'Thêm máy chủ', addServer: 'Thêm máy chủ',
    empty: 'Chưa có máy chủ MCP nào. Sử dụng "Thêm máy chủ" để bắt đầu.', unnamed: 'Máy chủ không tên', toggle: 'Bật hoặc tắt máy chủ MCP',
    name: 'Tên máy chủ', serverName: 'Tên máy chủ', namePlaceholder: 'Ví dụ: local-filesystem', config: 'Cấu hình máy chủ (JSON)',
    configPlaceholder: 'Nhập cấu hình JSON của máy chủ MCP', testing: 'Đang kiểm tra...', test: 'Kiểm tra kết nối', testConnection: 'Kiểm tra kết nối',
    objectRequired: 'Cấu hình phải là một đối tượng JSON, không phải mảng hoặc giá trị nguyên thủy', serversEmpty: 'mcpServers không được để trống',
    serverObjectRequired: 'Mỗi cấu hình mcpServers phải là một đối tượng', jsonError: 'JSON không hợp lệ: {error}',
    nameRequired: 'Nhập tên máy chủ trước', configRequired: 'Nhập cấu hình máy chủ trước', fixJson: 'Sửa cấu hình JSON trước',
    success: 'Kết nối thành công', failed: 'Kết nối thất bại'
  },
  personalization: {
    title: 'Hướng dẫn tùy chỉnh', instructions: 'Hướng dẫn tùy chỉnh', subtitle: 'Đặt một lời nhắn AI toàn cục được sử dụng trong mọi cuộc trò chuyện',
    instructionsDesc: 'Đặt một lời nhắn AI toàn cục được sử dụng trong mọi cuộc trò chuyện', globalPrompt: 'Lời nhắn toàn cục',
    promptHint: 'Áp dụng cho mọi cuộc trò chuyện để giúp trợ lý hiểu nhu cầu của bạn',
    promptPlaceholder: 'Ví dụ: Bạn là một trợ lý viết chuyên nghiệp. Trả lời ngắn gọn và chuyên nghiệp...',
    chars: '{count} ký tự', quickTemplates: 'Mẫu nhanh', temperature: 'Nhiệt độ LLM', temperatureDesc: 'Điều chỉnh sáng tạo và ngẫu nhiên của AI',
    precise: 'Chính xác (0-0.33)', preciseDesc: 'More deterministic và nhất quán; phù hợp cho các tác vụ thực tế', balanced: 'Cân bằng (0.33-0.67)',
    balancedDesc: 'Cân bằng độ chính xác và sáng tạo cho hầu hết các tác vụ', creative: 'Sáng tạo (0.67-1)', creativeDesc: 'More varied và đổi mới; phù hợp cho brainstorming',
    clearConfirm: 'Xóa các hướng dẫn tùy chỉnh?', overwriteConfirm: 'Áp dụng một mẫu sẽ thay thế các hướng dẫn hiện tại. Tiếp tục?',
    templates: {
      academicName: 'Viết học thuật', academicDesc: 'Phong cách học thuật chính xác và nghiêm túc', academicPrompt: 'Bạn là một trợ lý viết học thuật chuyên nghiệp. Sử dụng ngôn ngữ chính xác, nghiêm túc với logic rõ ràng và thuật ngữ chính xác.',
      creativeName: 'Viết sáng tạo', creativeDesc: 'Phong cách sáng tạo đổi mới', creativePrompt: 'Bạn là một trợ lý viết sáng tạo. Sử dụng ngôn ngữ sinh động và khuyến khích ý tưởng gốc và góc nhìn mới.',
      businessName: 'Tài liệu kinh doanh', businessDesc: 'Phong cách kinh doanh ngắn gọn, chuyên nghiệp', businessPrompt: 'Bạn là một trợ lý viết kinh doanh chuyên nghiệp. Tạo ra tài liệu, báo cáo, và email ngắn gọn, rõ ràng với các điểm chính nổi bật.',
      casualName: 'Giao tiếp hàng ngày', casualDesc: 'Phong cách thư giãn, thân thiện', casualPrompt: 'Bạn là một trợ lý viết thân thiện, dễ tiếp cận. Sử dụng ngôn ngữ tự nhiên, thư giãn và dễ đọc.'
    }
  },
  data: {
    title: 'Quản lý dữ liệu', subtitle: 'Quản lý dữ liệu và lưu trữ ứng dụng', cache: 'Xóa bộ nhớ đệm', clearCache: 'Xóa bộ nhớ đệm',
    cacheDesc: 'Xóa các tệp tin được lưu trữ trong project/temp và project/uploads để giải phóng không gian đĩa', clearCacheDesc: 'Xóa các tệp tin được lưu trữ trong project/temp và project/uploads để giải phóng không gian đĩa',
    cacheLocation: 'Vị trí bộ nhớ đệm', cacheSize: 'Kích thước bộ nhớ đệm', scan: 'Quét', scanning: 'Đang quét...', clear: 'Xóa bộ nhớ đệm', clearing: 'Đang xóa...',
    memory: 'Nhớ dài hạn', memoryDesc: 'Quản lý nhớ AI dài hạn, sắp xếp theo thứ tự từ cũ đến mới', enableMemory: 'Bật nhớ dài hạn',
    memoryPlaceholder: 'Nhớ dài hạn AI của bạn sẽ xuất hiện ở đây. Bạn có thể chỉnh sửa và lưu...', memoryHint: 'Nhớ được sắp xếp theo thời gian; các mục mới nhất ở đầu cuối.',
    reload: 'Tải lại', saveMemory: 'Lưu nhớ', deleteAll: 'Xóa tất cả dữ liệu', deleteAllDesc: 'Xóa lịch sử trò chuyện và dữ liệu ứng dụng được lưu trữ',
    irreversible: 'Cảnh báo: hành động này không thể hoàn ngược', warning: 'Cảnh báo: hành động này không thể hoàn ngược', deleteIncludes: 'Xóa tất cả dữ liệu sẽ xóa:', chats: 'Lịch sử trò chuyện',
    cachedDocs: 'Dữ liệu tài liệu được lưu trữ', sessionState: 'Trạng thái phiên', confirmTitle: 'Xóa tất cả dữ liệu?',
    confirmDesc: 'Xóa vĩnh viễn tất cả dữ liệu, bao gồm đoạn chat, bộ nhớ đệm và cài đặt. Không thể hoàn ngược.',
    confirmBody: 'Xóa vĩnh viễn tất cả dữ liệu, bao gồm đoạn chat, bộ nhớ đệm và cài đặt. Không thể hoàn ngược.', typeDelete: 'Nhập DELETE để xác nhận:',
    typeDeletePlaceholder: 'Nhập DELETE', deletePlaceholder: 'Nhập DELETE', confirmDelete: 'Xóa vĩnh viễn', deleting: 'Đang xóa...', calculating: 'Đang tính toán...', noCache: 'Không có bộ nhớ đệm',
    cacheSummary: '{size} ({count} tệp)', clearConfirm: 'Xóa tất cả tệp tin trong thư mục bộ nhớ đệm?', cleared: 'Đã xóa {count} tệp tin bộ nhớ đệm',
    clearFailed: 'Xóa bộ nhớ đệm thất bại: {error}', deleted: 'Tất cả dữ liệu đã được xóa.', deleteFailed: 'Xóa thất bại: {error}',
    memoryLoadFailed: 'Tải nhớ dài hạn thất bại: {error}', memorySaved: 'Nhớ dài hạn đã được lưu.', memorySaveFailed: 'Lưu nhớ dài hạn thất bại: {error}',
    memoryToggled: 'Nhớ dài hạn {state}', memoryEnabled: 'được bật', memoryDisabled: 'được tắt',
    toggleFailed: 'Lưu thiết lập nhớ thất bại: {error}'
  },
  session: {
    title: 'Lịch sử trò chuyện', newChat: 'Trò chuyện mới', empty: 'Không có lịch sử trò chuyện', newConversation: 'Cuộc trò chuyện mới', noMessages: 'Không có thông điệp',
    rename: 'Đổi tên', renameTitle: 'Đổi tên cuộc trò chuyện', renamePlaceholder: 'Nhập tên mới', deleteTitle: 'Xóa cuộc trò chuyện',
    deleteBody: 'Xóa cuộc trò chuyện này? Hành động này không thể hoàn ngược.'
  },
  chat: {
    attachment: 'Tệp tin đính kèm', removeFile: 'Xóa tệp tin', chars: '{count} ký tự', clearSelection: 'Xóa chọn',
    allowThinking: 'Suy nghĩ bật', disableThinking: 'Suy nghĩ tắt', thinkingToggle: 'Bật hoặc tắt suy nghĩ sâu',
    addFile: 'Thêm tệp tin', addSelection: 'Thêm chọn', send: 'Gửi', stop: 'Dừng',
    agentPlaceholder: 'Mô tả những gì cần xây dựng tiếp theo', askPlaceholder: 'Nhập câu hỏi',
    chooseModel: 'Chọn mô hình', deleteParagraphs: 'đã xóa {count} đoạn', aiOperation: 'Chỉnh sửa AI: {actions} (đang chờ xác nhận)', revisionCount: '{count} thay đổi',
    acceptRevision: 'Chấp nhận', rejectRevision: 'Từ chối',
    context: 'Ngữ cảnh: {current}k / {max}k token ({percentage}%)', unnamedFile: 'Tệp tin không tên',
    unsupportedFiles: 'Tệp tin không được hỗ trợ: {files}. Định dạng hỗ trợ: png, jpg, jpeg, pdf, docx, txt, md.',
    paragraphRange: 'Đoạn {start} - {end}', showHistory: 'Hiển thị lịch sử trò chuyện', whatCanIDo: 'Tôi có thể làm gì?',
    documentation: 'Tài liệu', selectionRef: 'Lựa chọn được tham chiếu ({count})', fileRef: 'Tệp tin được tham chiếu ({count})',
    unknownFile: 'Tệp tin không xác định', preparing: 'AI đang chuẩn bị', thinking: 'Suy nghĩ sâu', thinkingDone: 'Suy nghĩ sâu (hoàn thành)',
    contextCompactionStarted: '🗜️ Đang tự động gọn lại ngữ cảnh', contextCompactionCompleted: '✅ Gọn lại ngữ cảnh hoàn thành',
    collapseMcp: 'Thu gọp chi tiết MCP', expandMcp: 'Mở rộng chi tiết MCP', callMcp: 'Gọi công cụ MCP: {name}',
    arguments: 'Đối số:', noArguments: 'Không có đối số', toolOutput: 'Kết quả công cụ:', noOutput: '(Không có kết quả)',
    outputDocument: 'Chèn vào tài liệu', copyImage: 'Sao chép hình ảnh', saveImage: 'Lưu hình ảnh', selection: 'Chọn',
    copyImageFailed: 'Sao chép thất bại. Vui lòng lưu hình ảnh từ menu ngữ cảnh.',
    mcpWaiting: 'Đang chờ kết quả công cụ...', unknownArguments: 'Đối số không khả dụng', imageTableSelection: '[Chọn hình ảnh và bảng]',
    imageSelection: '[Chọn hình ảnh]', tableSelection: '[Chọn bảng]', networkTimeout: 'Kết nối mạng đã hết thời gian và bị đóng.',
    networkError: 'Lỗi mạng: {error}. Vui lòng đảm bảo dịch vụ backend đang chạy trên localhost:3880.',
    networkInterruptedReconnecting: 'Kết nối đã bị ngắt và yêu cầu này thất bại. Đang kết nối lại tự động; vui lòng gửi lại sớm.',
    readingDocumentById: 'Đang đọc tài liệu (ID đoạn {start} - {end})',
    readingDocument: 'Đang đọc tài liệu (đoạn {start} - {end})', searchingDocument: 'Đang tìm kiếm tài liệu...',
    generatingDocument: 'Đang tạo tài liệu', documentInsertFailed: 'Chèn tài liệu thất bại. Kiểm tra vị trí đối tượng và quyền truy cập tài liệu.',
    deletePreview: 'Xóa {ids}', generatedPending: 'đã tạo {summary}',
    wpsUnavailable: 'API WPS không khả dụng', openDocumentFirst: 'Mở tài liệu Word trước', messageMissing: 'Thông điệp không được tìm thấy',
    undoFailed: 'Hoàn thao thất bại: {error}', selectionUnavailable: 'Không thể đọc phần được chọn. Vui lòng chọn nội dung trong WPS Writer đầu tiên.',
    selectionRangeUnavailable: 'Không thể xác định phạm vi chọn', selectContentFirst: 'Vui lòng chọn văn bản, hình ảnh, hoặc bảng trong tài liệu đầu tiên.',
    selectionFailed: 'Xử lý nội dung được chọn thất bại: {error}', insertFailed: 'Chèn thất bại. Vui lòng đảm bảo tài liệu Word đang mở.', unnamedDocument: 'Tài liệu không tên',
    searchComplete: 'Tìm kiếm hoàn thành', documentReadComplete: 'Đọc tài liệu hoàn thành', prepareDelete: 'Áp dụng xóa theo dõi cho ID đoạn ({ids})',
    deleteComplete: 'Xóa hoàn thành', insertBreakSuccess: 'Đã chèn phân đoạn tài liệu', insertBreakFailed: 'Chèn phân đoạn tài liệu thất bại: {error}', createDocumentPending: 'Đang tạo tài liệu DOCX trống mới', createDocumentSuccess: 'Đã tạo và mở tài liệu DOCX trống mới', createDocumentFailed: 'Tạo tài liệu DOCX mới thất bại: {error}', documentGenerated: 'Tài liệu đã được tạo', errorLabel: 'Lỗi: {error}',
    paragraphCount: '{count} đoạn', tableCount: '{count} bảng', summarySeparator: ', ', actionSeparator: ', ', pendingAddition: 'Thêm đang chờ',
    input: {
      attachment: 'Tệp tin đính kèm', removeFile: 'Xóa tệp tin', paragraphRange: 'Đoạn {start} - {end}', clearSelection: 'Xóa chọn',
      confirm: 'Xác nhận', cancel: 'Hủy', modelsLoading: 'Đang tải...', thinkingAria: 'Bật hoặc tắt suy nghĩ sâu',
      thinkingOn: 'Suy nghĩ bật', thinkingOff: 'Suy nghĩ tắt', addFile: 'Thêm tệp tin', addSelection: 'Thêm chọn', send: 'Gửi', stop: 'Dừng',
      agentPlaceholder: 'Mô tả những gì cần xây dựng tiếp theo', askPlaceholder: 'Nhập câu hỏi',
      chooseModel: 'Chọn mô hình', deleteParagraphs: 'đã xóa {count} đoạn', aiOperation: 'Chỉnh sửa AI: {actions} (đang chờ xác nhận)',
      context: 'Ngữ cảnh: {current}k / {max}k token ({percentage}%)', unnamedFile: 'Tệp tin không tên',
      unsupportedFiles: 'Tệp tin không được hỗ trợ: {files}. Định dạng hỗ trợ: png, jpg, pdf, docx, txt, md.'
    },
    messages: {
      showHistory: 'Hiển thị lịch sử trò chuyện', empty: 'Tôi có thể làm gì?', docs: 'Tài liệu', selections: 'Lựa chọn được tham chiếu ({count})',
      files: 'Tệp tin được tham chiếu ({count})', unknownFile: 'Tệp tin không xác định', preparing: 'AI đang chuẩn bị', thinking: 'Suy nghĩ sâu',
      thinkingDone: 'Suy nghĩ sâu (hoàn thành)', collapseMcp: 'Thu gọp chi tiết MCP', expandMcp: 'Mở rộng chi tiết MCP',
      mcpCall: 'Gọi công cụ MCP: {name}', parameters: 'Đối số:', noParameters: 'Không có đối số', output: 'Kết quả công cụ:', noOutput: '(Không có kết quả)',
      copy: 'Sao chép', insert: 'Chèn vào Word', retry: 'Thử lại', undo: 'Hoàn thao'
    },
    session: {
      newChat: 'Trò chuyện mới', title: 'Lịch sử trò chuyện', empty: 'Không có lịch sử trò chuyện', rename: 'Đổi tên', delete: 'Xóa',
      renameTitle: 'Đổi tên cuộc trò chuyện', renamePlaceholder: 'Nhập tên cuộc trò chuyện', deleteTitle: 'Xóa cuộc trò chuyện',
      deleteConfirm: 'Xóa cuộc trò chuyện này? Hành động này không thể hoàn ngược.'
    }
  },
  about: {
    name: '文策AI', product: '文策AI', version: 'Version', pluginType: 'Add-in type', wpsPlugin: 'WPS Writer add-in', wordPlugin: 'Microsoft Word add-in',
    developer: 'Developer', developerName: 'Riyue Xingchen', links: 'Links', repository: 'GitHub repository', website: 'Project website',
    docs: 'Documentation', issues: 'Report an issue', sponsor: 'Sponsor the author', github: 'GitHub repository', unknownVersion: 'Unknown version'
  },
  debug: {
    title: 'Bảng điều khiển gỡ lỗi', hint: 'Nhấn F12 để mở công cụ nhà phát triển', parse: 'Phân tích nội dung tài liệu', parseSelection: 'Phân tích phần chọn',
    showDocuments: 'Hiển thị tên tệp tin đang mở', openDocuments: 'Tài liệu đang mở ({count})', deleteParagraphs: 'Xóa đoạn theo chỉ số',
    deletePlaceholder: 'Nhập chỉ số đoạn bắt đầu và kết thúc (dựa trên 0), ví dụ: 3, 7', clear: 'Xóa', jsonToDoc: 'JSON sang tài liệu',
    jsonPlaceholder: 'Dán JSON vào đây...', apply: 'Áp dụng vào tài liệu', export: 'Xuất', copy: 'Sao chép vào bộ nhớ tạm',
    download: 'Tải xuống JSON', deleteAction: 'Xóa đoạn', result: 'Kết quả phân tích:', paragraphs: 'Đoạn: {count}', tables: 'Bảng: {count}', images: 'Hình ảnh: {count}', chars: 'Ký tự: {count}'
  }
};
