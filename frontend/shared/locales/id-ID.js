export default {
  common: {
    add: 'Tambah', cancel: 'Batal', clear: 'Kosongkan', close: 'Tutup', confirm: 'Konfirmasi', delete: 'Hapus',
    disabled: 'Nonaktif', edit: 'Edit', enabled: 'Aktif', loading: 'Memuat...', none: 'Tidak ada',
    refresh: 'Muat ulang', remove: 'Hapus', retry: 'Coba lagi', copy: 'Salin', save: 'Simpan', saving: 'Menyimpan...',
    unknown: 'Tidak diketahui', unknownError: 'Kesalahan tidak diketahui', pleaseRetry: 'Silakan coba lagi nanti', testing: 'Menguji...'
  },
  language: {
    label: 'Bahasa antarmuka', chinese: '简体中文', english: 'English', indonesian: 'Bahasa Indonesia'
  },
  windows: { assistant: '文策AI', settings: 'Pengaturan', about: 'Tentang', debug: 'Panel debug' },
  nav: { chat: 'Obrolan AI', history: 'Riwayat obrolan', settings: 'Pengaturan', about: 'Tentang', debug: 'Debug' },
  settings: {
    tabs: { general: 'Umum', model: 'Model', personalization: 'Personalisasi', mcp: 'MCP', skill: 'Skill', data: 'Data' },
    generalTitle: 'Pengaturan umum', generalDesc: 'Konfigurasikan perilaku dasar aplikasi',
    modelTitle: 'Pengaturan model', modelDesc: 'Konfigurasikan penyedia dan model AI',
    personalizationTitle: 'Personalisasi', personalizationDesc: 'Sesuaikan perilaku asisten dan parameter respons',
    mcpTitle: 'Server MCP', mcpDesc: 'Kelola nama server MCP dan konfigurasi JSON, termasuk uji koneksi',
    skillTitle: 'Manajemen skill', skillDesc: 'Kelola skill lokal: unggah, aktifkan, buka folder, dan hapus',
    save: 'Simpan pengaturan', saving: 'Menyimpan...', saved: 'Pengaturan disimpan.', saveFailed: 'Gagal menyimpan. Silakan coba lagi.'
  },
  general: {
    title: 'Pengaturan dasar', subtitle: 'Konfigurasikan perilaku saat startup dan mode tampilan', language: 'Bahasa antarmuka',
    simplifiedChinese: '简体中文', english: 'English', indonesian: 'Bahasa Indonesia', japanese: 'Bahasa Jepang', korean: 'Bahasa Korea', vietnamese: 'Bahasa Vietnam',
    showPanel: 'Tampilkan panel AI saat startup', proofread: 'Mode tampilan proofreading', proofreadMode: 'Mode tampilan proofreading',
    redBlue: 'Mode merah/biru', redblue: 'Mode merah/biru', redBlueDesc: 'Tandai penghapusan dengan biru muda dan penambahan dengan merah muda',
    redblueDesc: 'Tandai penghapusan dengan biru muda dan penambahan dengan merah muda',
    revision: 'Mode track changes', revisionDesc: 'Gunakan track changes Word untuk menandai edit', proxy: 'Proxy jaringan',
    proxyTitle: 'Proxy jaringan', proxyDesc: 'Konfigurasikan server proxy untuk permintaan HTTP/HTTPS',
    proxySubtitle: 'Konfigurasikan server proxy untuk permintaan HTTP/HTTPS', enableProxy: 'Aktifkan proxy',
    host: 'Alamat proxy (IP)', proxyHost: 'Alamat proxy (IP)', port: 'Port',
    proxyHint: 'Permintaan HTTP dan HTTPS menggunakan proxy ini. Hanya mendukung proxy HTTP; proxy SOCKS tidak didukung.'
  },
  skill: {
    title: 'Manajemen skill', subtitle: 'Unggah ZIP yang berisi SKILL.md dan pasang di direktori skill lokal',
    upload: 'Unggah ZIP skill', uploading: 'Mengunggah...', tip: 'Hanya ZIP; arsip harus berisi SKILL.md',
    zipHint: 'Hanya ZIP; arsip harus berisi SKILL.md',
    loading: 'Memuat daftar skill...', empty: 'Belum ada skill. Gunakan “Unggah ZIP skill” untuk menambahkan.', unnamed: 'Skill tanpa nama',
    toggle: 'Aktifkan atau nonaktifkan skill', openFolder: 'Buka folder skill', delete: 'Hapus', loadFailed: 'Gagal memuat skill',
    zipOnly: 'Hanya arsip ZIP yang didukung', uploadZipOnly: 'Hanya arsip ZIP yang didukung', uploadSuccess: 'Skill diunggah', uploadFailed: 'Gagal mengunggah skill',
    updateFailed: 'Gagal memperbarui status skill', deleteConfirm: 'Hapus skill: {name}?', deleteSuccess: 'Skill dihapus',
    deleteFailed: 'Gagal menghapus skill', openFailed: 'Gagal membuka folder skill',
    builtinDeleteDisabled: 'Skill bawaan tidak dapat dihapus'
  },
  model: {
    parameters: {
      editTitle: 'Edit model {name}',
      temperatureHint: 'Mengontrol keacakan keluaran, biasanya dari 0 hingga 2. Nilai lebih tinggi menghasilkan keluaran lebih acak.',
      topPHint: 'Parameter nucleus sampling, biasanya dari 0 hingga 1. Mengontrol massa probabilitas yang dipertimbangkan model.',
      maxTokensHint: 'Jumlah maksimum token yang dihasilkan. Kosongkan untuk menggunakan 8192.',
      reasoningHint: 'Mengontrol intensitas penalaran. Nilai yang didukung bergantung pada model.',
      numericValue: 'Nilai {name}'
    },
    title: 'Konfigurasi penyedia AI', subtitle: 'Kelola penyedia dan model AI', configured: 'Penyedia terkonfigurasi',
    availableCount: '{count} model tersedia', addProvider: 'Tambah penyedia', newProvider: 'Penyedia baru', modelCount: '{count} model',
    name: 'Nama', namePlaceholder: 'Contoh: openai', apiType: 'Tipe API', openaiCompatible: 'Kompatibel OpenAI',
    fetchModels: 'Ambil daftar model', fetch: 'Ambil daftar model', fetching: 'Mengambil...', collapseAvailable: 'Sembunyikan daftar model', collapse: 'Sembunyikan daftar model',
    availableModels: 'Model tersedia ({count})', clickToAdd: 'Klik + untuk menambahkan model', addHint: 'Klik + untuk menambahkan model', addModel: 'Tambah model', added: 'Ditambahkan',
    addedModels: 'Model ditambahkan ({count})', remove: 'Hapus', noModels: 'Belum ada model. Ambil daftar model terlebih dahulu.',
    empty: 'Belum ada penyedia. Gunakan “Tambah penyedia” untuk memulai.', deleteConfirm: 'Hapus penyedia ini?',
    credentialsRequired: 'Masukkan API key dan base URL terlebih dahulu', fetchFailed: 'Gagal mengambil model: {error}', checkConfig: 'Periksa konfigurasi'
  },
  mcp: {
    title: 'Konfigurasi server MCP', subtitle: 'Klik kartu server untuk membuka dan mengedit', add: 'Tambah server', addServer: 'Tambah server',
    empty: 'Belum ada server MCP. Gunakan “Tambah server” untuk memulai.', unnamed: 'Server tanpa nama', toggle: 'Aktifkan atau nonaktifkan server MCP',
    name: 'Nama server', serverName: 'Nama server', namePlaceholder: 'Contoh: local-filesystem', config: 'Konfigurasi server (JSON)',
    configPlaceholder: 'Masukkan konfigurasi JSON server MCP', testing: 'Menguji...', test: 'Uji koneksi', testConnection: 'Uji koneksi',
    objectRequired: 'Konfigurasi harus berupa objek JSON, bukan array atau nilai primitif', serversEmpty: 'mcpServers tidak boleh kosong',
    serverObjectRequired: 'Setiap konfigurasi mcpServers harus berupa objek', jsonError: 'JSON tidak valid: {error}',
    nameRequired: 'Masukkan nama server terlebih dahulu', configRequired: 'Masukkan konfigurasi server terlebih dahulu', fixJson: 'Perbaiki konfigurasi JSON terlebih dahulu',
    success: 'Terhubung', failed: 'Koneksi gagal'
  },
  personalization: {
    title: 'Instruksi kustom', instructions: 'Instruksi kustom', subtitle: 'Atur prompt global AI yang digunakan di setiap percakapan',
    instructionsDesc: 'Atur prompt global AI yang digunakan di setiap percakapan', globalPrompt: 'Prompt global',
    promptHint: 'Diterapkan di setiap percakapan untuk membantu asisten memahami kebutuhan Anda',
    promptPlaceholder: 'Contoh: Anda adalah asisten penulisan profesional. Jawablah secara ringkas dan profesional...',
    chars: '{count} karakter', quickTemplates: 'Template cepat', temperature: 'Temperatur LLM', temperatureDesc: 'Sesuaikan kreativitas dan keacakan AI',
    precise: 'Tepat (0-0,33)', preciseDesc: 'Lebih deterministik dan konsisten; cocok untuk tugas faktual', balanced: 'Seimbang (0,33-0,67)',
    balancedDesc: 'Menyeimbangkan akurasi dan kreativitas untuk kebanyakan tugas', creative: 'Kreatif (0,67-1)', creativeDesc: 'Lebih bervariasi dan imajinatif; cocok untuk brainstorming',
    clearConfirm: 'Kosongkan instruksi kustom?', overwriteConfirm: 'Menerapkan template akan mengganti instruksi saat ini. Lanjutkan?',
    templates: {
      academicName: 'Penulisan akademik', academicDesc: 'Gaya akademik formal dan ketat', academicPrompt: 'Anda adalah asisten penulisan akademik profesional. Gunakan bahasa formal, ketat, dengan logika jelas dan terminologi akurat.',
      creativeName: 'Penulisan kreatif', creativeDesc: 'Gaya kreatif imajinatif', creativePrompt: 'Anda adalah asisten penulisan kreatif. Gunakan bahasa hidup dan dorong ide serta perspektif orisinal.',
      businessName: 'Dokumen bisnis', businessDesc: 'Gaya bisnis ringkas dan profesional', creativePrompt: 'Anda adalah asisten penulisan bisnis profesional. Hasilkan dokumen, laporan, dan email yang jelas, ringkas, dan poin pentingnya menonjol.',
      casualName: 'Komunikasi sehari-hari', casualDesc: 'Gaya santai dan ramah', casualPrompt: 'Anda adalah asisten penulisan yang ramah dan mudah didekati. Gunakan bahasa alami, santai, dan mudah dibaca.'
    }
  },
  data: {
    title: 'Manajemen data', subtitle: 'Kelola data dan penyimpanan aplikasi', cache: 'Kosongkan cache', clearCache: 'Kosongkan cache',
    cacheDesc: 'Hapus file cache dari project/temp dan project/uploads untuk membebaskan ruang disk', clearCacheDesc: 'Hapus file cache dari project/temp dan project/uploads untuk membebaskan ruang disk',
    cacheLocation: 'Lokasi cache', cacheSize: 'Ukuran cache', scan: 'Pindai cache', scanning: 'Memindai...', clear: 'Kosongkan cache', clearing: 'Mengosongkan...',
    memory: 'Memori jangka panjang', memoryDesc: 'Kelola memori AI persisten, dari yang paling lama ke yang paling baru', enableMemory: 'Aktifkan memori jangka panjang',
    memoryPlaceholder: 'Memori AI jangka panjang muncul di sini. Anda dapat mengedit dan menyimpannya...', memoryHint: 'Memori berurutan; entri terbaru ada di bagian bawah.',
    reload: 'Muat ulang', saveMemory: 'Simpan memori', deleteAll: 'Hapus semua data', deleteAllDesc: 'Hapus semua riwayat obrolan dan data cache aplikasi',
    irreversible: 'Peringatan: tindakan ini tidak bisa dibatalkan', warning: 'Peringatan: tindakan ini tidak bisa dibatalkan', deleteIncludes: 'Menghapus semua data akan menghapus:', chats: 'Semua riwayat obrolan',
    cachedDocs: 'Data dokumen cache', sessionState: 'Status sesi', confirmTitle: 'Hapus semua data?',
    confirmDesc: 'Ini akan menghapus semua data secara permanen, termasuk obrolan, cache, dan pengaturan. Tindakan ini tidak bisa dibatalkan.',
    confirmBody: 'Ini akan menghapus semua data secara permanen, termasuk obrolan, cache, dan pengaturan. Tindakan ini tidak bisa dibatalkan.', typeDelete: 'Ketik DELETE untuk konfirmasi:',
    typeDeletePlaceholder: 'Ketik DELETE', deletePlaceholder: 'Ketik DELETE', confirmDelete: 'Hapus permanen', deleting: 'Menghapus...', calculating: 'Menghitung...', noCache: 'Tidak ada cache',
    cacheSummary: '{size} ({count} file)', clearConfirm: 'Kosongkan semua file di direktori cache?', cleared: 'Berhasil mengosongkan {count} file cache',
    clearFailed: 'Gagal mengosongkan cache: {error}', deleted: 'Semua data telah dihapus.', deleteFailed: 'Gagal menghapus: {error}',
    memoryLoadFailed: 'Gagal memuat memori jangka panjang: {error}', memorySaved: 'Memori jangka panjang disimpan.', memorySaveFailed: 'Gagal menyimpan memori jangka panjang: {error}',
    memoryToggled: 'Memori jangka panjang {state}', memoryEnabled: 'diaktifkan', memoryDisabled: 'dinonaktifkan',
    toggleFailed: 'Gagal menyimpan pengaturan memori: {error}'
  },
  session: {
    title: 'Riwayat obrolan', newChat: 'Obrolan baru', empty: 'Tidak ada riwayat obrolan', newConversation: 'Percakapan baru', noMessages: 'Tidak ada pesan',
    rename: 'Ganti nama', renameTitle: 'Ganti nama percakapan', renamePlaceholder: 'Masukkan nama baru', deleteTitle: 'Hapus percakapan',
    deleteBody: 'Hapus percakapan ini? Tindakan ini tidak bisa dibatalkan.'
  },
  chat: {
    attachment: 'Lampiran', removeFile: 'Hapus file', chars: '{count} karakter', clearSelection: 'Kosongkan pilihan',
    allowThinking: 'Pemikiran aktif', disableThinking: 'Pemikiran nonaktif', thinkingToggle: 'Aktifkan atau nonaktifkan pemikiran mendalam',
    addFile: 'Tambah file', addSelection: 'Tambah pilihan', send: 'Kirim', stop: 'Berhenti',
    agentPlaceholder: 'Jelaskan apa yang ingin dibuat selanjutnya', askPlaceholder: 'Masukkan pertanyaan',
    chooseModel: 'Pilih model', deleteParagraphs: 'menghapus {count} paragraf', aiOperation: 'Revisi AI: {actions} (menunggu konfirmasi)', revisionCount: '{count} perubahan',
    acceptRevision: 'Terima', rejectRevision: 'Tolak',
    context: 'Konteks: {current}k / {max}k token ({percentage}%)', unnamedFile: 'File tanpa nama',
    unsupportedFiles: 'File tidak didukung: {files}. Format yang didukung: png, jpg, jpeg, pdf, docx, txt, md.',
    paragraphRange: 'Paragraf {start} - {end}', showHistory: 'Tampilkan riwayat obrolan', whatCanIDo: 'Apa yang bisa saya lakukan?',
    documentation: 'Dokumentasi', selectionRef: 'Pilihan yang direferensikan ({count})', fileRef: 'File yang direferensikan ({count})',
    unknownFile: 'File tidak diketahui', preparing: 'AI sedang menyiapkan', thinking: 'Pemikiran mendalam', thinkingDone: 'Pemikiran mendalam (selesai)',
    contextCompactionStarted: '🗜️ Mengompresi konteks secara otomatis', contextCompactionCompleted: '✅ Kompresi konteks selesai',
    collapseMcp: 'Sembunyikan detail MCP', expandMcp: 'Tampilkan detail MCP', callMcp: 'Memanggil alat MCP: {name}',
    arguments: 'Argumen:', noArguments: 'Tidak ada argumen', toolOutput: 'Output alat:', noOutput: '(Tidak ada output)',
    outputDocument: 'Sisipkan ke dokumen', copyImage: 'Salin gambar', saveImage: 'Simpan gambar', selection: 'Pilihan',
    copyImageFailed: 'Gagal menyalin. Coba simpan gambar dari menu konteksnya.',
    mcpWaiting: 'Menunggu output alat...', unknownArguments: 'Argumen tidak tersedia', imageTableSelection: '[Pilihan gambar dan tabel]',
    imageSelection: '[Pilihan gambar]', tableSelection: '[Pilihan tabel]', networkTimeout: 'Koneksi jaringan timeout dan telah ditutup.',
    networkError: 'Kesalahan jaringan: {error}. Pastikan layanan backend berjalan di localhost:3880.',
    networkInterruptedReconnecting: 'Koneksi terputus dan permintaan ini gagal. Menghubungkan kembali secara otomatis; kirim ulang sebentar lagi.',
    readingDocumentById: 'Membaca dokumen (ID paragraf {start} - {end})',
    readingDocument: 'Membaca dokumen (paragraf {start} - {end})', searchingDocument: 'Mencari dokumen...',
    generatingDocument: 'Menghasilkan dokumen', documentInsertFailed: 'Gagal menyisipkan dokumen. Periksa posisi target dan izin dokumen.',
    deletePreview: 'Hapus {ids}', generatedPending: 'dihasilkan {summary}',
    wpsUnavailable: 'API WPS tidak tersedia', openDocumentFirst: 'Buka dokumen Word terlebih dahulu', messageMissing: 'Pesan tidak ditemukan',
    undoFailed: 'Gagal membatalkan: {error}', selectionUnavailable: 'Tidak dapat membaca pilihan. Pilih konten di WPS Writer terlebih dahulu.',
    selectionRangeUnavailable: 'Tidak dapat menentukan rentang pilihan', selectContentFirst: 'Pilih teks, gambar, atau tabel di dokumen terlebih dahulu.',
    selectionFailed: 'Tidak dapat memproses konten yang dipilih: {error}', insertFailed: 'Gagal menyisipkan. Pastikan dokumen Word terbuka.', unnamedDocument: 'Dokumen tanpa nama',
    searchComplete: 'Pencarian selesai', documentReadComplete: 'Pembacaan dokumen selesai', prepareDelete: 'Menerapkan penghapusan terlacak ke ID paragraf ({ids})',
    deleteComplete: 'Penghapusan selesai', insertBreakSuccess: 'Pemisah dokumen disisipkan', insertBreakFailed: 'Gagal menyisipkan pemisah dokumen: {error}', createDocumentPending: '📄 Membuat dokumen DOCX kosong baru', createDocumentSuccess: '📄 Dokumen DOCX kosong baru dibuat dan dibuka', createDocumentFailed: 'Gagal membuat dokumen DOCX baru: {error}', documentGenerated: 'Dokumen dihasilkan', errorLabel: 'Kesalahan: {error}',
    paragraphCount: '{count} paragraf', tableCount: '{count} tabel', summarySeparator: ', ', actionSeparator: ', ', pendingAddition: 'Menunggu penambahan',
    input: {
      attachment: 'Lampiran', removeFile: 'Hapus file', paragraphRange: 'Paragraf {start} - {end}', clearSelection: 'Kosongkan pilihan',
      confirm: 'Konfirmasi', cancel: 'Batal', modelsLoading: 'Memuat...', thinkingAria: 'Aktifkan atau nonaktifkan pemikiran mendalam',
      thinkingOn: 'Pemikiran aktif', thinkingOff: 'Pemikiran nonaktif', addFile: 'Tambah file', addSelection: 'Tambah pilihan', send: 'Kirim', stop: 'Berhenti',
      agentPlaceholder: 'Jelaskan apa yang ingin dibuat selanjutnya', askPlaceholder: 'Masukkan pertanyaan',
      chooseModel: 'Pilih model', deleteParagraphs: 'menghapus {count} paragraf', aiOperation: 'Revisi AI: {actions} (menunggu konfirmasi)',
      context: 'Konteks: {current}k / {max}k token ({percentage}%)', unnamedFile: 'File tanpa nama', unsupportedFiles: 'File tidak didukung: {files}. Format yang didukung: png, jpg, pdf, docx, txt, md.'
    },
    messages: {
      showHistory: 'Tampilkan riwayat obrolan', empty: 'Apa yang bisa saya lakukan?', docs: 'Dokumentasi', selections: 'Pilihan yang direferensikan ({count})',
      files: 'File yang direferensikan ({count})', unknownFile: 'File tidak diketahui', preparing: 'AI sedang menyiapkan', thinking: 'Pemikiran mendalam',
      thinkingDone: 'Pemikiran mendalam (selesai)', collapseMcp: 'Sembunyikan detail MCP', expandMcp: 'Tampilkan detail MCP',
      mcpCall: 'Memanggil alat MCP: {name}', parameters: 'Parameter:', noParameters: 'Tidak ada parameter', output: 'Output alat:', noOutput: '(Tidak ada output)',
      copy: 'Salin', insert: 'Sisipkan ke Word', retry: 'Coba lagi', undo: 'Batal'
    },
    session: {
      newChat: 'Obrolan baru', title: 'Riwayat obrolan', empty: 'Tidak ada riwayat obrolan', rename: 'Ganti nama', delete: 'Hapus',
      renameTitle: 'Ganti nama percakapan', renamePlaceholder: 'Masukkan nama percakapan', deleteTitle: 'Hapus percakapan',
      deleteConfirm: 'Hapus percakapan ini? Tindakan ini tidak bisa dibatalkan.'
    }
  },
  about: {
    name: '文策AI', product: '文策AI', version: 'Versi', pluginType: 'Jenis add-in', wpsPlugin: 'Add-in WPS Writer', wordPlugin: 'Add-in Microsoft Word',
    developer: 'Pengembang', developerName: 'Riyue Xingchen', links: 'Tautan', repository: 'Repositori GitHub', website: 'Situs proyek',
    docs: 'Dokumentasi', issues: 'Laporkan masalah', sponsor: 'Sponsor pengembang', github: 'Repositori GitHub', unknownVersion: 'Versi tidak diketahui'
  },
  debug: {
    title: 'Panel debug', hint: 'Tekan F12 untuk membuka developer tools', parse: 'Parse konten dokumen', parseSelection: 'Parse pilihan',
    showDocuments: 'Tampilkan nama file yang terbuka', openDocuments: 'Dokumen terbuka ({count})', deleteParagraphs: 'Hapus paragraf berdasarkan indeks',
    deletePlaceholder: 'Masukkan indeks paragraf awal dan akhir (0-based), contoh: 3, 7', clear: 'Kosongkan', jsonToDoc: 'JSON ke dokumen',
    jsonPlaceholder: 'Tempel JSON di sini...', apply: 'Terapkan ke dokumen', export: 'Ekspor', copy: 'Salin ke clipboard',
    download: 'Unduh JSON', deleteAction: 'Hapus paragraf', result: 'Hasil parse:', paragraphs: 'Paragraf: {count}', tables: 'Tabel: {count}', images: 'Gambar: {count}', chars: 'Karakter: {count}'
  }
};
