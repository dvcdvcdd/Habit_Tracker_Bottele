# app/database/init_db.py

import aiosqlite
import logging
from pathlib import Path

from app.config import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQL untuk membuat semua tabel
# Dipisah ke konstanta agar mudah dibaca dan diubah
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
    last_active     TEXT
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
    FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE,
    UNIQUE (habit_id, date)
);
"""

SQL_CREATE_INDEXES = [
    # Mempercepat query checkin berdasarkan user dan tanggal
    "CREATE INDEX IF NOT EXISTS idx_checkins_user_date ON checkins(user_id, date);",
    # Mempercepat query habit aktif milik user tertentu
    "CREATE INDEX IF NOT EXISTS idx_habits_user_active ON habits(user_id, is_active);",
    # Mempercepat query reminder berdasarkan waktu
    "CREATE INDEX IF NOT EXISTS idx_users_reminder ON users(reminder_time, is_active);",
]

SQL_ENABLE_WAL = "PRAGMA journal_mode=WAL;"
SQL_ENABLE_FK  = "PRAGMA foreign_keys=ON;"


async def init_db() -> None:
    """
    Menginisialisasi database SQLite.

    Yang dilakukan:
    1. Buat folder data/ jika belum ada
    2. Aktifkan WAL mode (lebih cepat dan aman untuk concurrent access)
    3. Aktifkan foreign key constraint
    4. Buat semua tabel jika belum ada
    5. Buat index untuk performa query

    Fungsi ini dipanggil sekali saat bot pertama kali start.
    """
    # Pastikan folder data/ ada
    db_path = Path(config.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Menginisialisasi database di: {db_path}")

    async with aiosqlite.connect(db_path) as db:

        # Aktifkan WAL mode
        # WAL = Write-Ahead Logging
        # Membuat read dan write bisa terjadi bersamaan tanpa lock
        await db.execute(SQL_ENABLE_WAL)

        # Aktifkan foreign key constraint
        # SQLite tidak aktifkan ini secara default
        await db.execute(SQL_ENABLE_FK)

        # Buat tabel users
        await db.execute(SQL_CREATE_USERS)
        logger.info("Tabel 'users' siap.")

        # Buat tabel habits
        await db.execute(SQL_CREATE_HABITS)
        logger.info("Tabel 'habits' siap.")

        # Buat tabel checkins
        await db.execute(SQL_CREATE_CHECKINS)
        logger.info("Tabel 'checkins' siap.")

        # Buat semua index
        for sql_index in SQL_CREATE_INDEXES:
            await db.execute(sql_index)
        logger.info("Index database siap.")

        # Simpan semua perubahan
        await db.commit()

    logger.info("Database berhasil diinisialisasi.")


async def get_db_connection() -> aiosqlite.Connection:
    """
    Membuka dan mengembalikan koneksi database.

    Penting:
    - Selalu aktifkan foreign keys setiap kali buka koneksi baru
    - Aktifkan row_factory agar hasil query bisa diakses seperti dict

    Cara pakai:
        async with await get_db_connection() as db:
            await db.execute(...)

    Catatan:
    Untuk project yang lebih besar, sebaiknya pakai connection pool.
    Untuk versi 1.0 ini, pendekatan per-query sudah cukup.
    """
    db = await aiosqlite.connect(config.db_path)
    db.row_factory = aiosqlite.Row

    # Aktifkan foreign keys
    await db.execute(SQL_ENABLE_FK)

    return db