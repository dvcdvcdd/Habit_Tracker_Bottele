# app/database/init_db.py

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from app.config import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQL schema
# ---------------------------------------------------------------------------

SQL_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    username        TEXT,
    first_name      TEXT    NOT NULL,
    reminder_time   TEXT    NOT NULL DEFAULT '19:00',
    timezone        TEXT    NOT NULL DEFAULT 'Asia/Jakarta',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL,
    last_active     TEXT,
    points          INTEGER NOT NULL DEFAULT 0,
    level           INTEGER NOT NULL DEFAULT 1
);
"""

SQL_CREATE_HABITS = """
CREATE TABLE IF NOT EXISTS habits (
    habit_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    name            TEXT    NOT NULL,
    schedule        TEXT    NOT NULL DEFAULT 'everyday',
    custom_days     TEXT    NOT NULL DEFAULT '',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL,
    current_streak  INTEGER NOT NULL DEFAULT 0,
    longest_streak  INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
"""

SQL_CREATE_CHECKINS = """
CREATE TABLE IF NOT EXISTS checkins (
    checkin_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id    INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    date        TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'done',
    checked_at  TEXT    NOT NULL,
    FOREIGN KEY (habit_id) REFERENCES habits(habit_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE (habit_id, date)
);
"""

SQL_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_checkins_user_date ON checkins(user_id, date);",
    "CREATE INDEX IF NOT EXISTS idx_habits_user_active ON habits(user_id, is_active);",
    "CREATE INDEX IF NOT EXISTS idx_users_reminder ON users(reminder_time, is_active);",
]

SQL_ENABLE_WAL = "PRAGMA journal_mode=WAL;"
SQL_ENABLE_FK = "PRAGMA foreign_keys=ON;"


async def init_db() -> None:
    """
    Inisialisasi database:
    - pastikan folder data ada
    - aktifkan WAL
    - aktifkan foreign keys
    - buat tabel jika belum ada
    - buat index
    """
    db_path = Path(config.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Menginisialisasi database di: {db_path}")

    async with aiosqlite.connect(db_path) as db:
        await db.execute(SQL_ENABLE_WAL)
        await db.execute(SQL_ENABLE_FK)

        await db.execute(SQL_CREATE_USERS)
        logger.info("Tabel 'users' siap.")

        await db.execute(SQL_CREATE_HABITS)
        logger.info("Tabel 'habits' siap.")

        await db.execute(SQL_CREATE_CHECKINS)
        logger.info("Tabel 'checkins' siap.")

        for sql_index in SQL_CREATE_INDEXES:
            await db.execute(sql_index)

        logger.info("Index database siap.")

        # ALTER TABLE for existing users schema
        try:
            await db.execute("ALTER TABLE users ADD COLUMN points INTEGER NOT NULL DEFAULT 0")
            await db.execute("ALTER TABLE users ADD COLUMN level INTEGER NOT NULL DEFAULT 1")
            logger.info("Migrasi kolom points dan level berhasil.")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info("Kolom points dan level sudah ada.")
            else:
                logger.error(f"Gagal melakukan ALTER TABLE users: {e}")

        await db.commit()

    logger.info("Database berhasil diinisialisasi.")


@asynccontextmanager
async def get_db_connection():
    """
    Koneksi database per pemakaian.

    Cara pakai:
        async with get_db_connection() as db:
            await db.execute(...)

    Penting:
    - jangan pakai: async with await get_db_connection()
    - pakai:        async with get_db_connection()
    """
    async with aiosqlite.connect(config.db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(SQL_ENABLE_FK)
        yield db