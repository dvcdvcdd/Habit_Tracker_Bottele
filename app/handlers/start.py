# app/handlers/start.py

import logging

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery, Message

from app.database.queries import upsert_user, get_user, get_habits
from app.keyboards.inline import (
    kb_main_menu,
    kb_onboarding,
    CB_BACK_MAIN,
    CB_CLOSE,
    CB_ONBOARDING_SKIP,
    CB_HABIT_ADD,
)
from app.services.stats_service import get_comeback_text
from app.utils.dates import weekday_name_today, format_date_display, today_str
from app.utils.helpers import esc

logger = logging.getLogger(__name__)

router = Router()

PARSE_MODE = "HTML"


def _build_welcome_text(first_name: str) -> str:
    day = weekday_name_today()
    date = format_date_display(today_str())
    return (
        f"<b>Selamat datang kembali, {esc(first_name)}!</b>\n\n"
        f"Hari ini: <i>{day}, {date}</i>\n\n"
        "Apa yang ingin kamu lakukan hari ini?"
    )


def _build_onboarding_text(first_name: str) -> str:
    return (
        f"<b>Selamat datang, {esc(first_name)}!</b>\n\n"
        "Selamat datang di <b>Habit Tracker</b> — "
        "alat untuk membangun kebiasaan baik secara konsisten.\n\n"
        "<b>Cara kerja:</b>\n\n"
        "1. <b>Tambah habit</b> yang ingin kamu jaga\n"
        "   Contoh: olahraga, membaca, meditasi\n\n"
        "2. <b>Check-in setiap hari</b> saat habit selesai dilakukan\n"
        "   Cukup satu ketukan tombol, tanpa perlu mengetik\n\n"
        "3. <b>Pantau streak dan statistik</b>\n"
        "   Konsistensi kamu dihitung dan dilaporkan otomatis\n\n"
        "4. <b>Terima reminder harian</b>\n"
        "   Pengingat agar tidak ada habit yang terlewat\n\n"
        "<i>Tips: mulailah dengan 2–3 habit saja.</i>\n\n"
        "Tambahkan habit pertamamu untuk memulai."
    )


def _build_menu_text(first_name: str) -> str:
    return (
        "<b>Menu Utama</b>\n\n"
        f"Selamat datang, {esc(first_name)}.\n"
        "Silakan pilih aksi di bawah ini."
    )


def _build_help_text() -> str:
    return (
        "<b>Pusat Bantuan</b>\n\n"
        "<b>Cara pakai</b>\n"
        "1. Tambahkan habit yang ingin kamu jaga\n"
        "2. Setiap hari, buka bot dan tekan <b>Check-in</b>\n"
        "3. Tandai habit yang sudah kamu lakukan\n"
        "4. Pantau streak dan statistik kamu\n\n"
        "<b>Perintah</b>\n"
        "<code>/start</code> — buka menu utama\n"
        "<code>/checkin</code> — check-in hari ini\n"
        "<code>/habits</code> — daftar habit\n"
        "<code>/statistik</code> — statistik harian dan mingguan\n"
        "<code>/summary</code> — ringkasan hari ini\n"
        "<code>/profile</code> — profile dan pengaturan\n"
        "<code>/help</code> — bantuan ini\n\n"
        "<b>Tips</b>\n"
        "• Mulai dengan 2–3 habit saja\n"
        "• Check-in setiap hari, meskipun hanya satu habit\n"
        "• Streak pendek yang konsisten lebih baik daripada "
        "target besar yang tidak tercapai\n\n"
        "<i>Bot akan mengingatkan kamu setiap hari "
        "sesuai jam reminder kamu.</i>"
    )


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    user = message.from_user

    await upsert_user(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )

    logger.info(f"User /start: {user.id} (@{user.username})")

    habits = await get_habits(user.id, active_only=True)
    is_new_user = len(habits) == 0

    if is_new_user:
        existing_user = await get_user(user.id)
        if existing_user and existing_user.last_active == today_str():
            is_new_user = False

    if is_new_user:
        await message.answer(
            text=_build_onboarding_text(user.first_name),
            parse_mode=PARSE_MODE,
            reply_markup=kb_onboarding(),
        )
        return

    comeback_text = await get_comeback_text(user.id)

    if comeback_text:
        await message.answer(
            text=comeback_text,
            parse_mode=PARSE_MODE,
        )

    await message.answer(
        text=_build_welcome_text(user.first_name),
        parse_mode=PARSE_MODE,
        reply_markup=kb_main_menu(),
    )


@router.callback_query(lambda c: c.data == CB_ONBOARDING_SKIP)
async def handle_onboarding_skip(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        text=_build_menu_text(callback.from_user.first_name),
        parse_mode=PARSE_MODE,
        reply_markup=kb_main_menu(),
    )
    await callback.answer()


@router.message(Command("menu"))
async def handle_menu_command(message: Message) -> None:
    await message.answer(
        text=_build_menu_text(message.from_user.first_name),
        parse_mode=PARSE_MODE,
        reply_markup=kb_main_menu(),
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(
        text=_build_help_text(),
        parse_mode=PARSE_MODE,
        reply_markup=kb_main_menu(),
    )


@router.callback_query(lambda c: c.data == CB_BACK_MAIN)
async def handle_back_to_main(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        text=_build_menu_text(callback.from_user.first_name),
        parse_mode=PARSE_MODE,
        reply_markup=kb_main_menu(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == CB_CLOSE)
async def handle_close(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.answer()
