import logging

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery, Message

from app.database.queries import upsert_user, get_user
from app.keyboards.inline import (
    kb_main_menu,
    CB_BACK_MAIN,
    CB_CLOSE,
)
from app.services.stats_service import get_comeback_text
from app.utils.dates import weekday_name_today, format_date_display, today_str

logger = logging.getLogger(__name__)

# Router adalah cara aiogram v3 mengelompokkan handler
# Setiap file handler punya router-nya sendiri
# Nanti semua router didaftarkan di bot.py
router = Router()

def _build_welcome_text(first_name: str) -> str:
    """
    Membangun teks sambutan untuk /start.

    Dibuat sebagai fungsi terpisah agar mudah diubah
    tanpa harus mencari di tengah-tengah handler.
    """
    day  = weekday_name_today()
    date = format_date_display(today_str())

    return (
        f"Hei, *{first_name}!* 👋\n\n"
        f"Selamat datang di *Habit Tracker Bot*.\n\n"
        f"Bot ini membantu kamu membangun konsistensi "
        f"dengan cara yang sederhana dan tidak ribet.\n\n"
        f"Hari ini: _{day}, {date}_\n\n"
        f"Apa yang ingin kamu lakukan?"
    )


def _build_menu_text(first_name: str) -> str:
    """
    Teks menu utama saat user kembali dari halaman lain.
    Lebih singkat dari teks welcome.
    """
    return (
        f"Hei, *{first_name}!* 🏠\n\n"
        f"Kamu di menu utama.\n"
        f"Pilih yang ingin kamu lakukan:"
    )

@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """
    Handler untuk command /start.

    Yang dilakukan:
    1. Simpan atau update data user ke database
    2. Cek apakah user baru kembali setelah lama tidak aktif (comeback mode)
    3. Kirim pesan sambutan + menu utama
    """
    user = message.from_user

    # Simpan user ke database (upsert: insert jika baru, update jika sudah ada)
    await upsert_user(
        user_id    = user.id,
        first_name = user.first_name,
        username   = user.username,
    )

    logger.info(f"User /start: {user.id} (@{user.username})")

    # Cek comeback mode
    comeback_text = await get_comeback_text(user.id)

    if comeback_text:
        # Kirim pesan comeback dulu
        await message.answer(
            text       = comeback_text,
            parse_mode = "Markdown",
        )

    # Kirim menu utama
    await message.answer(
        text       = _build_welcome_text(user.first_name),
        parse_mode = "Markdown",
        reply_markup = kb_main_menu(),
    )

@router.message(Command("menu"))
async def handle_menu_command(message: Message) -> None:
    """
    Handler untuk command /menu.
    Shortcut untuk kembali ke menu utama via command.
    """
    user = message.from_user

    await message.answer(
        text         = _build_menu_text(user.first_name),
        parse_mode   = "Markdown",
        reply_markup = kb_main_menu(),
    )

@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """
    Handler untuk command /help.
    Menampilkan daftar fitur dan cara penggunaan.
    """
    help_text = (
        "*Cara pakai Habit Tracker Bot:*\n\n"
        "1️⃣ Tambahkan habit yang ingin kamu track\n"
        "2️⃣ Setiap hari, buka bot dan tekan *Check-in*\n"
        "3️⃣ Centang habit yang sudah kamu lakukan\n"
        "4️⃣ Pantau streak dan statistik kamu\n\n"
        "*Command yang tersedia:*\n"
        "/start — buka menu utama\n"
        "/menu  — kembali ke menu utama\n"
        "/help  — tampilkan bantuan ini\n\n"
        "*Tips:*\n"
        "• Mulai dengan 2-3 habit saja, jangan langsung banyak\n"
        "• Check-in setiap hari meski hanya 1 habit\n"
        "• Streak yang pendek tapi konsisten lebih baik "
        "dari target besar yang tidak tercapai\n\n"
        "_Bot ini akan mengingatkan kamu setiap hari "
        "pada jam yang sudah kamu set._"
    )

    await message.answer(
        text         = help_text,
        parse_mode   = "Markdown",
        reply_markup = kb_main_menu(),
    )

@router.callback_query(lambda c: c.data == CB_BACK_MAIN)
async def handle_back_to_main(callback: CallbackQuery) -> None:
    """
    Handler untuk tombol 'Menu Utama' dari halaman mana saja.

    Kita edit pesan yang ada (bukan kirim pesan baru)
    agar tampilan tidak menumpuk.
    """
    user = callback.from_user

    await callback.message.edit_text(
        text         = _build_menu_text(user.first_name),
        parse_mode   = "Markdown",
        reply_markup = kb_main_menu(),
    )

    # Selalu jawab callback query untuk menghilangkan loading indicator
    await callback.answer()

@router.callback_query(lambda c: c.data == CB_CLOSE)
async def handle_close(callback: CallbackQuery) -> None:
    """
    Handler untuk tombol Close.
    Menghapus pesan bot dari chat.
    """
    await callback.message.delete()
    await callback.answer()