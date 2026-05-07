import logging
from typing import Tuple

from app.database.models import Habit
from app.database.queries import (
    get_checkins_for_habit,
    reset_streak,
    update_streak,
    was_checked_in_yesterday,
)
from app.utils.dates import (
    date_range,
    today_str,
    yesterday_str,
)
from app.utils.enums import StreakStatus

logger = logging.getLogger(__name__)


def is_habit_scheduled_today_for_date(
    schedule:    str,
    custom_days: str,
    target_date,
) -> bool:
    from app.utils.enums import HabitSchedule, SCHEDULE_DAYS
    day_of_week = target_date.weekday()
    if schedule == HabitSchedule.CUSTOM:
        if not custom_days:
            return False
        try:
            days = [int(d.strip()) for d in custom_days.split(",")]
            return day_of_week in days
        except ValueError:
            return False
    scheduled_days = SCHEDULE_DAYS.get(schedule, [])
    return day_of_week in scheduled_days


def _had_previous_checkins(checkins: list) -> bool:
    t = today_str()
    return any(c.date < t for c in checkins)


async def calculate_streak(habit: Habit) -> Tuple[int, str]:
    from datetime import date, timedelta
    checkins = await get_checkins_for_habit(habit.habit_id, limit=90)

    if not checkins:
        return 1, StreakStatus.NEW

    checkin_dates = {c.date for c in checkins}

    end_date   = date.fromisoformat(today_str())
    start_date = end_date - timedelta(days=89)
    all_dates  = date_range(start_date.isoformat(), end_date.isoformat())

    consecutive = 0
    for d in reversed(all_dates):
        date_str     = d.isoformat()
        is_scheduled = is_habit_scheduled_today_for_date(
            habit.schedule, habit.custom_days, d
        )
        if not is_scheduled:
            continue
        if date_str in checkin_dates:
            consecutive += 1
        else:
            break

    streak = consecutive

    if streak == 0:
        status = StreakStatus.BROKEN
    elif streak == 1:
        prev_streak = habit.current_streak
        if prev_streak == 0:
            status = StreakStatus.COMEBACK if _had_previous_checkins(checkins) else StreakStatus.NEW
        else:
            status = StreakStatus.ACTIVE
    else:
        status = StreakStatus.ACTIVE

    return streak, status


async def process_checkin_streak(habit: Habit) -> Tuple[int, int, str]:
    new_streak, status = await calculate_streak(habit)
    new_longest        = max(habit.longest_streak, new_streak)

    await update_streak(
        habit_id       = habit.habit_id,
        current_streak = new_streak,
        longest_streak = new_longest,
    )

    logger.info(
        f"Habit {habit.habit_id} streak: "
        f"{habit.current_streak} → {new_streak} ({status})"
    )

    return new_streak, new_longest, status


async def check_and_reset_broken_streaks(user_id: int) -> list:
    from app.database.queries import get_habits
    from datetime import date

    habits    = await get_habits(user_id, active_only=True)
    reset_ids = []
    yesterday = date.fromisoformat(yesterday_str())

    for habit in habits:
        was_scheduled = is_habit_scheduled_today_for_date(
            habit.schedule, habit.custom_days, yesterday
        )
        if not was_scheduled:
            continue
        checked = await was_checked_in_yesterday(habit.habit_id)
        if not checked and habit.current_streak > 0:
            await reset_streak(habit.habit_id)
            reset_ids.append(habit.habit_id)
            logger.info(f"Streak habit {habit.habit_id} direset")

    return reset_ids


def get_streak_display(habit: Habit) -> str:
    from app.utils.helpers import format_streak
    return format_streak(habit.current_streak)