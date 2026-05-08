# 🎯 Habit Tracker Telegram Bot

Bot Telegram untuk membantu membangun konsistensi kebiasaan harian.  
Track habit, pantau streak, dan tetap konsisten setiap hari.

---

## ✨ Fitur

### Manajemen Habit
- ➕ Tambah habit baru dengan jadwal fleksibel
- ✏️ Edit nama dan jadwal habit
- ⏸ Pause habit sementara tanpa merusak streak
- 🗑 Hapus habit (soft delete, data check-in tetap aman)
- 📋 Lihat daftar semua habit dengan status hari ini

### Check-in Harian
- ✅ Check-in habit dengan satu kali tekan tombol
- 📊 Progress bar harian
- 🔥 Streak otomatis dihitung per habit
- 🎉 Pesan milestone saat streak mencapai 7, 14, 21, 30 hari, dan seterusnya

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
- 📝 Logging ke file (`bot.log` dan `bot_error.log`)
- ✅ Validasi input yang ketat
- 🔄 Graceful shutdown

---

## 🛠 Tech Stack

| Teknologi | Fungsi |
|-----------|--------|
| Python 3.11+ | Bahasa pemrograman utama |
| aiogram v3 | Framework Telegram bot berbasis async |
| SQLite | Database ringan |
| aiosqlite | Akses database async |
| APScheduler | Reminder dan task terjadwal |
| python-dotenv | Manajemen environment variable |

---

## 📁 Struktur Project

```text
habit_tracker_bot/
│
├── app/
│   ├── __init__.py
│   ├── bot.py
│   ├── config.py
│   │
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py
│   │   ├── habits.py
│   │   ├── habit_edit.py
│   │   ├── checkin.py
│   │   ├── stats.py
│   │   ├── summary.py
│   │   └── profile.py
│   │
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── inline.py
│   │   └── reply.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── habit_service.py
│   │   ├── streak_service.py
│   │   ├── stats_service.py
│   │   ├── reminder_service.py
│   │   └── motivation_service.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── init_db.py
│   │   ├── queries.py
│   │   └── models.py
│   │
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── error_handler.py
│   │   ├── rate_limiter.py
│   │   └── logging_middleware.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── dates.py
│       ├── enums.py
│       └── helpers.py
│
├── data/
│   └── habits.db
│
├── logs/
│   ├── bot.log
│   └── bot_error.log
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

---

## 🚀 Cara Install dan Menjalankan

### 1. Clone repository

```bash
git clone https://github.com/username/habit-tracker-bot.git
cd habit-tracker-bot
```

### 2. Buat virtual environment

```bash
python -m venv venv
```

### 3. Aktifkan virtual environment

**Windows PowerShell**
```bash
venv\Scripts\Activate.ps1
```

**Windows CMD**
```bash
venv\Scripts\activate.bat
```

**Mac/Linux**
```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Buat bot di Telegram

1. Buka Telegram
2. Cari `@BotFather`
3. Kirim `/newbot`
4. Ikuti instruksi sampai mendapatkan token
5. Salin token bot

### 6. Konfigurasi environment

Salin file contoh:

```bash
cp .env.example .env
```

Lalu buka file `.env` dan isi token:

```env
BOT_TOKEN=token_dari_botfather
```

### 7. Jalankan bot

```bash
python -m app.bot
```

Bot siap. Buka Telegram dan kirim `/start` ke bot kamu.

---

## ⚙️ Konfigurasi

Semua konfigurasi ada di file `.env`.

| Variable | Default | Keterangan |
|----------|---------|------------|
| `BOT_TOKEN` | wajib diisi | Token dari BotFather |
| `TIMEZONE` | `Asia/Jakarta` | Timezone bot |
| `REMINDER_TIME` | `19:00` | Jam reminder default |
| `COMEBACK_THRESHOLD` | `2` | Hari bolong sebelum comeback mode aktif |

---

## 📱 Command Bot

| Command | Fungsi |
|---------|--------|
| `/start` | Buka menu utama |
| `/menu` | Kembali ke menu utama |
| `/help` | Tampilkan bantuan |
| `/profile` | Lihat profile |
| `/statistik` | Lihat statistik |
| `/summary` | Ringkasan hari ini |

---

## 🕐 Jadwal Otomatis

| Waktu | Aktivitas |
|-------|-----------|
| `00:05` | Reset streak yang putus |
| `19:00` | Daily reminder |
| `20:00` setiap Minggu | Weekly report |
| `21:00` | Daily summary |

---

## 🧪 Cara Testing Singkat

1. Jalankan bot:
   ```bash
   python -m app.bot
   ```

2. Buka Telegram dan kirim:
   ```text
   /start
   ```

3. Coba alur berikut:
   - Tambah habit
   - Lihat daftar habit
   - Check-in habit hari ini
   - Lihat statistik
   - Buka profile
   - Ubah reminder
   - Pause lalu resume habit
   - Lihat riwayat 30 hari

---

## 🖥 Deployment ke VPS

### 1. Setup server Ubuntu

```bash
apt update && apt upgrade -y
apt install python3.11 python3.11-venv git -y
```

### 2. Clone project dan setup environment

```bash
cd /opt/apps
git clone https://github.com/username/habit-tracker-bot.git
cd habit-tracker-bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Buat file `.env`

```bash
nano .env
```

Isi token dan konfigurasi sesuai kebutuhan.

### 4. Buat systemd service

```bash
nano /etc/systemd/system/habit-bot.service
```

Isi dengan:

```ini
[Unit]
Description=Habit Tracker Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/apps/habit-tracker-bot
ExecStart=/opt/apps/habit-tracker-bot/venv/bin/python -m app.bot
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 5. Aktifkan service

```bash
systemctl daemon-reload
systemctl enable habit-bot
systemctl start habit-bot
```

### 6. Pantau log

```bash
journalctl -u habit-bot -f
```

---

## 📝 Catatan

- File `.env` **jangan di-upload** ke GitHub
- Database SQLite akan otomatis dibuat saat bot pertama kali dijalankan
- Folder `logs/` digunakan untuk menyimpan log aktivitas dan error
- Bot berjalan selama terminal atau server masih aktif
- Untuk penggunaan 24 jam, disarankan deploy ke VPS

---

## 📌 Status Project

Project ini dibuat sebagai Telegram bot yang serius, modular, dan realistis untuk penggunaan sehari-hari.

Fokus utamanya:
- membantu user tetap konsisten
- mempermudah check-in harian
- memberi insight lewat statistik dan streak
- tetap nyaman dipakai tanpa terasa berisik

---

## 🔮 Pengembangan Selanjutnya

Beberapa ide pengembangan lanjutan:
- timezone per user
- target mingguan fleksibel
- kategori habit
- export data
- dashboard web
- notifikasi yang lebih personal
- penyimpanan database yang lebih besar seperti PostgreSQL

---

## 📄 Lisensi

Project ini dibuat untuk keperluan personal dan pembelajaran.
