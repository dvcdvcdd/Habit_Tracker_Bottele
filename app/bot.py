# app/bot.py

import asyncio
import logging
import logging.handlers
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from app.config import config
from app.database.init_db import init_db
from app.handlers import checkin, habit_edit, habits, profile, start, stats, summary
from app.middlewares.error_handler import ErrorHandlerMiddleware
from app.middlewares.logging_middleware import LoggingMiddleware
from app.middlewares.rate_limiter import RateLimiterMiddleware
from app.services.reminder_service import setup_scheduler


def setup_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)

    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "bot_error.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(fmt)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    """
    Mendaftarkan menu perintah resmi bot.
    Muncul di kolom input pesan Telegram sebagai tombol '/'.
    """
    commands = [
        BotCommand(command="start",     description="Menu utama"),
        BotCommand(command="checkin",   description="Check-in hari ini"),
        BotCommand(command="habits",    description="Daftar habit"),
        BotCommand(command="statistik", description="Statistik harian dan mingguan"),
        BotCommand(command="summary",   description="Ringkasan hari ini"),
        BotCommand(command="profile",   description="Profile dan pengaturan"),
        BotCommand(command="help",      description="Bantuan"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def main() -> None:

    setup_logging()

    logger.info("=" * 50)
    logger.info("Habit Tracker Bot sedang starting up...")
    logger.info("Log tersimpan di folder: logs/")
    logger.info("=" * 50)

    logger.info("Menginisialisasi database...")
    await init_db()
    logger.info("Database siap.")

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    logger.info("Mendaftarkan command menu...")

    try:
        await set_bot_commands(bot)
        logger.info("Command menu terdaftar.")
    except Exception as e:
        logger.warning(f"Gagal mendaftarkan command menu: {e}")

    logger.info("Mendaftarkan middleware...")

    rate_limiter = RateLimiterMiddleware(rate_limit=0.5)

    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(rate_limiter)
    dp.update.outer_middleware(ErrorHandlerMiddleware())

    logger.info("Middleware terdaftar.")

    logger.info("Mendaftarkan router handler...")

    dp.include_router(start.router)
    dp.include_router(habits.router)
    dp.include_router(habit_edit.router)
    dp.include_router(checkin.router)
    dp.include_router(stats.router)
    dp.include_router(summary.router)
    dp.include_router(profile.router)

    logger.info("Semua router terdaftar.")

    logger.info("Menyiapkan scheduler...")
    scheduler = setup_scheduler(bot)

    from apscheduler.triggers.interval import IntervalTrigger
    scheduler.add_job(
        func=lambda: rate_limiter.cleanup_old_entries(),
        trigger=IntervalTrigger(minutes=5),
        id="rate_limiter_cleanup",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler berjalan.")

    logger.info("Bot mulai polling...")
    logger.info("Bot siap menerima pesan. Tekan Ctrl+C untuk berhenti.")
    logger.info("=" * 50)

    try:
        await dp.start_polling(
            bot,
            drop_pending_updates=True,
        )
    except KeyboardInterrupt:
        logger.info("Bot dihentikan oleh user (Ctrl+C).")
    finally:
        logger.info("Memulai graceful shutdown...")
        logger.info("Mematikan scheduler...")
        scheduler.shutdown(wait=True)
        logger.info("Scheduler berhenti.")
        logger.info("Menutup koneksi bot...")
        await bot.session.close()
        logger.info("Koneksi bot ditutup.")
        logger.info("Bot berhenti dengan bersih.")
        logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())