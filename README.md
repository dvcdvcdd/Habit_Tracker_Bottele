# Habit Tracker Telegram Bot

Bot Telegram untuk membangun kebiasaan harian secara konsisten.
Kelola habit, pantau streak, dan terima reminder — semuanya dari dalam Telegram.

---

## Fitur

### Manajemen Habit
- Tambah habit baru dengan jadwal fleksibel
- Edit nama dan jadwal habit
- Jeda habit sementara tanpa merusak streak
- Hapus habit (soft delete, data check-in tetap aman)
- Lihat daftar semua habit dengan status hari ini

### Check-in Harian
- Check-in cukup dengan satu ketukan tombol
- Progress bar harian
- Streak dihitung otomatis per habit
- Pesan milestone di hari ke-7, 14, 21, 30, dan seterusnya

### Jadwal Fleksibel
- Setiap hari
- Senin – Jumat (weekday)
- Senin, Rabu, Jumat
- Selasa, Kamis, Sabtu
- Sabtu & Minggu (weekend)

### Statistik & Laporan
- Statistik harian dan mingguan
- Ringkasan harian otomatis (daily summary)
- Laporan mingguan otomatis setiap Minggu
- Riwayat check-in 30 hari dalam format kalender

### Reminder & Motivasi
- Reminder harian otomatis (jam bisa diubah per user)
- Pesan motivasi kontekstual (berbeda pagi/malam)
- Comeback mode saat user kembali setelah beberapa hari tidak aktif

### Profile
- Lihat profile dan ringkasan statistik
- Ubah jam reminder personal
- Total check-in, hari aktif, streak terpanjang

### Keamanan & Stabilitas
- Error handler global
- Rate limiter (anti spam)
- Logging ke file (`bot.log` dan `bot_error.log`)
- Validasi input yang ketat
- Graceful shutdown

---

## Tech Stack

| Teknologi | Fungsi |
|-----------|--------|
| Python 3.11+ | Bahasa pemrograman utama |
| aiogram v3 | Framework Telegram bot berbasis async |
| SQLite | Database ringan |
| aiosqlite | Akses database async |
| APScheduler | Reminder dan task terjadwal |
| python-dotenv | Manajemen environment variable |

---

## Struktur Project

```text
habit_tracker_bot/
│
├── app/
│   ├── __init__.py
│   ├── bot.py                 # Entry point: setup bot, middleware, scheduler
│   ├── config.py              # Konfigurasi dari environment variable
│   │
│   ├── handlers/              # Layer presentasi (menerima update dari Telegram)
│   │   ├── start.py           # /start, /menu, /help, onboarding
│   │   ├── checkin.py         # Check-in harian
│   │   ├── habits.py          # Tambah habit (FSM multi-langkah)
│   │   ├── habit_edit.py      # Detail, riwayat, edit, jeda, hapus habit
│   │   ├── stats.py           # Statistik harian & mingguan
│   │   ├── summary.py         # Ringkasan harian
│   │   └── profile.py         # Profile & ubah jam reminder
│   │
│   ├── keyboards/             # Inline & reply keyboard
│   │
│   ├── middlewares/           # Logging, rate limiter, error handler
│   │
│   ├── services/              # Logika bisnis
│   │   ├── habit_service.py   # CRUD habit & check-in
│   │   ├── streak_service.py  # Perhitungan streak
│   │   ├── stats_service.py   # Statistik & ringkasan
│   │   ├── motivation_service.py  # Pesan motivasi kontekstual
│   │   └── reminder_service.py    # Scheduler & broadcast
│   │
│   ├── database/              # Akses data (SQLite + aiosqlite)
│   │
│   └── utils/                 # Helper tanggal, validasi, formatting
│
├── logs/                      # File log berjalan
├── data/                      # Database SQLite (dibuat otomatis)
├── .env                       # Konfigurasi lokal (tidak di-commit)
├── requirements.txt
└── README.md
```

---

## Cara Menjalankan

### 1. Buat bot di Telegram

1. Buka [@BotFather](https://t.me/BotFather)
2. Kirim `/newbot` dan ikuti instruksinya
3. Salin token bot yang diberikan

### 2. Siapkan environment

```bash
cp .env.example .env
# isi BOT_TOKEN dengan token dari BotFather
```

### 3. Install dependency

```bash
pip install -r requirements.txt
```

### 4. Jalankan bot

```bash
python -m app.bot
```

Log tersimpan di folder `logs/`.

---

## Konfigurasi (.env)

| Variabel | Default | Keterangan |
|----------|---------|------------|
| `BOT_TOKEN` | - | Token bot dari BotFather (wajib) |
| `DB_PATH` | `data/habits.db` | Lokasi file database SQLite |
| `TIMEZONE` | `Asia/Jakarta` | Zona waktu bot |
| `REMINDER_TIME` | `19:00` | Jam reminder harian default |
| `COMEBACK_THRESHOLD` | `2` | Hari tidak aktif sebelum mode comeback aktif |

---

## Perintah Bot

Bot memiliki menu perintah resmi (muncul otomatis di kolom input Telegram):

| Perintah | Fungsi |
|----------|--------|
| `/start` | Buka menu utama |
| `/checkin` | Check-in hari ini |
| `/habits` | Daftar habit |
| `/statistik` | Statistik harian dan mingguan |
| `/summary` | Ringkasan hari ini |
| `/profile` | Profile dan pengaturan |
| `/help` | Bantuan |

---

## Bahasa Visual

Bot menggunakan sistem simbol teks monokrom (bukan emoji) agar tampil
konsisten, modern, dan profesional di semua perangkat:

| Simbol | Makna |
|--------|-------|
| `[x]` | Habit sudah di-check-in |
| `[ ]` | Habit belum di-check-in |
| `[·]` | Habit tidak dijadwalkan hari ini / dijeda |
| `█` `░` | Progress bar |
| `■` `□` `·` | Kalender riwayat 30 hari |

Semua pesan dikirim dengan HTML parse mode dan input user di-escape,
sehingga aman dari karakter yang merusak format.

---

## Jadwal Otomatis (Scheduler)

| Task | Waktu | Fungsi |
|------|-------|--------|
| Morning reset | 00:05 | Reset streak yang terputus |
| Daily reminder | sesuai `REMINDER_TIME` | Ingatkan check-in yang belum selesai |
| Daily summary | 21:00 | Kirim ringkasan harian |
| Weekly report | Minggu 20:00 | Kirim laporan mingguan |

---

## Roadmap (Ide Pengembangan)

- Custom schedule (pilih hari bebas per habit)
- Target & pengingat streak (misal: "3 hari lagi mencapai 30 hari")
- Ekspor riwayat (CSV / JSON)
- Mode gelap-friendly layout & opsi bahasa
- Webhook deployment (bukan long polling)
- Multi-bahasa (i18n)

---

Dikembangkan dengan Python, aiogram v3, dan SQLite.
Dokumentasi arsitektur lengkap: [ARSITEKTUR_SISTEM.md](ARSITEKTUR_SISTEM.md)
