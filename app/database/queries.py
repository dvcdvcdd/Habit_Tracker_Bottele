# app/database/queries.py

import logging
from datetime import datetime
from typing import List, Optional

import aiosqlite

from app.config import config
from app.database.init_db import get_db_connection
from app.database.models import CheckIn, DailySummary, Habit, User, WeeklyStats
from app.utils.dates import today_str, now, week_start_end, yesterday_str
from app.utils.enums import CheckinStatus, HabitSchedule, SCHEDULE_DAYS

logger = logging.getLogger(__name__)

async def upsert_user(
    user_id:    int,
    first_name: str,
    username:   Optional[str] = None,
) -> None:
    """
    Insert user baru atau update data user yang sudah ada.
    'Upsert' = insert + update dalam satu operasi.

    Dipanggil setiap kali user mengirim /start.
    """
    async with await get_db_connection() as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, first_name, created_at, last_active)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username    = excluded.username,
                first_name  = excluded.first_name,
                last_active = excluded.last_active,
                is_active   = 1
            """,
            (user_id, username, first_name, today_str(), today_str()),
        )
        await db.commit()


async def get_user(user_id: int) -> Optional[User]:
    """
    Mengambil data satu user berdasarkan user_id.
    Mengembalikan objek User atau None jika tidak ditemukan.
    """
    async with await get_db_connection() as db:
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return User(
                user_id       = row["user_id"],
                username      = row["username"],
                first_name    = row["first_name"],
                reminder_time = row["reminder_time"],
                timezone      = row["timezone"],
                is_active     = bool(row["is_active"]),
                created_at    = row["created_at"],
                last_active   = row["last_active"],
            )


async def update_user_reminder(user_id: int, reminder_time: str) -> None:
    """
    Mengupdate jam reminder user.
    Format reminder_time: "HH:MM", contoh "19:00"
    """
    async with await get_db_connection() as db:
        await db.execute(
            "UPDATE users SET reminder_time = ? WHERE user_id = ?",
            (reminder_time, user_id),
        )
        await db.commit()


async def update_last_active(user_id: int) -> None:
    """
    Memperbarui tanggal terakhir user berinteraksi dengan bot.
    Dipanggil setiap kali ada aktivitas dari user.
    """
    async with await get_db_connection() as db:
        await db.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (today_str(), user_id),
        )
        await db.commit()


async def get_all_active_users() -> List[User]:
    """
    Mengambil semua user yang masih aktif.
    Dipakai oleh reminder scheduler untuk mengirim pengingat ke semua user.
    """
    async with await get_db_connection() as db:
        async with db.execute(
            "SELECT * FROM users WHERE is_active = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                User(
                    user_id       = row["user_id"],
                    username      = row["username"],
                    first_name    = row["first_name"],
                    reminder_time = row["reminder_time"],
                    timezone      = row["timezone"],
                    is_active     = bool(row["is_active"]),
                    created_at    = row["created_at"],
                    last_active   = row["last_active"],
                )
                for row in rows
            ]


async def get_users_by_reminder_time(reminder_time: str) -> List[User]:
    """
    Mengambil semua user aktif yang punya jam reminder tertentu.
    Dipakai scheduler untuk kirim reminder pada jam yang tepat.

    Parameter:
    - reminder_time: format "HH:MM", contoh "19:00"
    """
    async with await get_db_connection() as db:
        async with db.execute(
            """
            SELECT * FROM users
            WHERE reminder_time = ? AND is_active = 1
            """,
            (reminder_time,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                User(
                    user_id       = row["user_id"],
                    username      = row["username"],
                    first_name    = row["first_name"],
                    reminder_time = row["reminder_time"],
                    timezone      = row["timezone"],
                    is_active     = bool(row["is_active"]),
                    created_at    = row["created_at"],
                    last_active   = row["last_active"],
                )
                for row in rows
            ]

async def create_habit(
    user_id:     int,
    name:        str,
    schedule:    str = HabitSchedule.EVERYDAY,
    custom_days: str = "",
) -> int:
    """
    Membuat habit baru untuk user tertentu.

    Mengembalikan habit_id dari habit yang baru dibuat.
    Berguna agar langsung bisa dipakai untuk operasi berikutnya.
    """
    async with await get_db_connection() as db:
        cursor = await db.execute(
            """
            INSERT INTO habits (user_id, name, schedule, custom_days, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name, schedule, custom_days, today_str()),
        )
        await db.commit()
        return cursor.lastrowid  # ID habit yang baru saja dibuat


async def get_habits(user_id: int, active_only: bool = True) -> List[Habit]:
    """
    Mengambil semua habit milik user tertentu.

    Parameter:
    - active_only: True  → hanya habit yang belum dihapus
                   False → semua habit termasuk yang sudah dihapus
    """
    query = "SELECT * FROM habits WHERE user_id = ?"
    params: tuple = (user_id,)

    if active_only:
        query  += " AND is_active = 1"

    query += " ORDER BY created_at ASC"

    async with await get_db_connection() as db:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_habit(row) for row in rows]


async def get_habit_by_id(habit_id: int, user_id: int) -> Optional[Habit]:
    """
    Mengambil satu habit berdasarkan habit_id.
    user_id diikutkan untuk memastikan habit memang milik user tersebut.
    Ini mencegah user mengakses habit milik orang lain.
    """
    async with await get_db_connection() as db:
        async with db.execute(
            """
            SELECT * FROM habits
            WHERE habit_id = ? AND user_id = ? AND is_active = 1
            """,
            (habit_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_habit(row)


async def get_habits_scheduled_today(user_id: int) -> List[Habit]:
    """
    Mengambil semua habit aktif milik user yang dijadwalkan hari ini.

    Kita ambil semua habit aktif, lalu filter di Python
    menggunakan is_habit_scheduled_today().

    Kenapa tidak filter di SQL?
    Karena logika jadwal (SCHEDULE_DAYS, custom_days) lebih mudah
    dan lebih aman dihitung di Python daripada di SQL.
    """
    from app.utils.dates import is_habit_scheduled_today

    all_habits = await get_habits(user_id, active_only=True)
    return [
        h for h in all_habits
        if is_habit_scheduled_today(h.schedule, h.custom_days)
    ]


async def soft_delete_habit(habit_id: int, user_id: int) -> bool:
    """
    'Menghapus' habit dengan mengubah is_active menjadi 0.
    Data checkin lama tetap tersimpan untuk keperluan statistik.

    Mengembalikan True jika berhasil, False jika habit tidak ditemukan.
    """
    async with await get_db_connection() as db:
        cursor = await db.execute(
            """
            UPDATE habits SET is_active = 0
            WHERE habit_id = ? AND user_id = ?
            """,
            (habit_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0  # True jika ada baris yang berhasil diupdate


async def update_streak(
    habit_id:       int,
    current_streak: int,
    longest_streak: int,
) -> None:
    """
    Mengupdate nilai streak setelah ada check-in baru.

    longest_streak selalu diupdate ke nilai terbesar antara
    nilai lama dan nilai baru current_streak.
    """
    async with await get_db_connection() as db:
        await db.execute(
            """
            UPDATE habits
            SET current_streak = ?, longest_streak = ?
            WHERE habit_id = ?
            """,
            (current_streak, longest_streak, habit_id),
        )
        await db.commit()


async def reset_streak(habit_id: int) -> None:
    """
    Reset current_streak ke 0 saat streak putus.
    longest_streak tidak direset karena itu adalah rekor sepanjang masa.
    """
    async with await get_db_connection() as db:
        await db.execute(
            "UPDATE habits SET current_streak = 0 WHERE habit_id = ?",
            (habit_id,),
        )
        await db.commit()

async def create_checkin(habit_id: int, user_id: int) -> bool:
    """
    Membuat check-in baru untuk hari ini.

    Mengembalikan:
    - True  → check-in berhasil dibuat
    - False → sudah pernah check-in hari ini (UNIQUE constraint)

    Kita pakai INSERT OR IGNORE untuk menangani duplikat dengan aman
    tanpa perlu try-except.
    """
    checked_at = now().isoformat()

    async with await get_db_connection() as db:
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO checkins
                (habit_id, user_id, date, status, checked_at)
            VALUES
                (?, ?, ?, ?, ?)
            """,
            (habit_id, user_id, today_str(), CheckinStatus.DONE, checked_at),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_checkin_today(habit_id: int) -> Optional[CheckIn]:
    """
    Mengecek apakah habit sudah di-checkin hari ini.
    Mengembalikan objek CheckIn atau None.
    """
    async with await get_db_connection() as db:
        async with db.execute(
            """
            SELECT * FROM checkins
            WHERE habit_id = ? AND date = ?
            """,
            (habit_id, today_str()),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_checkin(row)


async def get_checkins_by_date_range(
    user_id:    int,
    start_date: str,
    end_date:   str,
) -> List[CheckIn]:
    """
    Mengambil semua checkin user dalam rentang tanggal tertentu.
    Dipakai untuk statistik mingguan.

    Parameter:
    - start_date: format "YYYY-MM-DD"
    - end_date:   format "YYYY-MM-DD"
    """
    async with await get_db_connection() as db:
        async with db.execute(
            """
            SELECT * FROM checkins
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
            """,
            (user_id, start_date, end_date),
        ) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_checkin(row) for row in rows]


async def get_checkins_for_habit(
    habit_id: int,
    limit:    int = 30,
) -> List[CheckIn]:
    """
    Mengambil history checkin untuk satu habit tertentu.
    Dipakai untuk kalkulasi streak.

    Parameter:
    - limit: berapa record terakhir yang diambil (default 30 hari)
    """
    async with await get_db_connection() as db:
        async with db.execute(
            """
            SELECT * FROM checkins
            WHERE habit_id = ? AND status = 'done'
            ORDER BY date DESC
            LIMIT ?
            """,
            (habit_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_checkin(row) for row in rows]


async def was_checked_in_yesterday(habit_id: int) -> bool:
    """
    Mengecek apakah habit di-checkin kemarin.
    Dipakai untuk kalkulasi streak — apakah streak masih berlanjut.
    """
    async with await get_db_connection() as db:
        async with db.execute(
            """
            SELECT 1 FROM checkins
            WHERE habit_id = ? AND date = ? AND status = 'done'
            """,
            (habit_id, yesterday_str()),
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def count_checkins_this_week(user_id: int) -> int:
    """
    Menghitung total checkin user dalam minggu ini.
    Dipakai untuk statistik mingguan.
    """
    start, end = week_start_end()
    async with await get_db_connection() as db:
        async with db.execute(
            """
            SELECT COUNT(*) as total FROM checkins
            WHERE user_id = ? AND date BETWEEN ? AND ? AND status = 'done'
            """,
            (user_id, start, end),
        ) as cursor:
            row = await cursor.fetchone()
            return row["total"] if row else 0

async def get_daily_summary(user_id: int) -> DailySummary:
    """
    Menghasilkan ringkasan harian untuk user.

    Menghitung:
    - Berapa habit yang dijadwalkan hari ini
    - Berapa yang sudah done
    - Berapa yang belum
    - Persentase completion
    """
    from app.utils.dates import is_habit_scheduled_today

    habits_today = await get_habits_scheduled_today(user_id)
    total = len(habits_today)

    if total == 0:
        return DailySummary(
            date            = today_str(),
            total_habits    = 0,
            done_habits     = 0,
            missed_habits   = 0,
            completion_rate = 0.0,
        )

    done = 0
    for habit in habits_today:
        checkin = await get_checkin_today(habit.habit_id)
        if checkin and checkin.status == CheckinStatus.DONE:
            done += 1

    missed = total - done

    return DailySummary(
        date            = today_str(),
        total_habits    = total,
        done_habits     = done,
        missed_habits   = missed,
        completion_rate = done / total if total > 0 else 0.0,
    )


async def get_weekly_stats(user_id: int) -> WeeklyStats:
    """
    Menghasilkan statistik mingguan untuk user.

    Menghitung:
    - Total checkin minggu ini
    - Total yang seharusnya di-checkin (berdasarkan jadwal)
    - Habit paling konsisten
    - Habit yang paling sering terlewat
    """
    from app.utils.dates import is_habit_scheduled_today, date_range

    start, end = week_start_end()
    all_habits = await get_habits(user_id, active_only=True)

    if not all_habits:
        return WeeklyStats(
            week_start       = start,
            week_end         = end,
            total_checkins   = 0,
            total_scheduled  = 0,
            completion_rate  = 0.0,
            best_habit_name  = None,
            worst_habit_name = None,
        )

    # Hitung total checkin minggu ini per habit
    checkins_this_week = await get_checkins_by_date_range(user_id, start, end)
    checkin_set = {(c.habit_id, c.date) for c in checkins_this_week}

    total_scheduled = 0
    total_done      = 0
    habit_scores: dict[int, tuple[int, int, str]] = {}
    # habit_scores = {habit_id: (done, scheduled, name)}

    for habit in all_habits:
        habit_done      = 0
        habit_scheduled = 0

        for d in date_range(start, end):
            from app.utils.dates import SCHEDULE_DAYS as _SD
            import datetime as _dt

            day_of_week = d.weekday()
            scheduled_days = SCHEDULE_DAYS.get(habit.schedule, [])

            if habit.schedule == HabitSchedule.CUSTOM:
                try:
                    scheduled_days = [
                        int(x) for x in habit.custom_days.split(",") if x.strip()
                    ]
                except ValueError:
                    scheduled_days = []

            if day_of_week not in scheduled_days:
                continue

            habit_scheduled += 1
            date_str = d.isoformat()

            if (habit.habit_id, date_str) in checkin_set:
                habit_done += 1

        total_scheduled += habit_scheduled
        total_done      += habit_done
        habit_scores[habit.habit_id] = (habit_done, habit_scheduled, habit.name)

    # Cari habit terbaik dan terburuk
    best_habit_name  = None
    worst_habit_name = None

    scored = [
        (habit_id, done, scheduled, name)
        for habit_id, (done, scheduled, name) in habit_scores.items()
        if scheduled > 0
    ]

    if scored:
        # habit terbaik: rasio done/scheduled tertinggi
        best = max(scored, key=lambda x: x[1] / x[2] if x[2] > 0 else 0)
        best_habit_name = best[3]

        # habit terburuk: rasio done/scheduled terendah
        worst = min(scored, key=lambda x: x[1] / x[2] if x[2] > 0 else 0)
        # hanya tampilkan "terburuk" jika memang ada yang terlewat
        if worst[1] < worst[2]:
            worst_habit_name = worst[3]

    return WeeklyStats(
        week_start       = start,
        week_end         = end,
        total_checkins   = total_done,
        total_scheduled  = total_scheduled,
        completion_rate  = total_done / total_scheduled if total_scheduled > 0 else 0.0,
        best_habit_name  = best_habit_name,
        worst_habit_name = worst_habit_name,
    )


async def get_last_checkin_date(user_id: int) -> Optional[str]:
    """
    Mengambil tanggal check-in terakhir user (dari semua habit).
    Dipakai untuk comeback mode.

    Mengembalikan string tanggal "YYYY-MM-DD" atau None
    jika user belum pernah check-in sama sekali.
    """
    async with await get_db_connection() as db:
        async with db.execute(
            """
            SELECT MAX(date) as last_date FROM checkins
            WHERE user_id = ? AND status = 'done'
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["last_date"] if row else None

def _row_to_habit(row: aiosqlite.Row) -> Habit:
    """
    Mengkonversi satu baris hasil query ke objek Habit.
    Fungsi private, hanya dipakai di dalam file ini.
    Nama diawali _ untuk menandakan bahwa ini internal function.
    """
    return Habit(
        habit_id       = row["habit_id"],
        user_id        = row["user_id"],
        name           = row["name"],
        schedule       = row["schedule"],
        custom_days    = row["custom_days"] or "",
        is_active      = bool(row["is_active"]),
        created_at     = row["created_at"],
        current_streak = row["current_streak"],
        longest_streak = row["longest_streak"],
    )


def _row_to_checkin(row: aiosqlite.Row) -> CheckIn:
    """
    Mengkonversi satu baris hasil query ke objek CheckIn.
    """
    return CheckIn(
        checkin_id = row["checkin_id"],
        habit_id   = row["habit_id"],
        user_id    = row["user_id"],
        date       = row["date"],
        status     = row["status"],
        checked_at = row["checked_at"],
    )