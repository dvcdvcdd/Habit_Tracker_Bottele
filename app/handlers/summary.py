# app/handlers/summary.py

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards.inline import (
    CB_MENU_SUMMARY,
    kb_back_to_main,
    kb_checkin_habits,
)
from app.services.stats_service import get_daily_summary_text
from app.services.habit_service import get_today_habits_with_status

logger = logging.getLogger(__name__)

router = Router()

PARSE_MODE = "HTML"


async def _render_daily_summary(user_id: int):
    """
    Menyusun teks ringkasan harian beserta keyboard-nya.
    Dipakai bersama oleh tombol menu dan perintah /summary.
    """
    text         = await get_daily_summary_text(user_id)
    habits_today = await get_today_habits_with_status(user_id)
    pending      = [h for h in habits_today if not h.is_done_today]

    if pending:
        reply_markup = kb_checkin_habits(pending)
    else:
        reply_markup = kb_back_to_main()

    return text, reply_markup


@router.callback_query(lambda c: c.data == CB_MENU_SUMMARY)
async def handle_show_summary(callback: CallbackQuery) -> None:
    """
    Menampilkan ringkasan harian via tombol menu.
    """
    user_id = callback.from_user.id

    await callback.answer("Memuat ringkasan...")

    text, reply_markup = await _render_daily_summary(user_id)

    await callback.message.edit_text(
        text=text,
        parse_mode=PARSE_MODE,
        reply_markup=reply_markup,
    )


@router.message(Command("summary"))
async def handle_summary_command(message: Message) -> None:
    """
    Menampilkan daily summary via command /summary.
    """
    user_id = message.from_user.id

    text, reply_markup = await _render_daily_summary(user_id)

    await message.answer(
        text=text,
        parse_mode=PARSE_MODE,
        reply_markup=reply_markup,
    )
