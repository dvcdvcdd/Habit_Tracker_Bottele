# 🎯 Habit Tracker Telegram Bot

Bot Telegram untuk membantu membangun konsistensi kebiasaan harian.
Track habit, pantau streak, dan tetap konsisten setiap hari.

---

## ✨ Fitur

### Manajemen Habit
- ➕ Tambah habit baru dengan jadwal fleksibel
- ✏️ Edit nama dan jadwal habit
- ⏸ Pause habit sementara tanpa merusak streak
- 🗑 Hapus habit (soft delete, data checkin tetap aman)
- 📋 Lihat daftar semua habit dengan status hari ini

### Check-in Harian
- ✅ Check-in habit dengan satu kali tekan tombol
- 📊 Progress bar harian
- 🔥 Streak otomatis dihitung per habit
- 🎉 Pesan milestone saat streak mencapai 7, 14, 21, 30 hari dst

### Jadwal Fleksibel
- 📅 Setiap hari
- 💼 Senin – Jumat (weekday)
- 🔄 Senin, Rabu, Jumat
- 🔄 Selasa, Kamis, Sabtu
- 🎉 Sabtu & Minggu (weekend)

### Statistik & Laporan
- 📊 Statistik harian dan mingguan
- 📝 Daily summary
- 📋 Weekly report otomatis setiap Minggu
- 📅 Riwayat check-in 30 hari dalam format kalender visual

### Reminder & Motivasi
- ⏰ Reminder harian otomatis (jam bisa diubah per user)
- 💬 Pesan motivasi kontekstual (berbeda pagi/malam)
- 👋 Comeback mode saat user baru kembali setelah bolong

### Profile
- 👤 Lihat profile dan ringkasan statistik
- ⏰ Ubah jam reminder personal
- 📊 Total check-in, hari aktif, streak terpanjang

### Keamanan & Stabilitas
- 🛡 Error handler global
- 🚦 Rate limiter (anti spam)
- 📝 Logging ke file (bot.log dan bot_error.log)
- ✅ Validasi input yang ketat
- 🔄 Graceful shutdown

---

## 🛠 Tech Stack

| Teknologi | Fungsi |
|-----------|--------|
| Python 3.11+ | Bahasa pemrograman utama |
| aiogram v3 | Framework Telegram bot (async) |
| SQLite | Database ringan |
| aiosqlite | Akses database async |
| APScheduler | Reminder dan task terjadwal |
| python-dotenv | Manajemen environment variable |

---

## 📁 Struktur Project
habit_tracker_bot/
│
├── app/
│ ├── init.py
│ ├── bot.py # Entry point utama
│ ├── config.py # Konfigurasi dari .env
│ │
│ ├── handlers/
│ │ ├── init.py
│ │ ├── start.py # /start, /menu, /help
│ │ ├── habits.py # Tambah habit
│ │ ├── habit_edit.py # Edit, pause, hapus, riwayat
│ │ ├── checkin.py # Check-in harian
│ │ ├── stats.py # Statistik
│ │ ├── summary.py # Daily summary
│ │ └── profile.py # Profile & pengaturan
│ │
│ ├── keyboards/
│ │ ├── init.py
│ │ ├── inline.py # Semua inline keyboard
│ │ └── reply.py # Reply keyboard
│ │
│ ├── services/
│ │ ├── init.py
│ │ ├── habit_service.py # Logika bisnis habit
│ │ ├── streak_service.py # Kalkulasi streak
│ │ ├── stats_service.py # Statistik & summary
│ │ ├── reminder_service.py # Scheduler & reminder
│ │ └── motivation_service.py # Pesan motivasi
│ │
│ ├── database/
│ │ ├── init.py
│ │ ├── init_db.py # Inisialisasi database
│ │ ├── queries.py # Semua query database
│ │ └── models.py # Struktur data
│ │
│ ├── middlewares/
│ │ ├── init.py
│ │ ├── error_handler.py # Error handler global
│ │ ├── rate_limiter.py # Rate limiter
│ │ └── logging_middleware.py # Logging aktivitas
│ │
│ └── utils/
│ ├── init.py
│ ├── dates.py # Fungsi tanggal & waktu
│ ├── enums.py # Konstanta & enum
│ └── helpers.py # Fungsi utilitas
│
├── data/
│ └── habits.db # Database SQLite (auto-generated)
│
├── logs/
│ ├── bot.log # Log semua aktivitas
│ └── bot_error.log # Log error saja
│
├── .env # Token bot (JANGAN commit)
├── .env.example # Contoh konfigurasi
├── .gitignore
├── requirements.txt
├── CHANGELOG.md
└── README.md


---

## 🚀 Cara Install & Menjalankan

### 1. Clone repository

```bash
git clone https://github.com/username/habit-tracker-bot.git
cd habit-tracker-bot

2. Buat virtual environment
python -m venv venv

aktifkan
# Windows PowerShell
venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat

# Mac/Linux
source venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

4. Buat bot di Telegram
  Buka Telegram, cari @BotFather
  Kirim /newbot
  Ikuti instruksi, dapatkan token
  Salin token
5. Konfigurasi environment
  cp .env.example .env
  Buka .env dan isi token:
  BOT_TOKEN=token_dari_botfather

6. Jalankan bot
  python -m app.bot

Bot siap! Buka Telegram dan kirim /start ke bot kamu.

⚙️ Konfigurasi
Semua konfigurasi ada di file .env:

Variable	Default	Keterangan
BOT_TOKEN	(wajib)	Token dari BotFather
TIMEZONE	Asia/Jakarta	Timezone bot
REMINDER_TIME	19:00	Jam reminder default
COMEBACK_THRESHOLD	2	Hari bolong sebelum comeback mode
📱 Command Bot
Command	Fungsi
/start	Buka menu utama
/menu	Kembali ke menu utama
/help	Tampilkan bantuan
/profile	Lihat profile
/statistik	Lihat statistik
/summary	Ringkasan hari ini
🕐 Jadwal Otomatis
Waktu	Aktivitas
00:05	Reset streak yang putus
19:00	Daily reminder (bisa diubah)
20:00 Minggu	Weekly report
21:00	Daily summary
