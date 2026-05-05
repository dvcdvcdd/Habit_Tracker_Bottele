# app/utils/enums.py

from enum import Enum


class HabitSchedule(str, Enum):
    """
    Jadwal kapan habit harus dilakukan.
    Mewarisi dari str agar bisa disimpan langsung ke database sebagai teks.
    """
    EVERYDAY    = "everyday"       # setiap hari
    WEEKDAY     = "weekday"        # Senin sampai Jumat
    MON_WED_FRI = "mon_wed_fri"    # Senin, Rabu, Jumat
    TUE_THU_SAT = "tue_thu_sat"    # Selasa, Kamis, Sabtu
    WEEKEND     = "weekend"        # Sabtu dan Minggu
    CUSTOM      = "custom"         # hari tertentu pilihan user


class CheckinStatus(str, Enum):
    """
    Status check-in habit untuk satu hari tertentu.
    """
    DONE    = "done"     # sudah check-in
    MISSED  = "missed"   # tidak check-in padahal dijadwalkan
    SKIP    = "skip"     # tidak dijadwalkan hari itu, jadi tidak dihitung


class UserState(str, Enum):
    """
    State percakapan user dengan bot.
    Dipakai untuk melacak sedang di tahap mana user saat input multi-langkah,
    misalnya saat proses tambah habit (input nama → pilih jadwal → konfirmasi).
    """
    IDLE                = "idle"
    WAITING_HABIT_NAME  = "waiting_habit_name"
    WAITING_SCHEDULE    = "waiting_schedule"
    WAITING_TIME        = "waiting_time"
    WAITING_CONFIRM     = "waiting_confirm"


class StreakStatus(str, Enum):
    """
    Kondisi streak user saat ini.
    Dipakai untuk menentukan jenis pesan yang dikirim bot.
    """
    ACTIVE   = "active"    # streak berjalan normal
    BROKEN   = "broken"    # streak baru saja putus
    COMEBACK = "comeback"  # user baru kembali setelah bolong beberapa hari
    NEW      = "new"       # habit baru, belum ada streak

SCHEDULE_DISPLAY = {
    HabitSchedule.EVERYDAY:    "Setiap hari",
    HabitSchedule.WEEKDAY:     "Senin – Jumat",
    HabitSchedule.MON_WED_FRI: "Senin, Rabu, Jumat",
    HabitSchedule.TUE_THU_SAT: "Selasa, Kamis, Sabtu",
    HabitSchedule.WEEKEND:     "Sabtu & Minggu",
    HabitSchedule.CUSTOM:      "Hari tertentu",
}

SCHEDULE_DAYS = {
    HabitSchedule.EVERYDAY:    [0, 1, 2, 3, 4, 5, 6],
    HabitSchedule.WEEKDAY:     [0, 1, 2, 3, 4],
    HabitSchedule.MON_WED_FRI: [0, 2, 4],
    HabitSchedule.TUE_THU_SAT: [1, 3, 5],
    HabitSchedule.WEEKEND:     [5, 6],
    HabitSchedule.CUSTOM:      [],  # diisi nanti berdasarkan pilihan user
}