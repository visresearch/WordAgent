STRINGS = {
    "app": {"name": "WenCe AI"},
    "tray": {"show": "Tampilkan", "quit": "Keluar WenCe AI", "tooltip": "WenCe AI"},
    "nav": {
        "home": "Beranda",
        "dashboard": "Dasbor",
        "wps": "Add-in WPS",
        "office": "Add-in Office",
        "mcp": "Server MCP",
        "console": "Konsol",
    },
    "home": {
        "subtitle": "Penulisan strategis, ekspresi lebih cerdas",
        "status": {
            "runningChecking": "Layanan backend berjalan (memeriksa pembaruan)",
            "runningNoUpdateInfo": "Layanan backend berjalan (tidak dapat mengambil info pembaruan)",
            "runningLatest": "Layanan backend berjalan (versi terbaru)",
            "newVersion": "Versi baru tersedia: {tag}, silakan unduh dari situs web",
            "updateFailed": "Pemeriksaan pembaruan gagal",
        },
        "version": {"current": "Versi saat ini: {version}", "unknown": "Versi tidak diketahui"},
        "update": {
            "checking": "Memeriksa pembaruan...",
            "failed": "Pemeriksaan pembaruan gagal",
            "latest": "Versi terbaru",
            "new": "Versi baru: {tag}",
        },
        "button": {"github": "GitHub", "website": "Dokumentasi Situs", "downloadLatest": "Unduh Versi Terbaru"},
        "cards": {
            "crossPlatform": {
                "title": "Lintas Platform",
                "desc": "Dibangun untuk WPS dan Microsoft Word, mendukung Windows dan Linux untuk bantuan penulisan AI yang mudah diakses.",
            },
            "richText": {
                "title": "Rich Text Asli",
                "desc": "Agen memahami struktur dokumen Word, mendukung judul, isi, tebal, font, indentasi, spasi baris dan lainnya.",
            },
            "workflow": {
                "title": "Alur Kerja Berbasis Alat",
                "desc": "Selesaikan penulisan panjang, riset dan pengeditan kompleks melalui alat dokumen, MCP dan Skill.",
            },
            "open": {
                "title": "Terbuka & Fleksibel",
                "desc": "Mendukung API kustom atau layanan lokal, kompatibel dengan sebagian besar penyedia LLM utama.",
            },
        },
        "infobar": {
            "newVersion": {
                "title": "Versi Baru Tersedia",
                "content": "Versi terbaru {tag} terdeteksi, silakan unduh dari situs web.",
            }
        },
    },
    "dashboard": {
        "title": "Dasbor Penggunaan Token",
        "subtitle": "Statistik penggunaan token WenCe AI terbaru",
        "period": {"today": "Hari Ini", "7d": "7 Hari"},
        "metrics": {
            "inputTokens": "Token Input",
            "outputTokens": "Token Output",
            "cachedTokens": "Token Cache",
            "cacheHitRate": "Rasio Hit Cache",
        },
        "chart": {"trend": "Tren Penggunaan", "empty": "Tidak Ada Data Penggunaan Token"},
        "status": {
            "loading": "Memuat...",
            "hover": "Arahkan kursor ke grafik untuk detail",
            "empty": "Tidak ada catatan penggunaan",
            "failed": "Gagal memuat data, silakan coba lagi",
            "invalid": "Format data penggunaan token tidak valid",
        },
        "tooltip": {"input": "Input:", "output": "Output:", "cached": "Cache:"},
    },
    "console": {
        "title": "Konsol",
        "buttons": {"logDir": "Folder Log", "clear": "Bersihkan", "bottom": "Bawah"},
        "hint": "Menampilkan semua output log selama runtime aplikasi",
        "tooltips": {"logDir": "Buka folder log", "clear": "Bersihkan log", "bottom": "Gulir ke bawah"},
        "error": {"openLogDir": "Gagal membuka folder log"},
    },
    "wps": {"title": "Add-in WPS Word", "subtitle": "Kelola instalasi add-in WPS Office"},
    "office": {
        "title": "Add-in Microsoft Word",
        "subtitle": "Kelola instalasi add-in Microsoft Word web dan desktop",
        "usage": (
            "Instal sertifikat:<br/>"
            '1. Pastikan "Mulai Layanan HTTPS" berjalan. (Otomatis dimulai saat membuka halaman ini)<br/>'
            '2. Klik "Instal Sertifikat", lalu di dialog sistem: Instal Sertifikat -&gt; Mesin Lokal -&gt; Tempatkan semua sertifikat di penyimpanan berikut -&gt; Jelajahi -&gt; Otoritas Sertifikasi Root Tepercaya, lalu konfirmasi.<br/>'
            '3. Klik "Buka di Browser", jika tidak ada peringatan keamanan, sertifikat terpasang; jika masih ada peringatan, restart backend dan coba lagi. Jika masih gagal, instal manual atau hubungi penulis.<br/><br/>'
            "Versi web:<br/>"
            "1. Buka <a href='https://word.cloud.microsoft/' style='color: #2563eb; text-decoration: underline;'>https://word.cloud.microsoft/</a> dan masuk ke Word untuk web.<br/>"
            "2. Buka: Beranda -&gt; Add-in -&gt; Add-in Lainnya -&gt; Add-in Saya -&gt; Kelola Add-in Saya -&gt; Unggah Add-in Saya<br/>"
            "3. Unggah manifest.xml yang diunduh. Refresh jika panel add-in tidak muncul.<br/><br/>"
            "Versi desktop:<br/>"
            '1. Klik "Unduh manifest.xml" dan simpan ke folder kosong.<br/>'
            "2. Klik kanan folder -&gt; Properti -&gt; Berbagi -&gt; Bagikan -&gt; Everyone -&gt; Bagikan dan catat jalur jaringan.<br/>"
            "3. Buka Microsoft Word: File -&gt; Opsi -&gt; Pusat Kepercayaan -&gt; Pengaturan Pusat Kepercayaan -&gt; Katalog Add-in Tepercaya, masukkan jalur jaringan dan Tambah Katalog, restart Word.<br/>"
            "4. Jika panel tidak muncul: File -&gt; Opsi -&gt; Sesuaikan Pita, tambahkan Pengembang ke Tab Utama. Klik Pengembang -&gt; Add-in -&gt; Folder Bersama -&gt; Asisten WenCe AI.<br/><br/>"
            "【Panduan detail: <a href='https://visresearch.github.io/WordAgent/' style='color: #2563eb; text-decoration: underline;'>https://visresearch.github.io/WordAgent/</a>】"
        ),
        "buttons": {
            "download": "Unduh manifest.xml",
            "start": "Mulai Layanan HTTPS",
            "installCert": "Instal Sertifikat",
            "openBrowser": "Buka di Browser",
            "stop": "Hentikan Layanan",
        },
        "status": {
            "running": "Status layanan: Berjalan (https://{host}:{port})",
            "stopped": "Status layanan: Tidak berjalan",
        },
        "infobar": {
            "downloadFailed": {"title": "Gagal Unduh", "contentMissing": "gui/resources/manifest.xml tidak ditemukan"},
            "downloadSuccess": {"title": "Berhasil Diunduh", "content": "manifest.xml disimpan ke: {path}"},
            "openBrowser": {"title": "Dibuka di Browser"},
            "openBrowserFailed": {"title": "Gagal Membuka Browser"},
            "certOpened": {"title": "File Sertifikat Dibuka", "content": "Silakan ikuti petunjuk di halaman ini"},
            "certFailed": {"title": "Gagal membuka sertifikat, silakan cari dan instal manual, jalur: {path}"},
            "serviceRunning": {"title": "Pemberitahuan", "content": "Layanan HTTPS sudah berjalan"},
            "startFailed": {
                "title": "Gagal Memulai",
                "contentMissingDist": "microsoft_word_plugin/dist tidak ditemukan, silakan build frontend terlebih dahulu",
            },
            "startSuccess": {"title": "Berhasil Dimulai", "content": "Layanan HTTPS dimulai: https://{host}:{port}"},
            "stopped": {"title": "Dihentikan", "content": "Layanan HTTPS dihentikan"},
            "stopFailed": {"title": "Gagal Menghentikan"},
            "notRunning": {"title": "Pemberitahuan", "content": "Layanan HTTPS tidak berjalan"},
        },
        "dialog": {"saveManifest": "Simpan manifest.xml", "xmlFilter": "File XML (*.xml)"},
    },
    "mcp": {
        "title": "Server MCP",
        "subtitle": "Izinkan klien seperti Codex memakai alat dokumen WPS / Microsoft Word yang sedang dibuka",
        "endpoint": "Alamat koneksi: {url}",
        "running": "Server berjalan",
        "stopped": "Server berhenti",
        "backendUnavailable": "Layanan backend belum siap",
        "start": "Jalankan",
        "stop": "Hentikan",
        "startFailed": "Gagal menjalankan server MCP",
        "clients": "Klien aktif baru-baru ini ({count})",
        "client": "{name} · permintaan {seconds} detik lalu",
        "noClients": "Belum ada klien aktif",
        "activityHint": "Server ini memakai HTTP stateless. Klien ditampilkan selama 2 menit setelah permintaan; status aplikasi klien tidak dapat diketahui secara tepat. Buka panel add-in WPS / Microsoft Word untuk memakai alat dokumen.",
        "configTitle": "Konfigurasi JSON MCP",
    },
    "language": {
        "label": "Bahasa",
        "english": "English",
        "chinese": "简体中文",
        "indonesian": "Bahasa Indonesia",
        "japanese": "Bahasa Jepang",
        "korean": "Bahasa Korea",
        "vietnamese": "Bahasa Vietnam",
    },
    "common": {"unknownVersion": "Versi tidak diketahui", "save": "Simpan", "cancel": "Batal"},
}
