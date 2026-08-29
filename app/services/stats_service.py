# app/services/stats_service.py

import logging
from typing import Optional

from app.database.queries import (
    get_daily_summary,
    get_weekly_stats,
    get_last_checkin_date,
    get_habits,
)
from app.services.motivation_service import (
    get_summary_message,
    get_comeback_message,
)
from app.utils.dates import (
    days_since,
    format_date_display,
    today_str,
)
from app.utils.helpers import DONE_MARK, TODO_MARK, esc, progress_bar

logger = logging.getLogger(__name__)


async def get_daily_summary_text(user_id: int) -> str:
    from app.database.queries import get_habits_scheduled_today, get_checkin_today
    from app.utils.enums import CheckinStatus

    summary      = await get_daily_summary(user_id)
    date_display = format_date_display(today_str())

    lines = [
        "<b>Ringkasan Hari Ini</b>",
        f"<i>{date_display}</i>",
        "",
    ]

    if summary.total_habits == 0:
        lines.append("Tidak ada habit yang dijadwalkan hari ini.")
        lines.append("Gunakan waktu ini untuk istirahat dan memulihkan tenaga.")
        return "\n".join(lines)

    pct      = int(summary.completion_rate * 100)
    progress = progress_bar(summary.done_habits, summary.total_habits)
    lines.append(f"<code>{progress}</code>  {pct}%")
    lines.append("")

    habits_today = await get_habits_scheduled_today(user_id)
    for habit in habits_today:
        checkin = await get_checkin_today(habit.habit_id)
        is_done = checkin and checkin.status == CheckinStatus.DONE
        icon    = DONE_MARK if is_done else TODO_MARK
        lines.append(f"{icon} {esc(habit.name)}")

    lines.append("")
    lines.append(
        f"<i>{get_summary_message(summary.done_habits, summary.total_habits)}</i>"
    )

    return "\n".join(lines)


async def get_weekly_stats_text(user_id: int) -> str:
    stats      = await get_weekly_stats(user_id)
    start_disp = format_date_display(stats.week_start)
    end_disp   = format_date_display(stats.week_end)

    lines = [
        "<b>Statistik Minggu Ini</b>",
        f"<i>{start_disp} – {end_disp}</i>",
        "",
    ]

    if stats.total_scheduled == 0:
        lines.append("Belum ada data untuk minggu ini.")
        return "\n".join(lines)

    pct      = int(stats.completion_rate * 100)
    progress = progress_bar(stats.total_checkins, stats.total_scheduled)

    lines.append(f"<code>{progress}</code>  {pct}%")
    lines.append("")
    lines.append(f"Total check-in : <b>{stats.total_checkins} / {stats.total_scheduled}</b>")
    lines.append("")

    if stats.best_habit_name:
        lines.append(f"Paling konsisten   : <b>{esc(stats.best_habit_name)}</b>")
    if stats.worst_habit_name:
        lines.append(f"Perlu diperhatikan : <b>{esc(stats.worst_habit_name)}</b>")

    lines.append("")
    if pct == 100:
        lines.append("<i>Minggu yang sempurna. Luar biasa.</i>")
    elif pct >= 80:
        lines.append("<i>Minggu yang solid. Pertahankan ritme ini.</i>")
    elif pct >= 50:
        lines.append("<i>Lumayan. Minggu depan bisa lebih baik.</i>")
    else:
        lines.append("<i>Minggu ini berat. Tidak apa-apa. Mulai lagi besok.</i>")

    return "\n".join(lines)


async def get_comeback_text(user_id: int) -> Optional[str]:
    from app.config import config

    last_checkin = await get_last_checkin_date(user_id)
    if last_checkin is None:
        return None

    absent_days = days_since(last_checkin)
    if absent_days < config.comeback_threshold:
        return None

    habits = await get_habits(user_id, active_only=True)
    if not habits:
        return None

    date_display = format_date_display(last_checkin)
    comeback_msg = get_comeback_message(absent_days)

    lines = [
        "<b>Selamat datang kembali!</b>",
        "",
        f"Check-in terakhir: <i>{date_display}</i> ({absent_days} hari yang lalu)",
        "",
        f"<i>{comeback_msg}</i>",
        "",
        f"Kamu memiliki <b>{len(habits)} habit</b> yang menunggu check-in hari ini.",
    ]

    return "\n".join(lines)


async def build_full_stats_text(user_id: int) -> str:
    daily_text  = await get_daily_summary_text(user_id)
    weekly_text = await get_weekly_stats_text(user_id)
    separator   = "\n\n" + "─" * 20 + "\n\n"
    return daily_text + separator + weekly_text
