# app/database/queries.py

import logging
from typing import List, Optional, Tuple

import aiosqlite

from app.database.init_db import get_db_connection
from app.database.models import CheckIn, DailySummary, Habit, User, WeeklyStats
from app.utils.dates import (
    date_range,
    is_habit_scheduled_today,
    now,
    today_str,
    week_start_end,
    yesterday_str,
)
from app.utils.enums import CheckinStatus, HabitSchedule, SCHEDULE_DAYS

logger = logging.getLogger(__name__)


# ===========================================================================
# SECTION 1 — USER QUERIES
# ===========================================================================

async def upsert_user(
    user_id: int,
    first_name: str,
    username: Optional[str] = None,
) -> None:
    async with get_db_connection() as db:
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
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return User(
                user_id=row["user_id"],
                username=row["username"],
                first_name=row["first_name"],
                reminder_time=row["reminder_time"],
                timezone=row["timezone"],
                is_active=bool(row["is_active"]),
                created_at=row["created_at"],
                last_active=row["last_active"],
            )


async def update_user_reminder(user_id: int, reminder_time: str) -> None:
    async with get_db_connection() as db:
        await db.execute(
            "UPDATE users SET reminder_time = ? WHERE user_id = ?",
            (reminder_time, user_id),
        )
        await db.commit()


async def update_last_active(user_id: int) -> None:
    async with get_db_connection() as db:
        await db.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (today_str(), user_id),
        )
        await db.commit()


async def get_all_active_users() -> List[User]:
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT * FROM users WHERE is_active = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                User(
                    user_id=row["user_id"],
                    username=row["username"],
                    first_name=row["first_name"],
                    reminder_time=row["reminder_time"],
                    timezone=row["timezone"],
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],
                    last_active=row["last_active"],
                )
                for row in rows
            ]


async def get_users_by_reminder_time(reminder_time: str) -> List[User]:
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT * FROM users WHERE reminder_time = ? AND is_active = 1",
            (reminder_time,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                User(
                    user_id=row["user_id"],
                    username=row["username"],
                    first_name=row["first_name"],
                    reminder_time=row["reminder_time"],
                    timezone=row["timezone"],
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],
                    last_active=row["last_active"],
                )
                for row in rows
            ]


# ===========================================================================
# SECTION 2 — HABIT QUERIES
# ===========================================================================

async def create_habit(
    user_id: int,
    name: str,
    schedule: str = HabitSchedule.EVERYDAY,
    custom_days: str = "",
) -> int:
    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            INSERT INTO habits (user_id, name, schedule, custom_days, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name, schedule, custom_days, today_str()),
        )
        await db.commit()
        return cursor.lastrowid


async def get_habits(user_id: int, active_only: bool = True) -> List[Habit]:
    query = "SELECT * FROM habits WHERE user_id = ?"
    params = [user_id]

    if active_only:
        query += " AND is_active = 1"

    query += " ORDER BY created_at ASC, habit_id ASC"

    async with get_db_connection() as db:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_habit(row) for row in rows]


async def get_habit_by_id(habit_id: int, user_id: int) -> Optional[Habit]:
    async with get_db_connection() as db:
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
    all_habits = await get_habits(user_id, active_only=True)
    return [
        habit for habit in all_habits
        if is_habit_scheduled_today(habit.schedule, habit.custom_days)
    ]


async def soft_delete_habit(habit_id: int, user_id: int) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute(
            "UPDATE habits SET is_active = 0 WHERE habit_id = ? AND user_id = ?",
            (habit_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_streak(
    habit_id: int,
    current_streak: int,
    longest_streak: int,
) -> None:
    async with get_db_connection() as db:
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
    async with get_db_connection() as db:
        await db.execute(
            "UPDATE habits SET current_streak = 0 WHERE habit_id = ?",
            (habit_id,),
        )
        await db.commit()


# ===========================================================================
# SECTION 3 — CHECKIN QUERIES
# ===========================================================================

async def create_checkin(habit_id: int, user_id: int) -> bool:
    checked_at = now().isoformat()
    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO checkins
                (habit_id, user_id, date, status, checked_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (habit_id, user_id, today_str(), CheckinStatus.DONE, checked_at),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_checkin_today(habit_id: int) -> Optional[CheckIn]:
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT * FROM checkins WHERE habit_id = ? AND date = ?",
            (habit_id, today_str()),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_checkin(row)


async def get_checkins_by_date_range(
    user_id: int,
    start_date: str,
    end_date: str,
) -> List[CheckIn]:
    async with get_db_connection() as db:
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


async def get_checkins_for_habit(habit_id: int, limit: int = 90) -> List[CheckIn]:
    async with get_db_connection() as db:
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
    async with get_db_connection() as db:
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
    start, end = week_start_end()
    async with get_db_connection() as db:
        async with db.execute(
            """
            SELECT COUNT(*) AS total FROM checkins
            WHERE user_id = ? AND date BETWEEN ? AND ? AND status = 'done'
            """,
            (user_id, start, end),
        ) as cursor:
            row = await cursor.fetchone()
            return row["total"] if row else 0


# ===========================================================================
# SECTION 4 — SUMMARY & STATS
# ===========================================================================

async def get_daily_summary(user_id: int) -> DailySummary:
    habits_today = await get_habits_scheduled_today(user_id)
    total = len(habits_today)

    if total == 0:
        return DailySummary(
            date=today_str(),
            total_habits=0,
            done_habits=0,
            missed_habits=0,
            completion_rate=0.0,
        )

    done = 0
    for habit in habits_today:
        checkin = await get_checkin_today(habit.habit_id)
        if checkin and checkin.status == CheckinStatus.DONE:
            done += 1

    return DailySummary(
        date=today_str(),
        total_habits=total,
        done_habits=done,
        missed_habits=total - done,
        completion_rate=(done / total) if total > 0 else 0.0,
    )


async def get_weekly_stats(user_id: int) -> WeeklyStats:
    start, end = week_start_end()
    all_habits = await get_habits(user_id, active_only=True)

    if not all_habits:
        return WeeklyStats(
            week_start=start, week_end=end,
            total_checkins=0, total_scheduled=0,
            completion_rate=0.0,
            best_habit_name=None, worst_habit_name=None,
        )

    checkins_this_week = await get_checkins_by_date_range(user_id, start, end)
    checkin_set = {(c.habit_id, c.date) for c in checkins_this_week}

    total_scheduled = 0
    total_done = 0
    habit_scores = {}

    for habit in all_habits:
        habit_done = 0
        habit_scheduled = 0

        for d in date_range(start, end):
            weekday_num = d.weekday()

            if habit.schedule == HabitSchedule.CUSTOM:
                try:
                    scheduled_days = [
                        int(x.strip()) for x in habit.custom_days.split(",") if x.strip()
                    ]
                except ValueError:
                    scheduled_days = []
            else:
                scheduled_days = SCHEDULE_DAYS.get(habit.schedule, [])

            if weekday_num not in scheduled_days:
                continue

            habit_scheduled += 1
            if (habit.habit_id, d.isoformat()) in checkin_set:
                habit_done += 1

        total_scheduled += habit_scheduled
        total_done += habit_done
        habit_scores[habit.habit_id] = (habit_done, habit_scheduled, habit.name)

    best_habit_name = None
    worst_habit_name = None

    scored = [
        (hid, d, s, n)
        for hid, (d, s, n) in habit_scores.items()
        if s > 0
    ]

    if scored:
        best = max(scored, key=lambda x: x[1] / x[2] if x[2] > 0 else 0)
        best_habit_name = best[3]
        worst = min(scored, key=lambda x: x[1] / x[2] if x[2] > 0 else 0)
        if worst[1] < worst[2]:
            worst_habit_name = worst[3]

    return WeeklyStats(
        week_start=start, week_end=end,
        total_checkins=total_done, total_scheduled=total_scheduled,
        completion_rate=(total_done / total_scheduled) if total_scheduled > 0 else 0.0,
        best_habit_name=best_habit_name, worst_habit_name=worst_habit_name,
    )


async def get_last_checkin_date(user_id: int) -> Optional[str]:
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT MAX(date) AS last_date FROM checkins WHERE user_id = ? AND status = 'done'",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["last_date"] if row else None


# ===========================================================================
# SECTION 5 — PROFILE QUERIES
# ===========================================================================

async def get_total_checkins(user_id: int) -> int:
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT COUNT(*) AS total FROM checkins WHERE user_id = ? AND status = 'done'",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["total"] if row else 0


async def get_total_active_days(user_id: int) -> int:
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT COUNT(DISTINCT date) AS total FROM checkins WHERE user_id = ? AND status = 'done'",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["total"] if row else 0


async def get_best_streak_ever(user_id: int):
    async with get_db_connection() as db:
        async with db.execute(
            """
            SELECT name, longest_streak FROM habits
            WHERE user_id = ? AND longest_streak > 0
            ORDER BY longest_streak DESC LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return (row["name"], row["longest_streak"])


# ===========================================================================
# SECTION 6 — EDIT & PAUSE QUERIES
# ===========================================================================

async def update_habit_name(habit_id: int, user_id: int, new_name: str) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            UPDATE habits SET name = ?
            WHERE habit_id = ? AND user_id = ? AND is_active IN (1, 2)
            """,
            (new_name, habit_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_habit_schedule(
    habit_id: int, user_id: int,
    schedule: str, custom_days: str = "",
) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            UPDATE habits SET schedule = ?, custom_days = ?
            WHERE habit_id = ? AND user_id = ? AND is_active IN (1, 2)
            """,
            (schedule, custom_days, habit_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def pause_habit(habit_id: int, user_id: int) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute(
            "UPDATE habits SET is_active = 2 WHERE habit_id = ? AND user_id = ? AND is_active = 1",
            (habit_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def resume_habit(habit_id: int, user_id: int) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute(
            "UPDATE habits SET is_active = 1 WHERE habit_id = ? AND user_id = ? AND is_active = 2",
            (habit_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_habit_by_id_any_status(habit_id: int, user_id: int) -> Optional[Habit]:
    async with get_db_connection() as db:
        async with db.execute(
            """
            SELECT * FROM habits
            WHERE habit_id = ? AND user_id = ? AND is_active IN (1, 2)
            """,
            (habit_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_habit(row)


async def get_all_habits_including_paused(user_id: int) -> List[Habit]:
    async with get_db_connection() as db:
        async with db.execute(
            """
            SELECT * FROM habits
            WHERE user_id = ? AND is_active IN (1, 2)
            ORDER BY is_active DESC, created_at ASC
            """,
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_habit(row) for row in rows]


# ===========================================================================
# SECTION 7 — PRIVATE HELPERS
# ===========================================================================

def _row_to_habit(row: aiosqlite.Row) -> Habit:
    return Habit(
        habit_id=row["habit_id"],
        user_id=row["user_id"],
        name=row["name"],
        schedule=row["schedule"],
        custom_days=row["custom_days"] or "",
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        current_streak=row["current_streak"],
        longest_streak=row["longest_streak"],
    )


def _row_to_checkin(row: aiosqlite.Row) -> CheckIn:
    return CheckIn(
        checkin_id=row["checkin_id"],
        habit_id=row["habit_id"],
        user_id=row["user_id"],
        date=row["date"],
        status=row["status"],
        checked_at=row["checked_at"],
    )