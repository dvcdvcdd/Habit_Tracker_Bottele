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

logger = logging.getLogger(__name__)

router = Router()


def _build_welcome_text(first_name: str) -> str:
    day = weekday_name_today()
    date = format_date_display(today_str())

    return (
        f"Hei, *{first_name}!* 👋\n\n"
        f"Selamat datang di *Habit Tracker Bot*.\n\n"
        f"Bot ini membantu kamu membangun konsistensi "
        f"dengan cara yang sederhana dan tidak ribet.\n\n"
        f"Hari ini: _{day}, {date}_\n\n"
        f"Apa yang ingin kamu lakukan?"
    )


def _build_onboarding_text(first_name: str) -> str:
    return (
        f"Hei, *{first_name}!* 👋\n\n"
        f"Selamat datang di *Habit Tracker Bot*.\n\n"
        f"Saya akan bantu kamu membangun kebiasaan baik "
        f"dengan cara yang simpel.\n\n"
        f"*Cara kerjanya gampang:*\n\n"
        f"1️⃣ *Tambah habit* yang ingin kamu track\n"
        f"   Contoh: Olahraga, Baca buku, Meditasi\n\n"
        f"2️⃣ *Check-in setiap hari* saat kamu menyelesaikan habit\n"
        f"   Cukup tekan tombol, tidak perlu ketik apa-apa\n\n"
        f"3️⃣ *Pantau streak* dan statistik kamu\n"
        f"   Bot akan menghitung berapa hari berturut-turut kamu konsisten\n\n"
        f"4️⃣ *Terima reminder* setiap hari\n"
        f"   Supaya kamu tidak lupa check-in\n\n"
        f"💡 _Tips: mulai dengan 2-3 habit saja, jangan langsung banyak._\n\n"
        f"Yuk mulai dengan menambahkan habit pertamamu!"
    )


def _build_menu_text(first_name: str) -> str:
    return (
        f"Hei, *{first_name}!* 🏠\n\n"
        f"Kamu di menu utama.\n"
        f"Pilih yang ingin kamu lakukan:"
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

    # Cek apakah user baru (belum punya habit)
    habits = await get_habits(user.id, active_only=True)
    is_new_user = len(habits) == 0

    if is_new_user:
        # Cek apakah benar-benar baru atau pernah pakai tapi hapus semua
        existing_user = await get_user(user.id)
        if existing_user and existing_user.last_active == today_str():
            # Bukan user baru, hanya belum punya habit aktif
            is_new_user = False

    if is_new_user:
        # Tampilkan onboarding untuk user baru
        await message.answer(
            text=_build_onboarding_text(user.first_name),
            parse_mode="Markdown",
            reply_markup=kb_onboarding(),
        )
        return

    # User lama — cek comeback mode
    comeback_text = await get_comeback_text(user.id)

    if comeback_text:
        await message.answer(
            text=comeback_text,
            parse_mode="Markdown",
        )

    await message.answer(
        text=_build_welcome_text(user.first_name),
        parse_mode="Markdown",
        reply_markup=kb_main_menu(),
    )


@router.callback_query(lambda c: c.data == CB_ONBOARDING_SKIP)
async def handle_onboarding_skip(callback: CallbackQuery) -> None:
    user = callback.from_user

    await callback.message.edit_text(
        text=_build_menu_text(user.first_name),
        parse_mode="Markdown",
        reply_markup=kb_main_menu(),
    )
    await callback.answer()


@router.message(Command("menu"))
async def handle_menu_command(message: Message) -> None:
    user = message.from_user

    await message.answer(
        text=_build_menu_text(user.first_name),
        parse_mode="Markdown",
        reply_markup=kb_main_menu(),
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    help_text = (
        "*Cara pakai Habit Tracker Bot:*\n\n"
        "1️⃣ Tambahkan habit yang ingin kamu track\n"
        "2️⃣ Setiap hari, buka bot dan tekan *Check-in*\n"
        "3️⃣ Centang habit yang sudah kamu lakukan\n"
        "4️⃣ Pantau streak dan statistik kamu\n\n"
        "*Command yang tersedia:*\n"
        "/start     — buka menu utama\n"
        "/menu      — kembali ke menu utama\n"
        "/help      — tampilkan bantuan ini\n"
        "/profile   — lihat profile kamu\n"
        "/statistik — lihat statistik\n"
        "/summary   — ringkasan hari ini\n\n"
        "*Tips:*\n"
        "• Mulai dengan 2-3 habit saja\n"
        "• Check-in setiap hari meski hanya 1 habit\n"
        "• Streak yang pendek tapi konsisten lebih baik "
        "dari target besar yang tidak tercapai\n\n"
        "_Bot ini akan mengingatkan kamu setiap hari._"
    )

    await message.answer(
        text=help_text,
        parse_mode="Markdown",
        reply_markup=kb_main_menu(),
    )


@router.callback_query(lambda c: c.data == CB_BACK_MAIN)
async def handle_back_to_main(callback: CallbackQuery) -> None:
    user = callback.from_user

    await callback.message.edit_text(
        text=_build_menu_text(user.first_name),
        parse_mode="Markdown",
        reply_markup=kb_main_menu(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == CB_CLOSE)
async def handle_close(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.answer()