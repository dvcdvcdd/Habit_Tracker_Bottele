import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Config:
    """
    Konfigurasi utama bot.
    frozen=True artinya nilai tidak bisa diubah setelah dibuat (immutable).
    Ini mencegah bug karena config diubah tidak sengaja di runtime.
    """

    # Token bot dari BotFather
    bot_token: str

    # Path ke file database SQLite
    db_path: str

    # Timezone yang dipakai bot
    timezone: str

    # Jam reminder default dalam format "HH:MM", contoh "19:00"
    reminder_time: str

    # Berapa hari bolong sebelum dianggap "comeback mode"
    comeback_threshold: int


def load_config() -> Config:
    """
    Membaca environment variable dan mengembalikan objek Config.

    Fungsi ini akan raise ValueError jika BOT_TOKEN tidak ditemukan,
    karena bot tidak bisa jalan tanpa token.
    """
    bot_token = os.getenv("BOT_TOKEN", "").strip()

    if not bot_token:
        raise ValueError(
            "BOT_TOKEN tidak ditemukan di file .env\n"
            "Pastikan file .env sudah dibuat dan diisi dengan token dari BotFather."
        )

    return Config(
        bot_token          = bot_token,
        db_path            = os.getenv("DB_PATH", str(BASE_DIR / "data" / "habits.db")),
        timezone           = os.getenv("TIMEZONE", "Asia/Jakarta"),
        reminder_time      = os.getenv("REMINDER_TIME", "19:00"),
        comeback_threshold = int(os.getenv("COMEBACK_THRESHOLD", "2")),
    )

config = load_config()