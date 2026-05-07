# app/handlers/profile.py

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.database.queries import (
    get_user,
    get_habits,
    update_user_reminder,
    update_last_active,
    get_total_checkins,
    get_total_active_days,
    get_best_streak_ever,
)
from app.keyboards.inline import (
    CB_MENU_PROFILE,
    CB_REMINDER_SET,
    kb_profile_menu,
    kb_back_to_main,
)
from app.keyboards.reply import kb_cancel, kb_remove
from app.utils.dates import format_date_display

logger = logging.getLogger(__name__)

router = Router()


# ---------------------------------------------------------------------------
# FSM untuk ubah jam reminder
# ---------------------------------------------------------------------------

class ReminderStates(StatesGroup):
    waiting_time = State()


# ---------------------------------------------------------------------------
# Tampilkan profile
# ---------------------------------------------------------------------------

async def _build_profile_text(user_id: int) -> str:
    """
    Bangun teks profile lengkap.
    """
    user = await get_user(user_id)
    if user is None:
        return "❌ Data profile tidak ditemukan."

    habits         = await get_habits(user_id, active_only=True)
    total_checkins = await get_total_checkins(user_id)
    active_days    = await get_total_active_days(user_id)
    best_streak    = await get_best_streak_ever(user_id)

    # Format data
    name     = user.first_name
    username = f"@{user.username}" if user.username else "tidak diset"
    joined   = format_date_display(user.created_at)
    reminder = user.reminder_time
    total_h  = len(habits)

    # Best streak display
    if best_streak:
        streak_name, streak_val = best_streak
        streak_text = f"{streak_val} hari ({streak_name})"
    else:
        streak_text = "belum ada"

    text = (
        f"👤 *Profile Kamu*\n"
        f"\n"
        f"📛 Nama      : *{name}*\n"
        f"🆔 Username  : {username}\n"
        f"📅 Bergabung : {joined}\n"
        f"🕐 Reminder  : {reminder} WIB\n"
        f"\n"
        f"📊 *Ringkasan*\n"
        f"├ Habit aktif        : *{total_h}*\n"
        f"├ Total check-in     : *{total_checkins}*\n"
        f"├ Hari aktif         : *{active_days}*\n"
        f"└ Streak terpanjang  : *{streak_text}*\n"
        f"\n"
        f"_Ketuk tombol di bawah untuk mengubah pengaturan._"
    )

    return text


@router.callback_query(lambda c: c.data == CB_MENU_PROFILE)
async def handle_show_profile(callback: CallbackQuery) -> None:
    """
    Tampilkan profile via tombol menu.
    """
    user_id = callback.from_user.id
    text    = await _build_profile_text(user_id)

    await callback.message.edit_text(
        text         = text,
        parse_mode   = "Markdown",
        reply_markup = kb_profile_menu(),
    )
    await callback.answer()


@router.message(Command("profile"))
async def handle_profile_command(message: Message) -> None:
    """
    Tampilkan profile via command /profile.
    """
    user_id = message.from_user.id
    text    = await _build_profile_text(user_id)

    await message.answer(
        text         = text,
        parse_mode   = "Markdown",
        reply_markup = kb_profile_menu(),
    )


# ---------------------------------------------------------------------------
# Ubah jam reminder
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data == CB_REMINDER_SET)
async def handle_reminder_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """
    User menekan tombol ubah reminder.
    Bot minta input jam baru.
    """
    user = await get_user(callback.from_user.id)
    current_time = user.reminder_time if user else "19:00"

    await callback.message.edit_text(
        text=(
            f"⏰ *Ubah Jam Reminder*\n\n"
            f"Jam reminder kamu sekarang: *{current_time}*\n\n"
            f"Ketik jam baru dalam format *HH:MM*\n\n"
            f"Contoh:\n"
            f"• `06:00` — pagi hari\n"
            f"• `12:30` — siang\n"
            f"• `19:00` — malam\n"
            f"• `21:30` — sebelum tidur"
        ),
        parse_mode="Markdown",
    )

    await callback.message.answer(
        text="Ketik jam reminder baru:",
        reply_markup=kb_cancel(),
    )

    await state.set_state(ReminderStates.waiting_time)
    await callback.answer()


@router.message(ReminderStates.waiting_time)
async def handle_reminder_input(
    message: Message,
    state: FSMContext,
) -> None:
    """
    User mengetik jam baru.
    Validasi format, simpan ke database.
    """
    user_input = message.text.strip()

    # Cek batal
    if user_input == "❌ Batal":
        await state.clear()
        await message.answer(
            text="Dibatalkan.",
            reply_markup=kb_remove(),
        )
        text = await _build_profile_text(message.from_user.id)
        await message.answer(
            text=text,
            parse_mode="Markdown",
            reply_markup=kb_profile_menu(),
        )
        return

    # Validasi format HH:MM
    if not _is_valid_time(user_input):
        await message.answer(
            text=(
                "⚠️ Format tidak valid.\n\n"
                "Gunakan format *HH:MM* dengan angka 00-23 untuk jam "
                "dan 00-59 untuk menit.\n\n"
                "Contoh: `19:00`, `06:30`, `21:45`"
            ),
            parse_mode="Markdown",
            reply_markup=kb_cancel(),
        )
        return

    # Simpan ke database
    user_id = message.from_user.id
    await update_user_reminder(user_id, user_input)
    await update_last_active(user_id)
    await state.clear()

    await message.answer(
        text=f"✅ Jam reminder berhasil diubah ke *{user_input}* WIB.",
        parse_mode="Markdown",
        reply_markup=kb_remove(),
    )

    # Tampilkan profile yang sudah diperbarui
    text = await _build_profile_text(user_id)
    await message.answer(
        text=text,
        parse_mode="Markdown",
        reply_markup=kb_profile_menu(),
    )

    logger.info(f"User {user_id} ubah reminder ke {user_input}")


def _is_valid_time(time_str: str) -> bool:
    """
    Validasi format jam HH:MM.
    """
    if ":" not in time_str:
        return False

    parts = time_str.split(":")
    if len(parts) != 2:
        return False

    try:
        hour   = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return False

    return 0 <= hour <= 23 and 0 <= minute <= 59