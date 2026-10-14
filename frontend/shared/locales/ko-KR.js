export default {
  common: {
    add: '추가', cancel: '취소', clear: '지우기', close: '닫기', confirm: '확인', delete: '삭제',
    disabled: '사용 불가', edit: '편집', enabled: '사용 가능', loading: '로딩 중...', none: '없음',
    refresh: '새로고침', remove: '제거', retry: '다시 시도', copy: '복사', save: '저장', saving: '저장 중...',
    unknown: '알 수 없음', unknownError: '알 수 없는 오류', pleaseRetry: '잠시 후 다시 시도해주세요', testing: '테스트 중...'
  },
  language: {
    label: '인터페이스 언어', chinese: '简体中文', english: 'English', indonesian: 'Bahasa Indonesia', japanese: '일본어', korean: '한국어', vietnamese: '베트남어'
  },
  windows: { assistant: '文策AI', settings: '설정', about: 'About', debug: '디버그 패널' },
  nav: { chat: 'AI 채팅', history: '채팅 기록', settings: '설정', about: 'About', debug: '디버그' },
  settings: {
    tabs: { general: '일반', model: '모델', personalization: '개인화', mcp: 'MCP', skill: '스킬', data: '데이터' },
    generalTitle: '일반 설정', generalDesc: '애플리케이션 기본 동작을 구성',
    modelTitle: '모델 설정', modelDesc: 'AI 프로바이더와 모델을 관리',
    personalizationTitle: '개인화', personalizationDesc: '어시스턴트 동작 및 응답 매개변수를 사용자 정의',
    mcpTitle: 'MCP 서버', mcpDesc: 'MCP 서버 이름과 JSON 구성을 관리하며 연결 테스트를 수행',
    skillTitle: '스킬 관리', skillDesc: '로컬 스킬을 관리: 업로드, 활성화, 폴더 열기, 삭제',
    save: '설정 저장', saving: '저장 중...', saved: '설정이 저장되었습니다.', saveFailed: '저장에 실패했습니다. 다시 시도해주세요.'
  },
  general: {
    title: '기본 설정', subtitle: '시작 동작 및 표시 모드를 구성', language: '인터페이스 언어',
    simplifiedChinese: '简体中文', english: 'English', indonesian: 'Bahasa Indonesia', japanese: '일본어', korean: '한국어', vietnamese: '베트남어',
    showPanel: '시작 시 AI 패널 표시', proofread: '교정 표시 모드', proofreadMode: '교정 표시 모드',
    redBlue: '빨간색/파란색 모드', redblue: '빨간색/파란색 모드', redBlueDesc: '삭제 부분은 연한 파란색, 추가 부분은 연한 빨간색으로 표시',
    redblueDesc: '삭제 부분은 연한 파란색, 추가 부분은 연한 빨간색으로 표시',
    revision: '변경 추적 모드', revisionDesc: 'Word의 변경 추적을 사용하여 편집을 표시', proxy: '네트워크 프록시',
    proxyTitle: '네트워크 프록시', proxyDesc: 'HTTP/HTTPS 요청을 위한 프록시 서버를 구성',
    proxySubtitle: '네트워크 프록시', enableProxy: '프록시 사용',
    host: '프록시 주소 (IP)', proxyHost: '프록시 주소 (IP)', port: '포트',
    proxyHint: 'HTTP와 HTTPS 요청은 이 프록시를 사용합니다. HTTP 프록시는 지원되지만 SOCKS 프록시는 지원되지 않습니다.'
  },
  skill: {
    title: '스킬 관리', subtitle: 'SKILL.md를 포함한 ZIP 파일을 업로드하고 로컬 스킬 디렉토리에 설치',
    upload: '스킬 ZIP 업로드', uploading: '업로드 중...', tip: 'ZIP만 지원; 압축 파일에는 SKILL.md가 포함되어야 합니다',
    zipHint: 'ZIP만 지원; 압축 파일에는 SKILL.md가 포함되어야 합니다',
    loading: '스킬 로딩 중...', empty: '스킬이 아직 없습니다. "스킬 ZIP 업로드"를 사용하여 추가해주세요.', unnamed: '이름 없는 스킬',
    toggle: '스킬 활성화/비활성화', openFolder: '스킬 폴더 열기', delete: '삭제', loadFailed: '스킬 로드 실패',
    zipOnly: 'ZIP 압축 파일만 지원됩니다', uploadZipOnly: 'ZIP 압축 파일만 지원됩니다', uploadSuccess: '스킬이 업로드되었습니다', uploadFailed: '스킬 업로드 실패',
    updateFailed: '스킬 상태 업데이트 실패', deleteConfirm: '스킬을 삭제하시겠습니까? {name}', deleteSuccess: '스킬이 삭제되었습니다',
    deleteFailed: '스킬 삭제 실패', openFailed: '스킬 폴더를 열 수 없습니다',
    builtinDeleteDisabled: '내장 스킬은 삭제할 수 없습니다'
  },
  model: {
    title: 'AI 프로바이더 구성', subtitle: 'AI 프로바이더와 모델을 관리', configured: '구성된 프로바이더',
    availableCount: '{count} 개의 사용 가능한 모델', addProvider: '프로바이더 추가', newProvider: '새 프로바이더', modelCount: '{count} 개의 모델',
    name: '이름', namePlaceholder: '예: openai', apiType: 'API 유형', openaiCompatible: 'OpenAI 호환',
    fetchModels: '모델 목록 가져오기', fetch: '모델 목록 가져오기', fetching: '가져오는 중...', collapseAvailable: '사용 가능한 모델 숨기기', collapse: '사용 가능한 모델 숨기기',
    availableModels: '사용 가능한 모델 ({count})', clickToAdd: '＋를 클릭하여 모델 추가', addHint: '＋를 클릭하여 모델 추가', addModel: '모델 추가', added: '추가됨',
    addedModels: '추가된 모델 ({count})', remove: '삭제', noModels: '모델이 없습니다. 먼저 모델 목록을 가져오세요.',
    empty: '프로바이더가 구성되어 있지 않습니다. "프로바이더 추가"를 사용해주세요.', deleteConfirm: '이 프로바이더를 삭제하시겠습니까?',
    credentialsRequired: '먼저 API 키와 베이스 URL을 입력해주세요', fetchFailed: '모델 가져오기 실패: {error}', checkConfig: '구성 확인'
  },
  mcp: {
    title: 'MCP 서버 구성', subtitle: '서버 카드를 클릭하여 확장하고 편집', add: '서버 추가', addServer: '서버 추가',
    empty: 'MCP 서버가 아직 없습니다. "서버 추가"를 사용해주세요.', unnamed: '이름 없는 서버', toggle: 'MCP 서버 활성화/비활성화',
    name: '서버 이름', serverName: '서버 이름', namePlaceholder: '예: local-filesystem', config: '서버 구성 (JSON)',
    configPlaceholder: 'MCP 서버 JSON 구성을 입력', testing: '테스트 중...', test: '연결 테스트', testConnection: '연결 테스트',
    objectRequired: '구성은 객체여야 합니다(배열이나 기본형이 아닌)', serversEmpty: 'mcpServers는 비어있을 수 없습니다',
    serverObjectRequired: '각 mcpServers 구성은 객체여야 합니다', jsonError: '유효하지 않은 JSON: {error}',
    nameRequired: '서버 이름을 입력해주세요', configRequired: '서버 구성을 입력해주세요', fixJson: 'JSON 구성을 수정해주세요',
    success: '연결 성공', failed: '연결 실패'
  },
  personalization: {
    title: '맞춤형 지시사항', instructions: '맞춤형 지시사항', subtitle: '모든 대화에서 사용되는 글로벌 AI 프롬프트를 설정',
    instructionsDesc: '모든 대화에서 사용되는 글로벌 AI 프롬프트를 설정', globalPrompt: '글로벌 프롬프트',
    promptHint: '어시스턴트가 요구사항을 이해하는 데 도움이 되도록 모든 대화에 적용됩니다',
    promptPlaceholder: '예: 당신은 전문적인 글쓰기 어시스턴트입니다. 간결하고 전문적인 답변을 제시해주세요...',
    chars: '{count} 문자', quickTemplates: '빠른 템플릿', temperature: 'LLM 온도', temperatureDesc: 'AI의 창의성과 무작위성을 조정',
    precise: '정확 (0-0.33)', preciseDesc: '더 결정적이고 일관성이 있으며 사실에 적합한 작업에 적합', balanced: '균형 (0.33-0.67)',
    balancedDesc: '정확도와 창의성의 균형을取り、대부분의 작업에 적합', creative: '창의적 (0.67-1)', creativeDesc: '더 다양하고 상상력이 있으며 브레인스토밍에 적합',
    clearConfirm: '맞춤형 지시사항을 지우시겠습니까?', overwriteConfirm: '템플릿을 적용하면 현재 지시사항이 교체됩니다. 계속하시겠습니까?',
    templates: {
      academicName: '학술 작성', academicDesc: '공식이고 엄격한 학술 스타일', academicPrompt: '당신은 전문 학술 글쓰기 어시스턴트입니다. 명확한 논리와 정확한 용어를 사용하여 공식적이고 엄격한 언어로 작성하십시오.',
      creativeName: '창의적 작성', creativeDesc: '상상력 풍부한 창의적 스타일', creativePrompt: '당신은 창의적인 글쓰기 어시스턴트입니다. 생생한 언어를 사용하여 원작 아이디어와 관점을 촉진하십시오.',
      businessName: '비즈니스 문서', businessDesc: '간결하고 전문적인 비즈니스 스타일', businessPrompt: '당신은 전문 비즈니스 글쓰기 어시스턴트입니다. 주요 내용이 명확한 간결한 문서, 보고서, 이메일을 작성하십시오.',
      casualName: '일상 대화', casualDesc: '편안하고 친근한 스타일', casualPrompt: '당신은 친근하고 접근 가능한 글쓰기 어시스턴트입니다. 자연스럽고 편안하며 읽기 쉬운 언어를 사용하십시오.'
    }
  },
  data: {
    title: '데이터 관리', subtitle: '애플리케이션 데이터와 스토리지를 관리', cache: '캐시 지우기', clearCache: '캐시 지우기',
    cacheDesc: 'project/temp와 project/uploads에서 캐시 파일을 삭제하여 디스크 공간을 확보', clearCacheDesc: 'project/temp와 project/uploads에서 캐시 파일을 삭제하여 디스크 공간을 확보',
    cacheLocation: '캐시 위치', cacheSize: '캐시 크기', scan: '스캔', scanning: '스캔 중...', clear: '캐시 지우기', clearing: '지우는 중...',
    memory: '장기 기억', memoryDesc: '가장 오래된 것부터 최신 순으로 정렬된 영구적인 AI 기억을 관리', enableMemory: '장기 기억 활성화',
    memoryPlaceholder: '여기에 장기 AI 기억이 표시됩니다. 편집하고 저장할 수 있습니다...', memoryHint: '기억은 시계열로 정렬되며, 최신 항목이 아래에 있습니다.',
    reload: '재로드', saveMemory: '기억 저장', deleteAll: '모든 데이터 삭제', deleteAllDesc: '채팅 기록과 캐시된 애플리케이션 데이터를 모두 삭제',
    irreversible: '경고: 이 작업은 취소할 수 없습니다', warning: '경고: 이 작업은 취소할 수 없습니다', deleteIncludes: '모든 데이터를 삭제하면 다음이 삭제됩니다:', chats: '모든 채팅 기록',
    cachedDocs: '캐시된 문서 데이터', sessionState: '세션 상태', confirmTitle: '모든 데이터를 삭제하시겠습니까?',
    confirmDesc: '채팅, 캐시, 설정을 모두 포함한 모든 데이터를 영구적으로 삭제합니다. 이것은 취소할 수 없습니다.',
    confirmBody: '채팅, 캐시, 설정을 모두 포함한 모든 데이터를 영구적으로 삭제합니다. 이것은 취소할 수 없습니다.', typeDelete: '확인을 위해 DELETE를 입력:',
    typeDeletePlaceholder: 'DELETE를 입력', deletePlaceholder: 'DELETE를 입력', confirmDelete: '영구 삭제', deleting: '삭제 중...', calculating: '계산 중...', noCache: '캐시 없음',
    cacheSummary: '{size} ({count} 파일)', clearConfirm: '캐시 디렉토리의 모든 파일을 지우시겠습니까?', cleared: '{count} 개의 캐시 파일을 삭제했습니다',
    clearFailed: '캐시 지우기 실패: {error}', deleted: '모든 데이터가 삭제되었습니다.', deleteFailed: '삭제 실패: {error}',
    memoryLoadFailed: '장기 기억 로드 실패: {error}', memorySaved: '장기 기억이 저장되었습니다.', memorySaveFailed: '장기 기억 저장 실패: {error}',
    memoryToggled: '장기 기억 {state}', memoryEnabled: '활성화', memoryDisabled: '비활성화',
    toggleFailed: '기억 설정 저장 실패: {error}'
  },
  session: {
    title: '채팅 기록', newChat: '새 채팅', empty: '채팅 기록이 없습니다', newConversation: '새 대화', noMessages: '메시지가 없습니다',
    rename: '이름 변경', renameTitle: '대화 이름 변경', renamePlaceholder: '새 이름을 입력', deleteTitle: '대화 삭제',
    deleteBody: '이 대화를 삭제하시겠습니까? 이 작업은 취소할 수 없습니다.'
  },
  chat: {
    attachment: '첨부 파일', removeFile: '파일 삭제', chars: '{count} 문자', clearSelection: '선택 지우기',
    allowThinking: '생각하기 켜짐', disableThinking: '생각하기 꺼짐', thinkingToggle: '생각하기 켜기/끄기',
    addFile: '파일 추가', addSelection: '선택 추가', send: '전송', stop: '중지',
    agentPlaceholder: '다음에 구축할 것을 설명', askPlaceholder: '질문 입력',
    chooseModel: '모델 선택', deleteParagraphs: '{count} 문단 삭제', aiOperation: 'AI 수정: {actions} (보류 중 확인)', revisionCount: '{count}개 변경 사항',
    acceptRevision: '수락', rejectRevision: '거부',
    context: '컨텍스트: {current}k / {max}k 토큰 ({percentage}%)', unnamedFile: '이름 없는 파일',
    unsupportedFiles: '지원하지 않는 파일: {files}. 지원 형식: png, jpg, jpeg, pdf, docx, txt, md.',
    paragraphRange: '문단 {start} - {end}', showHistory: '채팅 기록 표시', whatCanIDo: '무엇을 할 수 있나요?',
    documentation: '문서', selectionRef: '참조 선택 ({count})', fileRef: '참조 파일 ({count})',
    unknownFile: '알 수 없는 파일', preparing: 'AI가 준비 중', thinking: '생각하기', thinkingDone: '생각하기 (완료)',
    contextCompactionStarted: '🗜️ 컨텍스트 자동 압축 중', contextCompactionCompleted: '✅ 컨텍스트 압축 완료',
    collapseMcp: 'MCP 세부사항 접기', expandMcp: 'MCP 세부사항 펼치기', callMcp: 'MCP 도구 호출 중: {name}',
    arguments: '인수:', noArguments: '인수 없음', toolOutput: '도구 출력:', noOutput: '(출력 없음)',
    outputDocument: '문서에 삽입', copyImage: '이미지 복사', saveImage: '이미지 저장', selection: '선택',
    copyImageFailed: '복사 실패. 컨텍스트 메뉴에서 이미지를 저장해주세요.',
    mcpWaiting: '도구 출력 대기 중...', unknownArguments: '인수 사용 불가', imageTableSelection: '[이미지와 표 선택]',
    imageSelection: '[이미지 선택]', tableSelection: '[표 선택]', networkTimeout: '네트워크 연결이 타임아웃되고 닫혔습니다.',
    networkError: '네트워크 오류: {error}. 백엔드 서비스가 localhost:3880에서 실행 중인지 확인해주세요.',
    networkInterruptedReconnecting: '연결이 끊어지고 이 요청이 실패했습니다. 자동으로 재연결 중이며 곧 다시 시도해주세요.',
    readingDocumentById: '문서 읽는 중 (문단 ID {start} - {end})',
    readingDocument: '문서 읽는 중 (문단 {start} - {end})', searchingDocument: '문서 검색 중...',
    generatingDocument: '문서 생성 중', documentInsertFailed: '문서 삽입 실패. 대상 위치와 문서 권한을 확인해주세요.',
    deletePreview: '{ids} 삭제', generatedPending: '{summary} 생성됨',
    wpsUnavailable: 'WPS API를 사용할 수 없습니다', openDocumentFirst: 'Word 문서를 먼저 열어주세요', messageMissing: '메시지를 찾을 수 없습니다',
    undoFailed: '되돌리기 실패: {error}', selectionUnavailable: '선택 내용을 읽을 수 없습니다. WPS Writer에서 콘텐츠를 선택해주세요.',
    selectionRangeUnavailable: '선택 범위를 지정할 수 없습니다', selectContentFirst: '문서에서 텍스트, 이미지, 또는 표를 선택해주세요.',
    selectionFailed: '선택 내용 처리 실패: {error}', insertFailed: '삽입 실패. Word 문서가 열려 있는지 확인해주세요.', unnamedDocument: '이름 없는 문서',
    searchComplete: '검색 완료', documentReadComplete: '문서 읽기 완료', prepareDelete: '문단 ID ({ids})에 대한 추적 삭제 적용 중',
    deleteComplete: '삭제 완료', insertBreakSuccess: '문서 줄바꿈 삽입', insertBreakFailed: '문서 줄바꿈 삽입 실패: {error}', createDocumentPending: '새 빈 DOCX 문서 생성 중', createDocumentSuccess: '새 빈 DOCX 문서가 생성되고 열렸습니다', createDocumentFailed: '새 DOCX 문서 생성 실패: {error}', documentGenerated: '문서가 생성되었습니다', errorLabel: '오류: {error}',
    paragraphCount: '{count} 문단', tableCount: '{count} 표', summarySeparator: ', ', actionSeparator: ', ', pendingAddition: '보류 중 추가',
    input: {
      attachment: '첨부 파일', removeFile: '파일 삭제', paragraphRange: '문단 {start} - {end}', clearSelection: '선택 지우기',
      confirm: '확인', cancel: '취소', modelsLoading: '로딩 중...', thinkingAria: '생각하기 켜기/끄기',
      thinkingOn: '생각하기 켜짐', thinkingOff: '생각하기 꺼짐', addFile: '파일 추가', addSelection: '선택 추가', send: '전송', stop: '중지',
      agentPlaceholder: '다음에 구축할 것을 설명', askPlaceholder: '질문 입력',
      chooseModel: '모델 선택', deleteParagraphs: '{count} 문단 삭제', aiOperation: 'AI 수정: {actions} (보류 중 확인)',
      context: '컨텍스트: {current}k / {max}k 토큰 ({percentage}%)', unnamedFile: '이름 없는 파일',
      unsupportedFiles: '지원하지 않는 파일: {files}. 지원 형식: png, jpg, pdf, docx, txt, md.'
    },
    messages: {
      showHistory: '채팅 기록 표시', empty: '무엇을 할 수 있나요?', docs: '문서', selections: '참조 선택 ({count})',
      files: '참조 파일 ({count})', unknownFile: '알 수 없는 파일', preparing: 'AI가 준비 중', thinking: '생각하기',
      thinkingDone: '생각하기 (완료)', collapseMcp: 'MCP 세부사항 접기', expandMcp: 'MCP 세부사항 펼치기',
      mcpCall: 'MCP 도구 호출 중: {name}', parameters: '인수:', noParameters: '인수 없음', output: '도구 출력:', noOutput: '(출력 없음)',
      copy: '복사', insert: 'Word에 삽입', retry: '다시 시도', undo: '되돌리기'
    },
    session: {
      newChat: '새 채팅', title: '채팅 기록', empty: '채팅 기록이 없습니다', rename: '이름 변경', delete: '삭제',
      renameTitle: '대화 이름 변경', renamePlaceholder: '대화 이름 입력', deleteTitle: '대화 삭제',
      deleteConfirm: '이 대화를 삭제하시겠습니까? 이 작업은 취소할 수 없습니다.'
    }
  },
  about: {
    name: '文策AI', product: '文策AI', version: 'Version', pluginType: 'Add-in type', wpsPlugin: 'WPS Writer add-in', wordPlugin: 'Microsoft Word add-in',
    developer: 'Developer', developerName: 'Riyue Xingchen', links: 'Links', repository: 'GitHub repository', website: 'Project website',
    docs: 'Documentation', issues: 'Report an issue', sponsor: 'Sponsor the author', github: 'GitHub repository', unknownVersion: 'Unknown version'
  },
  debug: {
    title: '디버그 패널', hint: '개발자 도구를 열려면 F12를 누르세요', parse: '문서 내용 파싱', parseSelection: '선택 파싱',
    showDocuments: '열려 있는 파일 이름 표시', openDocuments: '열려 있는 문서 ({count})', deleteParagraphs: '인덱스별 문단 삭제',
    deletePlaceholder: '예: 3, 7처럼 0부터 시작하는 문단 인덱스 입력', clear: '지우기', jsonToDoc: 'JSON을 문서로',
    jsonPlaceholder: '여기에 JSON을 붙여넣으세요...', apply: '문서에 적용', export: '내보내기', copy: '클립보드에 복사',
    download: 'JSON 다운로드', deleteAction: '문단 삭제', result: '파싱 결과:', paragraphs: '문단: {count}', tables: '표: {count}', images: '이미지: {count}', chars: '문자 수: {count}'
  }
};
