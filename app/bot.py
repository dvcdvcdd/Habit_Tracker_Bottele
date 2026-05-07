# app/bot.py

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import config
from app.database.init_db import init_db
from app.handlers import checkin, habits, start, stats, summary
from app.services.reminder_service import setup_scheduler


def setup_logging() -> None:
    logging.basicConfig(
        level    = logging.INFO,
        format   = "%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt  = "%Y-%m-%d %H:%M:%S",
        handlers = [logging.StreamHandler(sys.stdout)],
    )
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


async def main() -> None:

    setup_logging()

    logger.info("=" * 50)
    logger.info("Habit Tracker Bot sedang starting up...")
    logger.info("=" * 50)

    logger.info("Menginisialisasi database...")
    await init_db()
    logger.info("Database siap.")

    bot = Bot(
        token   = config.bot_token,
        default = DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    dp = Dispatcher(storage=MemoryStorage())

    logger.info("Mendaftarkan router handler...")
    dp.include_router(start.router)
    dp.include_router(habits.router)
    dp.include_router(checkin.router)
    dp.include_router(stats.router)
    dp.include_router(summary.router)
    logger.info("Semua router terdaftar.")

    logger.info("Menyiapkan scheduler...")
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Scheduler berjalan.")

    logger.info("Bot mulai polling...")
    logger.info("Bot siap menerima pesan. Tekan Ctrl+C untuk berhenti.")
    logger.info("=" * 50)

    try:
        await dp.start_polling(
            bot,
            drop_pending_updates = True,
        )
    except KeyboardInterrupt:
        logger.info("Bot dihentikan.")
    finally:
        logger.info("Mematikan scheduler...")
        scheduler.shutdown(wait=False)
        logger.info("Menutup koneksi bot...")
        await bot.session.close()
        logger.info("Bot berhenti dengan bersih.")


if __name__ == "__main__":
    asyncio.run(main())