# Dokumentasi Arsitektur Habit Tracker Bot

Dokumen ini berisi penjelasan lengkap mengenai arsitektur sistem, alur bisnis, struktur folder, dan relasi antar modul pada proyek Habit Tracker Telegram Bot.

## 1. Arsitektur Sistem

Habit Tracker Bot dibangun dengan menggunakan pendekatan **Layered Architecture** (Arsitektur Berlapis) yang memisahkan antara penerima pesan, logika bisnis, dan akses data. Bot ini dirancang agar asinkronous menggunakan framework `aiogram`.

**Teknologi Utama:**
- **Bahasa Pemrograman:** Python 3.11+
- **Framework Bot:** `aiogram` v3 (berbasis *async*)
- **Database:** SQLite dengan `aiosqlite` untuk akses database secara asinkron.
- **Task Scheduler:** `APScheduler` untuk mengelola penjadwalan seperti *daily reminder*, *daily summary*, dan *weekly report*.
- **Konfigurasi:** Manajemen environment variables menggunakan `python-dotenv`.

**Lapisan Arsitektur:**
1. **Presentation Layer (Handlers & Keyboards):** Bertanggung jawab menerima *update* (pesan atau callback query) dari Telegram dan mengirimkan balasan.
2. **Business Logic Layer (Services):** Memproses aturan bisnis seperti menghitung *streak* berjalan, mengelola penjadwalan *habit*, dan menyajikan statistik harian/mingguan.
3. **Data Access Layer (Database):** Mengelola skema tabel, *models*, dan operasi query ke SQLite.
4. **Cross-Cutting Concerns (Middlewares & Utils):** Menangani *rate-limiting*, *error handling*, *logging*, serta fungsi utilitas tanggal dan waktu global.

---

## 2. Alur Bisnis (Business Flow)

### a. Alur Masuk Pesan & Middleware
1. User mengirim pesan (contoh: `/start`) atau menekan tombol (*Inline Keyboard* / *Reply Keyboard*).
2. Pesan diterima oleh dispatcher bot.
3. Pesan akan melewati kumpulan **Middleware**:
   - `LoggingMiddleware`: Mencatat aktivitas pesan.
   - `RateLimiterMiddleware`: Mencegah *spam* berlebihan dari satu user (anti-spam).
   - `ErrorHandlerMiddleware`: Menangkap *exception* secara global agar bot tidak *crash*.
4. Jika diizinkan oleh middleware, *update* diteruskan ke **Handler** yang sesuai.

### b. Alur Check-in Habit Harian
1. User mengklik tombol "Check-in" di *inline keyboard*.
2. Telegram mengirimkan `CallbackQuery` ke `checkin.py` (Handler).
3. Handler memanggil `app.services.habit_service` dan `app.services.streak_service`.
4. Service memeriksa apakah habit sudah di-check-in pada hari tersebut.
   - Jika *belum*: Tambahkan *record* check-in baru di database, hitung ulang *current streak* dan *longest streak*, dan berikan balasan motivasi acak dari `motivation_service`.
   - Jika *sudah*: Kembalikan informasi bahwa habit sudah tuntas hari ini.
5. Menampilkan hasil balasan lewat Telegram ke user.

### c. Penjadwalan Latar Belakang (Background Tasks)
1. Pada `bot.py`, `APScheduler` diinisialisasi.
2. Membaca fungsi dari `reminder_service.py` untuk mendaftarkan tugas harian dan mingguan.
3. Secara berkala, *scheduler* mengeksekusi job (misal: mengirimkan rekap jam 21:00) yang membaca data *check-in* hari itu dan memberikan notifikasi ke masing-masing pengguna aktif.

---

## 3. Struktur Folder

Berikut adalah representasi utama dari struktur *codebase* beserta fungsinya:

```text
.
├── app/
│   ├── bot.py                  # Entry point aplikasi bot (inisialisasi aiogram & scheduler)
│   ├── config.py               # Konfigurasi dari environment variables (membaca .env)
│   │
│   ├── database/               # Modul terkait database SQLite
│   │   ├── init_db.py          # Inisialisasi koneksi & pembuatan tabel
│   │   ├── models.py           # Data classes untuk entitas (User, Habit, CheckIn)
│   │   └── queries.py          # Fungsi-fungsi query SQL yang akan dipanggil Service
│   │
│   ├── handlers/               # Router dan controller bot
│   │   ├── checkin.py          # Handler untuk aksi check-in
│   │   ├── habit_edit.py       # Handler edit nama dan jadwal habit
│   │   ├── habits.py           # Handler melihat dan menambah habit
│   │   ├── profile.py          # Handler melihat/edit profile dan reminder time
│   │   ├── start.py            # Handler menyambut /start dan /menu
│   │   ├── stats.py            # Handler untuk statistik kalender/30 hari
│   │   └── summary.py          # Handler untuk ringkasan progres
│   │
│   ├── keyboards/              # Definisi layout tombol Telegram (Reply & Inline)
│   │   ├── inline.py
│   │   └── reply.py
│   │
│   ├── middlewares/            # Middleware yang menyaring traffic ke bot
│   │   ├── error_handler.py    # Mencegah crash & log error
│   │   ├── logging_middleware.py # Audit log input user
│   │   └── rate_limiter.py     # Throttling
│   │
│   ├── services/               # Logika bisnis dan layanan internal
│   │   ├── habit_service.py    # Operasi CRUD Habit
│   │   ├── motivation_service.py # Mendapatkan teks-teks motivasi
│   │   ├── reminder_service.py # Logika background tasks
│   │   ├── stats_service.py    # Logika agregasi statistik & perhitungan
│   │   └── streak_service.py   # Perhitungan streak saat ini / putus / longest
│   │
│   └── utils/                  # Fungsi bantu universal
│       ├── dates.py            # Fungsi parsing zona waktu & string
│       ├── enums.py            # Enumeration global
│       └── helpers.py          # Fungsi format text markdown
│
├── logs/                       # Folder yang dibuat otomatis menyimpan bot.log dan bot_error.log
├── .env.example
├── .gitignore
├── README.md                   # Spesifikasi bot dan cara setup
└── requirements.txt            # Dependensi pip
```

---

## 4. Relasi Antar Modul

Modul-modul dirancang agar longgar (*loosely coupled*) dan menerapkan *separation of concerns*:

- **`app.bot`** adalah **Orkestrator Utama**. Modul ini memanggil dan mendaftarkan `middlewares`, router dari `handlers`, dan *jobs* dari `services/reminder_service`.
- **`app.handlers` -> `app.services`**: Handlers tidak disarankan menulis SQL mentah secara langsung, sebaliknya handler bertugas mengurai pesan user dan melempar *data parameter* ke *service layer*.
- **`app.services` -> `app.database.queries`**: Semua *service layer* akan memanfaatkan fungsi di `queries.py` untuk menyimpan ke / mengambil dari *database*.
- **`app.services.streak_service`**: Relasi krusial dengan tabel *check-in* dan *habit*, berfungsi membandingkan tanggal log *check-in* terakhir, dan menambah/mereset *current streak* pada tabel *habit*.
- **`app.database.init_db`**: Dipanggil pada saat inisialisasi di `app.bot`. Menyediakan *context manager* koneksi database ke seluruh aplikasi.
- **`app.handlers` -> `app.keyboards`**: Handlers menggunakan `keyboards` untuk memformat balasan yang membutuhkan tombol agar user tidak perlu mengetik panjang-panjang.

Secara keseluruhan, arsitektur ini memungkinkan pengembangan fitur-fitur lanjutan tanpa harus merombak struktur utama, seperti penambahan opsi penjadwalan kompleks di masa depan.
