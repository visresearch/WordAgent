STRINGS = {
    "app": {"name": "WenCe AI"},
    "tray": {"show": "표시", "quit": "종료", "tooltip": "WenCe AI"},
    "nav": {
        "home": "홈",
        "dashboard": "대시보드",
        "wps": "WPS 애드인",
        "office": "Office 애드인",
        "mcp": "MCP 서버",
        "console": "콘솔",
    },
    "home": {
        "subtitle": "전략적 글쓰기, 더 스마트한 표현",
        "status": {
            "runningChecking": "백엔드 실행 중 (업데이트 확인 중)",
            "runningNoUpdateInfo": "백엔드 실행 중 (업데이트 정보를 가져올 수 없습니다)",
            "runningLatest": "백엔드 실행 중 (최신 버전입니다)",
            "newVersion": "새 버전이 있습니다: {tag}, 웹사이트에서 다운로드하세요",
            "updateFailed": "업데이트 확인 실패",
        },
        "version": {"current": "현재 버전: {version}", "unknown": "알 수 없음"},
        "update": {
            "checking": "업데이트 확인 중...",
            "failed": "업데이트 확인 실패",
            "latest": "최신 버전입니다",
            "new": "새 버전: {tag}",
        },
        "button": {"github": "GitHub", "website": "웹사이트 문서", "downloadLatest": "최신 버전 다운로드"},
        "cards": {
            "crossPlatform": {
                "title": "크로스 플랫폼",
                "desc": "WPS와 Microsoft Word용으로 구축, Windows 및 Linux 지원으로 AI 글쓰기 지원의 장벽을 낮춥니다.",
            },
            "richText": {
                "title": "네이티브 리치 텍스트",
                "desc": "에이전트는 Word 문서 구조를 이해하여 제목, 본문, 굵게, 글꼴, 들여쓰기, 줄 간격 등을 지원합니다.",
            },
            "workflow": {
                "title": "도구 기반 워크플로우",
                "desc": "문서 도구, MCP, Skills를 통해 장문 글쓰기, 연구, 복잡한 편집을 완료합니다.",
            },
            "open": {
                "title": "오픈 & 유연",
                "desc": "사용자 정의 API 또는 로컬 서비스를 지원하며 대부분의 주류 LLM 제공업체와 호환됩니다.",
            },
        },
        "infobar": {
            "newVersion": {
                "title": "새 버전이 있습니다",
                "content": "최신 버전 {tag}이 감지되었습니다. 웹사이트에서 다운로드하세요.",
            }
        },
    },
    "dashboard": {
        "title": "토큰 사용량 대시보드",
        "subtitle": "최근 WenCe AI 토큰 사용량 통계",
        "period": {"today": "오늘", "7d": "7일"},
        "metrics": {
            "inputTokens": "입력 토큰",
            "outputTokens": "출력 토큰",
            "cachedTokens": "캐시 토큰",
            "cacheHitRate": "캐시 히트율",
        },
        "chart": {"trend": "사용량 추이", "empty": "토큰 사용량 데이터가 없습니다"},
        "status": {
            "loading": "로딩 중...",
            "hover": "자세한 내용은 차트에 호버하세요",
            "empty": "사용 기록이 없습니다",
            "failed": "데이터 로드 실패, 다시 시도하세요",
            "invalid": "잘못된 토큰 사용량 데이터 형식",
        },
        "tooltip": {"input": "입력:", "output": "출력:", "cached": "캐시:"},
    },
    "console": {
        "title": "콘솔",
        "buttons": {"logDir": "로그 폴더", "clear": "지우기", "bottom": "하단으로"},
        "hint": "앱 실행 중 모든 로그 출력을 표시합니다",
        "tooltips": {"logDir": "로그 폴더 열기", "clear": "로그 지우기", "bottom": "하단으로 스크롤"},
        "error": {"openLogDir": "로그 폴더를 열 수 없습니다"},
    },
    "wps": {"title": "WPS Word 애드인", "subtitle": "WPS Office 애드인 설치 관리"},
    "office": {
        "title": "Microsoft Word 애드인",
        "subtitle": "Microsoft Word 웹 및 데스크톱 애드인 설치 관리",
        "usage": (
            "인증서 설치:<br/>"
            '1. "HTTPS 서비스 시작"이 실행 중인지 확인하세요. (이 페이지를 열면 자동으로 시작됩니다)<br/>'
            '2. "인증서 설치"를 클릭하고 시스템 대화상자에서: 인증서 설치 -> 로컬 컴퓨터 -> 모든 인증서를 다음 저장소에 배치 -> 찾아보기 -> 신뢰할 수 있는 루트 인증 기관, 그 다음 확인합니다.<br/>'
            '3. "브라우저에서 열기"를 클릭하고 보안 경고가 표시되지 않으면 인증서가 설치된 것입니다. 그렇지 않으면 백엔드 서비스를 다시 시작하고 다시 시도하세요. 여전히 경고가 표시되면 수동으로 설치하거나 작성자에게 문의하세요.<br/><br/>'
            "웹 버전 사용 방법:<br/>"
            "1. <a href='https://word.cloud.microsoft/' style='color: #2563eb; text-decoration: underline;'>https://word.cloud.microsoft/</a>를 열고 Word for the web에 들어갑니다.<br/>"
            "2. 이동: 홈 -> 애드인 -> 더 많은 애드인 -> 내 애드인 -> 내 애드인 관리 -> 내 애드인 업로드<br/>"
            "3. 다운로드한 manifest.xml을 업로드합니다. 애드인 패널이 표시되지 않으면 새로고침하세요.<br/><br/>"
            "데스크톱 버전 사용 방법:<br/>"
            '1. "manifest.xml 다운로드"를 클릭하여 빈 폴더에 저장합니다.<br/>'
            "2. 폴더를 마우스 오른쪽 버튼으로 클릭 -> 속성 -> 공유 -> 공유 -> 모든 사용자 -> 공유하고 네트워크 경로를 메모합니다.<br/>"
            "3. Microsoft Word를 엽니다: 파일 -> 옵션 -> 트러스트 센터 -> 트러스트 센터 설정 -> 신뢰할 수 있는 애드인 카탈로그, 네트워크 경로를 입력하고 카탈로그 추가, Word를 다시 시작합니다.<br/>"
            '4. 패널이 표시되지 않으면: 파일 -> 옵션 -> 리본 사용자 지정에서 개발 도구를 기본 탭에 추가합니다. Word의 "개발 도구" 탭을 클릭하고 애드인 -> 공유 폴더 -> WenCe AI Assistant를 선택합니다.<br/><br/>'
            "【상세 가이드: <a href='https://visresearch.github.io/WordAgent/' style='color: #2563eb; text-decoration: underline;'>https://visresearch.github.io/WordAgent/</a>】"
        ),
        "buttons": {
            "download": "manifest.xml 다운로드",
            "start": "HTTPS 서비스 시작",
            "installCert": "인증서 설치",
            "openBrowser": "브라우저에서 열기",
            "stop": "서비스 중지",
        },
        "status": {"running": "서비스 실행 중 (https://{host}:{port})", "stopped": "서비스가 실행되지 않았습니다"},
        "infobar": {
            "downloadFailed": {
                "title": "다운로드 실패",
                "contentMissing": "gui/resources/manifest.xml을 찾을 수 없습니다",
            },
            "downloadSuccess": {"title": "다운로드 성공", "content": "manifest.xml을 저장했습니다: {path}"},
            "openBrowser": {"title": "브라우저에서 열었습니다"},
            "openBrowserFailed": {"title": "브라우저를 열 수 없습니다"},
            "certOpened": {"title": "인증서 파일을 열었습니다", "content": "이 페이지의 지침을 따르세요"},
            "certFailed": {"title": "인증서를 열 수 없습니다", "content": "수동으로 찾아 설치하세요. 경로: {path}"},
            "serviceRunning": {"title": "알림", "content": "HTTPS 서비스가 이미 실행 중입니다"},
            "startFailed": {
                "title": "시작 실패",
                "contentMissingDist": "microsoft_word_plugin/dist를 찾을 수 없습니다. 먼저 프론트엔드를 빌드하세요",
            },
            "startSuccess": {
                "title": "성공적으로 시작했습니다",
                "content": "HTTPS 서비스를 시작했습니다: https://{host}:{port}",
            },
            "stopped": {"title": "중지됨", "content": "HTTPS 서비스를 중지했습니다"},
            "stopFailed": {"title": "중지 실패"},
            "notRunning": {"title": "알림", "content": "HTTPS 서비스가 실행되지 않았습니다"},
        },
        "dialog": {"saveManifest": "manifest.xml 저장", "xmlFilter": "XML 파일 (*.xml)"},
    },
    "mcp": {
        "title": "MCP 서버",
        "subtitle": "Codex 등의 클라이언트가 현재 WPS / Microsoft Word 문서 도구를 사용할 수 있습니다",
        "endpoint": "연결 주소: {url}",
        "running": "서버 실행 중",
        "stopped": "서버 중지됨",
        "backendUnavailable": "백엔드 서비스가 아직 준비되지 않았습니다",
        "start": "실행",
        "stop": "중지",
        "startFailed": "MCP 서버를 시작하지 못했습니다",
        "clients": "최근 활성 클라이언트 ({count})",
        "client": "{name} · {seconds}초 전 요청",
        "noClients": "활성 클라이언트가 없습니다",
        "activityHint": "이 서버는 상태 비저장 HTTP를 사용합니다. 요청 후 2분 동안 클라이언트를 표시하며, 클라이언트 앱이 열려 있는지 정확히 알 수는 없습니다. 문서 도구를 사용하려면 WPS / Microsoft Word 추가 기능 창을 여세요.",
        "configTitle": "MCP JSON 설정",
    },
    "language": {
        "label": "언어",
        "english": "English",
        "chinese": "简体中文",
        "indonesian": "Bahasa Indonesia",
        "japanese": "日本語",
        "korean": "한국어",
        "vietnamese": "Tiếng Việt",
    },
    "common": {"unknownVersion": "알 수 없는 버전", "save": "저장", "cancel": "취소"},
}
