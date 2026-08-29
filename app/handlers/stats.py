# app/handlers/stats.py

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards.inline import (
    CB_MENU_STATS,
    kb_stats_menu,
)
from app.services.stats_service import build_full_stats_text

logger = logging.getLogger(__name__)

router = Router()

PARSE_MODE = "HTML"


@router.callback_query(lambda c: c.data == CB_MENU_STATS)
async def handle_show_stats(callback: CallbackQuery) -> None:
    """
    Menampilkan statistik lengkap via tombol menu.
    """
    user_id = callback.from_user.id

    await callback.answer("Memuat statistik...")

    text = await build_full_stats_text(user_id)

    await callback.message.edit_text(
        text=text,
        parse_mode=PARSE_MODE,
        reply_markup=kb_stats_menu(),
    )


@router.message(Command("statistik"))
async def handle_stats_command(message: Message) -> None:
    """
    Menampilkan statistik via command /statistik.
    """
    user_id = message.from_user.id
    text    = await build_full_stats_text(user_id)

    await message.answer(
        text=text,
        parse_mode=PARSE_MODE,
        reply_markup=kb_stats_menu(),
    )
