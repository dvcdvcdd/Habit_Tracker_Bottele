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

from app.config import config
from app.database.init_db import init_db
from app.handlers import checkin, habits, profile, start, stats, summary
from app.middlewares.error_handler import ErrorHandlerMiddleware
from app.middlewares.logging_middleware import LoggingMiddleware
from app.middlewares.rate_limiter import RateLimiterMiddleware
from app.services.reminder_service import setup_scheduler


# ---------------------------------------------------------------------------
# Setup logging — ke terminal DAN ke file
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    """
    Setup logging ke dua tempat sekaligus:
    1. Terminal — untuk monitoring real-time
    2. File     — untuk history dan debugging

    File log:
    - logs/bot.log        → semua log INFO ke atas
    - logs/bot_error.log  → hanya ERROR ke atas
    - Rotasi otomatis tiap 5MB, simpan 5 file terakhir
    """

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Format log
    fmt = logging.Formatter(
        fmt     = "%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S",
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Handler 1 — Terminal
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    # Handler 2 — File utama (semua log INFO ke atas)
    # RotatingFileHandler otomatis buat file baru saat ukuran melebihi batas
    file_handler = logging.handlers.RotatingFileHandler(
        filename    = log_dir / "bot.log",
        maxBytes    = 5 * 1024 * 1024,  # 5MB per file
        backupCount = 5,                 # simpan 5 file lama
        encoding    = "utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)

    # Handler 3 — File error (hanya ERROR ke atas)
    error_handler = logging.handlers.RotatingFileHandler(
        filename    = log_dir / "bot_error.log",
        maxBytes    = 5 * 1024 * 1024,
        backupCount = 3,
        encoding    = "utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(fmt)

    # Pasang semua handler ke root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # Kurangi verbosity library pihak ketiga
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validasi input global
# ---------------------------------------------------------------------------

def sanitize_markdown(text: str) -> str:
    """
    Escape karakter Markdown yang bisa merusak tampilan pesan.

    Karakter yang di-escape: _ * [ ] ( ) ~ ` > # + - = | { } . !

    Dipakai untuk teks yang berasal dari input user sebelum
    dimasukkan ke dalam pesan Markdown.
    """
    chars_to_escape = r"\_*[]()~`>#+-=|{}.!"
    result = ""
    for char in text:
        if char in chars_to_escape:
            result += f"\\{char}"
        else:
            result += char
    return result


# ---------------------------------------------------------------------------
# Fungsi utama
# ---------------------------------------------------------------------------

async def main() -> None:
    """
    Entry point utama bot.

    Urutan startup:
    1. Setup logging
    2. Init database
    3. Buat Bot dan Dispatcher
    4. Daftarkan middleware
    5. Daftarkan router
    6. Setup dan start scheduler
    7. Jalankan polling
    8. Shutdown bersih
    """

    # 1. Setup logging
    setup_logging()

    logger.info("=" * 50)
    logger.info("Habit Tracker Bot sedang starting up...")
    logger.info(f"Log tersimpan di folder: logs/")
    logger.info("=" * 50)

    # 2. Init database
    logger.info("Menginisialisasi database...")
    await init_db()
    logger.info("Database siap.")

    # 3. Buat Bot dan Dispatcher
    bot = Bot(
        token   = config.bot_token,
        default = DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # 4. Daftarkan middleware
    # Urutan middleware sangat penting:
    # - LoggingMiddleware dulu agar semua request tercatat
    # - RateLimiterMiddleware setelah logging agar rate limit juga tercatat
    # - ErrorHandlerMiddleware terakhir agar menangkap error dari handler

    logger.info("Mendaftarkan middleware...")

    rate_limiter = RateLimiterMiddleware(rate_limit=0.5)

    # Update middleware — menangani Message
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(RateLimiterMiddleware(rate_limit=0.5))
    dp.update.outer_middleware(ErrorHandlerMiddleware())

    logger.info("Middleware terdaftar.")

    # 5. Daftarkan router
    logger.info("Mendaftarkan router handler...")

    dp.include_router(start.router)
    dp.include_router(habits.router)
    dp.include_router(checkin.router)
    dp.include_router(stats.router)
    dp.include_router(summary.router)
    dp.include_router(profile.router)

    logger.info("Semua router terdaftar.")

    # 6. Setup scheduler
    logger.info("Menyiapkan scheduler...")
    scheduler = setup_scheduler(bot)

    # Tambahkan job cleanup rate limiter setiap 5 menit
    from apscheduler.triggers.interval import IntervalTrigger
    scheduler.add_job(
        func             = lambda: rate_limiter.cleanup_old_entries(),
        trigger          = IntervalTrigger(minutes=5),
        id               = "rate_limiter_cleanup",
        replace_existing = True,
    )

    scheduler.start()
    logger.info("Scheduler berjalan.")

    # 7. Jalankan polling
    logger.info("Bot mulai polling...")
    logger.info("Bot siap menerima pesan. Tekan Ctrl+C untuk berhenti.")
    logger.info("=" * 50)

    try:
        await dp.start_polling(
            bot,
            drop_pending_updates = True,
        )
    except KeyboardInterrupt:
        logger.info("Bot dihentikan oleh user (Ctrl+C).")

    finally:
        # 8. Graceful shutdown
        logger.info("Memulai graceful shutdown...")

        # Stop scheduler dulu
        logger.info("Mematikan scheduler...")
        scheduler.shutdown(wait=True)  # wait=True → tunggu job yang sedang jalan selesai
        logger.info("Scheduler berhenti.")

        # Tutup koneksi bot
        logger.info("Menutup koneksi bot...")
        await bot.session.close()
        logger.info("Koneksi bot ditutup.")

        logger.info("Bot berhenti dengan bersih.")
        logger.info("=" * 50)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())