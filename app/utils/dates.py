# app/utils/dates.py

from datetime import date, datetime, timedelta
from typing import List
from zoneinfo import ZoneInfo  # tersedia di Python 3.9+

from app.utils.enums import HabitSchedule, SCHEDULE_DAYS

DEFAULT_TIMEZONE = "Asia/Jakarta"


def get_timezone() -> ZoneInfo:
    """Mengembalikan objek timezone yang dipakai bot."""
    return ZoneInfo(DEFAULT_TIMEZONE)


def now() -> datetime:
    """
    Mengembalikan datetime sekarang dengan timezone yang benar.
    Selalu pakai fungsi ini, jangan pakai datetime.now() langsung,
    agar timezone konsisten di seluruh project.
    """
    return datetime.now(tz=get_timezone())


def today() -> date:
    """
    Mengembalikan tanggal hari ini (hanya tanggal, tanpa jam).
    Contoh hasil: date(2025, 1, 15)
    """
    return now().date()


def today_str() -> str:
    """
    Mengembalikan tanggal hari ini dalam format string YYYY-MM-DD.
    Format ini yang akan disimpan ke database.
    Contoh hasil: "2025-01-15"
    """
    return today().isoformat()


def weekday_today() -> int:
    """
    Mengembalikan angka hari ini.
    0 = Senin, 1 = Selasa, ..., 6 = Minggu
    Mengikuti konvensi Python datetime.weekday()
    """
    return today().weekday()


def weekday_name_today() -> str:
    """
    Mengembalikan nama hari ini dalam Bahasa Indonesia.
    Contoh hasil: "Senin", "Selasa", dst.
    """
    names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    return names[weekday_today()]


def is_habit_scheduled_today(schedule: str, custom_days: str = "") -> bool:
    """
    Mengecek apakah habit dengan jadwal tertentu dijadwalkan untuk hari ini.

    Parameter:
    - schedule: nilai dari HabitSchedule enum, disimpan sebagai string di DB
    - custom_days: string berisi angka hari dipisah koma, contoh "0,2,4"
                   hanya dipakai jika schedule == HabitSchedule.CUSTOM

    Mengembalikan True jika hari ini adalah jadwal habit, False jika tidak.
    """
    today_wd = weekday_today()

    if schedule == HabitSchedule.CUSTOM:
        if not custom_days:
            return False
        try:
            days = [int(d.strip()) for d in custom_days.split(",")]
            return today_wd in days
        except ValueError:
            return False

    scheduled_days = SCHEDULE_DAYS.get(schedule, [])
    return today_wd in scheduled_days


def days_since(date_str: str) -> int:
    """
    Menghitung berapa hari yang sudah berlalu sejak tanggal tertentu.

    Parameter:
    - date_str: tanggal dalam format "YYYY-MM-DD"

    Contoh:
    - Hari ini: 2025-01-15
    - date_str: "2025-01-10"
    - Hasil: 5
    """
    if not date_str:
        return 0
    try:
        past_date = date.fromisoformat(date_str)
        return (today() - past_date).days
    except ValueError:
        return 0


def date_range(start_str: str, end_str: str) -> List[date]:
    """
    Mengembalikan daftar semua tanggal dari start sampai end (inklusif).

    Parameter:
    - start_str: tanggal mulai, format "YYYY-MM-DD"
    - end_str: tanggal akhir, format "YYYY-MM-DD"

    Contoh:
    - start: "2025-01-10", end: "2025-01-13"
    - Hasil: [date(2025,1,10), date(2025,1,11), date(2025,1,12), date(2025,1,13)]
    """
    try:
        start = date.fromisoformat(start_str)
        end   = date.fromisoformat(end_str)
    except ValueError:
        return []

    result = []
    current = start
    while current <= end:
        result.append(current)
        current += timedelta(days=1)
    return result


def week_start_end() -> tuple[str, str]:
    """
    Mengembalikan tanggal awal dan akhir minggu ini (Senin s.d. Minggu).

    Hasil: tuple (start_str, end_str) dalam format "YYYY-MM-DD"
    Contoh: ("2025-01-13", "2025-01-19")
    """
    t = today()
    start = t - timedelta(days=t.weekday())   # Senin minggu ini
    end   = start + timedelta(days=6)         # Minggu minggu ini
    return start.isoformat(), end.isoformat()


def format_date_display(date_str: str) -> str:
    """
    Mengubah format tanggal dari "YYYY-MM-DD" menjadi tampilan lebih ramah.
    Contoh: "2025-01-15" → "15 Januari 2025"
    """
    months = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    try:
        d = date.fromisoformat(date_str)
        return f"{d.day} {months[d.month]} {d.year}"
    except ValueError:
        return date_str


def yesterday_str() -> str:
    """
    Mengembalikan tanggal kemarin dalam format "YYYY-MM-DD".
    Dipakai untuk mengecek apakah streak kemarin masih aktif.
    """
    return (today() - timedelta(days=1)).isoformat()