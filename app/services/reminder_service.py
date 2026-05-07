# app/services/reminder_service.py

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import config
from app.database.queries import (
    get_all_active_users,
    get_daily_summary,
    get_weekly_stats,
)
from app.keyboards.inline import kb_checkin_habits, kb_back_to_main
from app.services.motivation_service import (
    get_reminder_message,
    get_weekly_report_message,
)
from app.services.streak_service import check_and_reset_broken_streaks
from app.utils.dates import today_str, format_date_display, week_start_end
from app.utils.helpers import emoji_progress_bar

logger = logging.getLogger(__name__)


async def send_daily_reminder(bot: Bot) -> None:
    logger.info(f"Menjalankan daily reminder — {today_str()}")
    from app.services.habit_service import get_today_habits_with_status

    users = await get_all_active_users()
    sent_count = 0

    for user in users:
        try:
            habits_today = await get_today_habits_with_status(user.user_id)
            pending = [h for h in habits_today if not h.is_done_today]

            if not pending:
                continue

            reminder_msg = get_reminder_message(user.first_name)
            pending_list = "\n".join(f"⬜ {h.habit.name}" for h in pending)

            text = (
                f"⏰ *Reminder Habit*\n\n"
                f"{reminder_msg}\n\n"
                f"Habit yang belum selesai:\n"
                f"{pending_list}\n\n"
                f"_Ketuk tombol di bawah untuk check-in._"
            )

            await bot.send_message(
                chat_id=user.user_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=kb_checkin_habits(pending),
            )
            sent_count += 1

        except Exception as e:
            logger.error(f"Gagal kirim reminder ke user {user.user_id}: {e}")
            continue

    logger.info(f"Reminder selesai. Terkirim: {sent_count}/{len(users)}")


async def send_morning_reset(bot: Bot) -> None:
    logger.info(f"Menjalankan morning reset — {today_str()}")
    users = await get_all_active_users()
    total_reset = 0

    for user in users:
        try:
            reset_ids = await check_and_reset_broken_streaks(user.user_id)
            total_reset += len(reset_ids)
        except Exception as e:
            logger.error(f"Gagal reset streak user {user.user_id}: {e}")
            continue

    logger.info(f"Morning reset selesai. Total direset: {total_reset}")


async def send_daily_summary_broadcast(bot: Bot) -> None:
    from app.services.stats_service import get_daily_summary_text

    logger.info(f"Menjalankan summary broadcast — {today_str()}")
    users = await get_all_active_users()
    sent_count = 0

    for user in users:
        try:
            summary = await get_daily_summary(user.user_id)
            if summary.done_habits == 0:
                continue

            text = await get_daily_summary_text(user.user_id)
            await bot.send_message(
                chat_id=user.user_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=kb_back_to_main(),
            )
            sent_count += 1

        except Exception as e:
            logger.error(f"Gagal kirim summary ke user {user.user_id}: {e}")
            continue

    logger.info(f"Summary broadcast selesai. Terkirim: {sent_count}/{len(users)}")


async def send_weekly_report(bot: Bot) -> None:
    """
    Kirim laporan mingguan ke semua user aktif.
    Dijalankan setiap Minggu malam.
    """
    logger.info(f"Menjalankan weekly report — {today_str()}")
    users = await get_all_active_users()
    sent_count = 0

    for user in users:
        try:
            stats = await get_weekly_stats(user.user_id)

            if stats.total_scheduled == 0:
                continue

            start_disp = format_date_display(stats.week_start)
            end_disp = format_date_display(stats.week_end)
            pct = int(stats.completion_rate * 100)
            progress = emoji_progress_bar(
                stats.total_checkins, stats.total_scheduled
            )
            motivation = get_weekly_report_message(stats.completion_rate)

            lines = [
                "📋 *Laporan Mingguan*",
                f"_{start_disp} — {end_disp}_",
                "",
                f"`{progress}` {pct}%",
                "",
                f"Check-in : *{stats.total_checkins} / {stats.total_scheduled}*",
            ]

            if stats.best_habit_name:
                lines.append(f"⭐ Terkonsisten : *{stats.best_habit_name}*")

            if stats.worst_habit_name:
                lines.append(f"⚠️ Perlu fokus : *{stats.worst_habit_name}*")

            lines.append("")
            lines.append(f"_{motivation}_")

            text = "\n".join(lines)

            await bot.send_message(
                chat_id=user.user_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=kb_back_to_main(),
            )
            sent_count += 1

        except Exception as e:
            logger.error(f"Gagal kirim weekly report ke user {user.user_id}: {e}")
            continue

    logger.info(f"Weekly report selesai. Terkirim: {sent_count}/{len(users)}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=config.timezone)

    try:
        reminder_hour, reminder_minute = config.reminder_time.split(":")
        reminder_hour = int(reminder_hour)
        reminder_minute = int(reminder_minute)
    except (ValueError, AttributeError):
        logger.warning("Format REMINDER_TIME tidak valid. Pakai default 19:00.")
        reminder_hour = 19
        reminder_minute = 0

    # Morning reset — setiap hari 00:05
    scheduler.add_job(
        func=send_morning_reset,
        trigger=CronTrigger(hour=0, minute=5, timezone=config.timezone),
        args=[bot],
        id="morning_reset",
        replace_existing=True,
    )

    # Daily reminder — sesuai config
    scheduler.add_job(
        func=send_daily_reminder,
        trigger=CronTrigger(
            hour=reminder_hour,
            minute=reminder_minute,
            timezone=config.timezone,
        ),
        args=[bot],
        id="daily_reminder",
        replace_existing=True,
    )

    # Daily summary — setiap hari 21:00
    scheduler.add_job(
        func=send_daily_summary_broadcast,
        trigger=CronTrigger(hour=21, minute=0, timezone=config.timezone),
        args=[bot],
        id="daily_summary",
        replace_existing=True,
    )

    # Weekly report — setiap Minggu 20:00
    scheduler.add_job(
        func=send_weekly_report,
        trigger=CronTrigger(
            day_of_week="sun",
            hour=20,
            minute=0,
            timezone=config.timezone,
        ),
        args=[bot],
        id="weekly_report",
        replace_existing=True,
    )

    logger.info(
        f"Scheduler dikonfigurasi:\n"
        f"  - Morning reset  : 00:05\n"
        f"  - Daily reminder : {config.reminder_time}\n"
        f"  - Daily summary  : 21:00\n"
        f"  - Weekly report  : Minggu 20:00\n"
        f"  - Timezone       : {config.timezone}"
    )

    return scheduler