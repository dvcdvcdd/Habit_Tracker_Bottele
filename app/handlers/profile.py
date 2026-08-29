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
from app.utils.helpers import esc

logger = logging.getLogger(__name__)

router = Router()

PARSE_MODE = "HTML"


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
        return "<b>Data profile tidak ditemukan.</b>"

    habits         = await get_habits(user_id, active_only=True)
    total_checkins = await get_total_checkins(user_id)
    active_days    = await get_total_active_days(user_id)
    best_streak    = await get_best_streak_ever(user_id)

    # Format data
    name     = user.first_name
    username = f"@{user.username}" if user.username else "belum diset"
    joined   = format_date_display(user.created_at)
    reminder = user.reminder_time
    total_h  = len(habits)

    # Best streak display
    if best_streak:
        streak_name, streak_val = best_streak
        streak_text = f"{streak_val} hari ({esc(streak_name)})"
    else:
        streak_text = "belum ada"

    text = (
        "<b>Profile</b>\n\n"
        "<code>"
        f"Nama      : {esc(name)}\n"
        f"Username  : {esc(username)}\n"
        f"Bergabung : {joined}\n"
        f"Reminder  : {reminder} WIB"
        "</code>\n\n"
        "<b>Ringkasan</b>\n\n"
        "<code>"
        f"Habit aktif       : {total_h}\n"
        f"Total check-in    : {total_checkins}\n"
        f"Hari aktif        : {active_days}\n"
        f"Streak terpanjang : {streak_text}"
        "</code>\n\n"
        "<i>Gunakan tombol di bawah untuk mengubah pengaturan.</i>"
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
        text=text,
        parse_mode=PARSE_MODE,
        reply_markup=kb_profile_menu(),
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
        text=text,
        parse_mode=PARSE_MODE,
        reply_markup=kb_profile_menu(),
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
            "<b>Ubah Jam Reminder</b>\n\n"
            f"Jam reminder saat ini: <b>{current_time}</b>\n\n"
            "Ketik jam baru dengan format <b>HH:MM</b>.\n\n"
            "Contoh:\n"
            "<code>06:00</code> — pagi hari\n"
            "<code>12:30</code> — siang\n"
            "<code>19:00</code> — malam\n"
            "<code>21:30</code> — sebelum tidur"
        ),
        parse_mode=PARSE_MODE,
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
    if user_input == "Batal":
        await state.clear()
        await message.answer(
            text="Perubahan reminder dibatalkan.",
            reply_markup=kb_remove(),
        )
        text = await _build_profile_text(message.from_user.id)
        await message.answer(
            text=text,
            parse_mode=PARSE_MODE,
            reply_markup=kb_profile_menu(),
        )
        return

    # Validasi format HH:MM
    if not _is_valid_time(user_input):
        await message.answer(
            text=(
                "<b>Format tidak valid.</b>\n\n"
                "Gunakan format <b>HH:MM</b> — jam 00–23, menit 00–59.\n\n"
                "Contoh: <code>19:00</code>, <code>06:30</code>, <code>21:45</code>"
            ),
            parse_mode=PARSE_MODE,
            reply_markup=kb_cancel(),
        )
        return

    # Simpan ke database
    user_id = message.from_user.id
    await update_user_reminder(user_id, user_input)
    await update_last_active(user_id)
    await state.clear()

    await message.answer(
        text=f"Jam reminder berubah menjadi <b>{user_input}</b> WIB.",
        parse_mode=PARSE_MODE,
        reply_markup=kb_remove(),
    )

    # Tampilkan profile yang sudah diperbarui
    text = await _build_profile_text(user_id)
    await message.answer(
        text=text,
        parse_mode=PARSE_MODE,
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
