# app/database/models.py

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    """
    Merepresentasikan satu baris di tabel 'users'.

    Menyimpan data dasar user Telegram yang berinteraksi dengan bot.
    """
    user_id:          int            # Telegram user ID (primary key)
    username:         Optional[str]  # @username Telegram, bisa None
    first_name:       str            # Nama depan user di Telegram
    reminder_time:    str            # Jam reminder, format "HH:MM"
    timezone:         str            # Timezone user
    is_active:        bool           # Apakah user masih aktif (belum /stop)
    created_at:       str            # Tanggal pertama kali /start, format "YYYY-MM-DD"
    last_active:      Optional[str]  # Tanggal terakhir interaksi


@dataclass
class Habit:
    """
    Merepresentasikan satu baris di tabel 'habits'.

    Setiap user bisa punya banyak habit.
    """
    habit_id:     int            # Primary key, auto-increment
    user_id:      int            # Foreign key ke tabel users
    name:         str            # Nama habit, contoh "Olahraga"
    schedule:     str            # Nilai dari HabitSchedule enum
    custom_days:  str            # Dipakai jika schedule == "custom", contoh "0,2,4"
    is_active:    bool           # Habit masih aktif atau sudah dihapus
    created_at:   str            # Tanggal habit dibuat, format "YYYY-MM-DD"
    current_streak: int = 0      # Streak berjalan saat ini
    longest_streak: int = 0      # Streak terpanjang sepanjang masa


@dataclass
class CheckIn:
    """
    Merepresentasikan satu baris di tabel 'checkins'.

    Setiap check-in user untuk satu habit di satu tanggal tertentu.
    Kombinasi (habit_id, date) harus unik, tidak boleh double check-in.
    """
    checkin_id:   int   # Primary key, auto-increment
    habit_id:     int   # Foreign key ke tabel habits
    user_id:      int   # Redundan tapi berguna untuk query yang lebih cepat
    date:         str   # Tanggal check-in, format "YYYY-MM-DD"
    status:       str   # Nilai dari CheckinStatus enum
    checked_at:   str   # Datetime saat check-in, format ISO


@dataclass
class DailySummary:
    """
    Bukan tabel tersendiri, tapi struktur data yang dipakai
    untuk menampilkan ringkasan harian ke user.

    Dibuat dari hasil query, bukan disimpan ke database.
    """
    date:            str
    total_habits:    int   # total habit yang dijadwalkan hari ini
    done_habits:     int   # berberapa yang sudah check-in
    missed_habits:   int   # berapa yang belum/terlewat
    completion_rate: float # persentase selesai (0.0 - 1.0)


@dataclass
class WeeklyStats:
    """
    Struktur data untuk statistik mingguan.
    Juga tidak disimpan ke database, dibuat dari hasil query.
    """
    week_start:       str
    week_end:         str
    total_checkins:   int    # total check-in minggu ini
    total_scheduled:  int    # total habit yang harusnya check-in
    completion_rate:  float  # persentase keseluruhan
    best_habit_name:  Optional[str]  # habit paling konsisten minggu ini
    worst_habit_name: Optional[str]  # habit yang paling sering terlewat