STRINGS = {
    "app": {"name": "WenCe AI"},
    "tray": {"show": "Hiện", "quit": "Thoát", "tooltip": "WenCe AI"},
    "nav": {
        "home": "Trang chủ",
        "dashboard": "Bảng điều khiển",
        "wps": "Tiện ích WPS",
        "office": "Tiện ích Office",
        "mcp": "Máy chủ MCP",
        "console": "Bảng điều khiển",
    },
    "home": {
        "subtitle": "Viết chiến lược, diễn đạt thông minh hơn",
        "status": {
            "runningChecking": "Backend đang chạy (đang kiểm tra cập nhật)",
            "runningNoUpdateInfo": "Backend đang chạy (không thể lấy thông tin cập nhật)",
            "runningLatest": "Backend đang chạy (đã là phiên bản mới nhất)",
            "newVersion": "Phiên bản mới có sẵn: {tag}, vui lòng tải xuống từ trang web",
            "updateFailed": "Kiểm tra cập nhật thất bại",
        },
        "version": {"current": "Phiên bản hiện tại: {version}", "unknown": "Không xác định"},
        "update": {
            "checking": "Đang kiểm tra cập nhật...",
            "failed": "Kiểm tra cập nhật thất bại",
            "latest": "Đã là phiên bản mới nhất",
            "new": "Phiên bản mới: {tag}",
        },
        "button": {"github": "GitHub", "website": "Tài liệu trang web", "downloadLatest": "Tải phiên bản mới nhất"},
        "cards": {
            "crossPlatform": {
                "title": "Đa nền tảng",
                "desc": "Được xây dựng cho WPS và Microsoft Word, hỗ trợ Windows và Linux để hỗ trợ viết AI dễ tiếp cận.",
            },
            "richText": {
                "title": "Văn bản phong phú gốc",
                "desc": "Agent hiểu cấu trúc tài liệu Word, hỗ trợ tiêu đề, nội dung, đậm, phông chữ, thụt lề, khoảng cách dòng và hơn thế nữa.",
            },
            "workflow": {
                "title": "Quy trình làm việc dựa trên công cụ",
                "desc": "Hoàn thành viết dài, nghiên cứu và chỉnh sửa phức tạp thông qua công cụ tài liệu, MCP và Skills.",
            },
            "open": {
                "title": "Mở & Linh hoạt",
                "desc": "Hỗ trợ API tùy chỉnh hoặc dịch vụ cục bộ, tương thích với hầu hết các nhà cung cấp LLM phổ biến.",
            },
        },
        "infobar": {
            "newVersion": {
                "title": "Phiên bản mới có sẵn",
                "content": "Phiên bản mới nhất {tag} được phát hiện, vui lòng tải xuống từ trang web.",
            }
        },
    },
    "dashboard": {
        "title": "Bảng điều khiển sử dụng token",
        "subtitle": "Thống kê sử dụng token WenCe AI gần đây",
        "period": {"today": "Hôm nay", "7d": "7 ngày"},
        "metrics": {
            "inputTokens": "Token đầu vào",
            "outputTokens": "Token đầu ra",
            "cachedTokens": "Token bộ nhớ đệm",
            "cacheHitRate": "Tỷ lệ bộ nhớ đệm",
        },
        "chart": {"trend": "Xu hướng sử dụng", "empty": "Không có dữ liệu sử dụng token"},
        "status": {
            "loading": "Đang tải...",
            "hover": "Di chuột vào biểu đồ để xem chi tiết",
            "empty": "Không có bản ghi sử dụng",
            "failed": "Không thể tải dữ liệu, vui lòng thử lại",
            "invalid": "Định dạng dữ liệu sử dụng token không hợp lệ",
        },
        "tooltip": {"input": "Đầu vào:", "output": "Đầu ra:", "cached": "Bộ nhớ đệm:"},
    },
    "console": {
        "title": "Bảng điều khiển",
        "buttons": {"logDir": "Thư mục nhật ký", "clear": "Xóa", "bottom": "Cuối cùng"},
        "hint": "Hiển thị tất cả đầu ra nhật ký trong quá trình chạy ứng dụng",
        "tooltips": {"logDir": "Mở thư mục nhật ký", "clear": "Xóa nhật ký", "bottom": "Cuộn xuống cuối"},
        "error": {"openLogDir": "Không thể mở thư mục nhật ký"},
    },
    "wps": {"title": "Tiện ích WPS Word", "subtitle": "Quản lý cài đặt tiện ích WPS Office"},
    "office": {
        "title": "Tiện ích Microsoft Word",
        "subtitle": "Quản lý cài đặt tiện ích web và máy tính để bàn Microsoft Word",
        "usage": (
            "Cài đặt chứng thực:<br/>"
            '1. Đảm bảo "Bắt đầu dịch vụ HTTPS" đang chạy. (Tự động bắt đầu khi bạn mở trang này)<br/>'
            '2. Nhấp vào "Cài đặt chứng thực", sau đó trong hộp thoại hệ thống: Cài đặt chứng thực -> Máy tính cục bộ -> Đặt tất cả chứng thực vào kho lưu trữ sau -> Duyệt -> Cơ quan phát hành chứng thực gốc đáng tin cậy, sau đó xác nhận.<br/>'
            '3. Nhấp vào "Mở trong trình duyệt", nếu không có cảnh báo bảo mật, chứng thực đã được cài đặt; nếu không, khởi động lại dịch vụ backend và thử lại. Nếu vẫn có cảnh báo, hãy cài đặt thủ công hoặc liên hệ tác giả.<br/><br/>'
            "Phương pháp sử dụng phiên bản web:<br/>"
            "1. Mở <a href='https://word.cloud.microsoft/' style='color: #2563eb; text-decoration: underline;'>https://word.cloud.microsoft/</a> và vào Word for the web.<br/>"
            "2. Đi đến: Trang chủ -> Tiện ích -> Tiện ích khác -> Tiện ích của tôi -> Quản lý tiện ích của tôi -> Tải tiện ích của tôi lên<br/>"
            "3. Tải lên manifest.xml đã tải xuống. Làm mới nếu bảng tiện ích không xuất hiện.<br/><br/>"
            "Phương pháp sử dụng phiên bản máy tính để bàn:<br/>"
            '1. Nhấp vào "Tải xuống manifest.xml" và lưu vào một thư mục trống.<br/>'
            "2. Nhấp chuột phải vào thư mục -> Thuộc tính -> Chia sẻ -> Chia sẻ -> Mọi người -> Chia sẻ và ghi lại đường dẫn mạng.<br/>"
            "3. Mở Microsoft Word: Tệp -> Tùy chọn -> Trung tâm tin cậy -> Cài đặt trung tâm tin cậy -> Danh mục tiện ích đáng tin cậy, nhập đường dẫn mạng và Thêm danh mục, khởi động lại Word.<br/>"
            '4. Nếu bảng không xuất hiện: Tệp -> Tùy chọn -> Tùy chỉnh băng ribbon, thêm Nhà phát triển vào tab chính. Nhấp vào tab "Nhà phát triển" của Word, Tiện ích -> Thư mục chia sẻ -> WenCe AI Assistant.<br/><br/>'
            "【Hướng dẫn chi tiết: <a href='https://visresearch.github.io/WordAgent/' style='color: #2563eb; text-decoration: underline;'>https://visresearch.github.io/WordAgent/</a>】"
        ),
        "buttons": {
            "download": "Tải xuống manifest.xml",
            "start": "Bắt đầu dịch vụ HTTPS",
            "installCert": "Cài đặt chứng thực",
            "openBrowser": "Mở trong trình duyệt",
            "stop": "Dừng dịch vụ",
        },
        "status": {"running": "Dịch vụ đang chạy (https://{host}:{port})", "stopped": "Dịch vụ không chạy"},
        "infobar": {
            "downloadFailed": {
                "title": "Tải xuống thất bại",
                "contentMissing": "Không tìm thấy gui/resources/manifest.xml",
            },
            "downloadSuccess": {"title": "Tải xuống thành công", "content": "Đã lưu manifest.xml vào: {path}"},
            "openBrowser": {"title": "Đã mở trong trình duyệt"},
            "openBrowserFailed": {"title": "Không thể mở trình duyệt"},
            "certOpened": {"title": "Đã mở tệp chứng thực", "content": "Vui lòng làm theo hướng dẫn trên trang này"},
            "certFailed": {
                "title": "Không thể mở chứng thực",
                "content": "Vui lòng tìm và cài đặt thủ công, đường dẫn: {path}",
            },
            "serviceRunning": {"title": "Thông báo", "content": "Dịch vụ HTTPS đã đang chạy"},
            "startFailed": {
                "title": "Khởi động thất bại",
                "contentMissingDist": "Không tìm thấy microsoft_word_plugin/dist, vui lòng xây dựng frontend trước",
            },
            "startSuccess": {
                "title": "Khởi động thành công",
                "content": "Đã khởi động dịch vụ HTTPS: https://{host}:{port}",
            },
            "stopped": {"title": "Đã dừng", "content": "Đã dừng dịch vụ HTTPS"},
            "stopFailed": {"title": "Dừng thất bại"},
            "notRunning": {"title": "Thông báo", "content": "Dịch vụ HTTPS không chạy"},
        },
        "dialog": {"saveManifest": "Lưu manifest.xml", "xmlFilter": "Tệp XML (*.xml)"},
    },
    "mcp": {
        "title": "Máy chủ MCP",
        "subtitle": "Cho phép Codex và các ứng dụng khác dùng công cụ tài liệu WPS / Microsoft Word hiện tại",
        "endpoint": "Địa chỉ kết nối: {url}",
        "running": "Máy chủ đang chạy",
        "stopped": "Máy chủ đã dừng",
        "backendUnavailable": "Dịch vụ backend chưa sẵn sàng",
        "start": "Chạy",
        "stop": "Dừng",
        "startFailed": "Không thể khởi động máy chủ MCP",
        "clients": "Ứng dụng hoạt động gần đây ({count})",
        "client": "{name} · yêu cầu cách đây {seconds} giây",
        "noClients": "Chưa có ứng dụng hoạt động",
        "activityHint": "Máy chủ dùng HTTP không lưu trạng thái. Ứng dụng được hiển thị trong 2 phút sau mỗi yêu cầu; không thể xác định chính xác ứng dụng còn mở hay không. Hãy mở bảng tiện ích WPS / Microsoft Word để dùng công cụ tài liệu.",
        "configTitle": "Cấu hình JSON MCP",
    },
    "language": {
        "label": "Ngôn ngữ",
        "english": "English",
        "chinese": "简体中文",
        "indonesian": "Bahasa Indonesia",
        "japanese": "日本語",
        "korean": "한국어",
        "vietnamese": "Tiếng Việt",
    },
    "common": {"unknownVersion": "Không xác định", "save": "Lưu", "cancel": "Hủy"},
}
