# app/handlers/habits.py

import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards.inline import (
    CB_HABIT_ADD,
    CB_PREFIX_SCHEDULE,
    kb_back_to_main,
    kb_schedule_picker,
)
from app.keyboards.reply import kb_cancel, kb_remove
from app.services.habit_service import add_habit, format_schedule_display
from app.utils.helpers import sanitize_text, is_valid_habit_name, esc

logger = logging.getLogger(__name__)

router = Router()

PARSE_MODE = "HTML"


class AddHabitStates(StatesGroup):
    waiting_name     = State()
    waiting_schedule = State()


@router.callback_query(lambda c: c.data == CB_HABIT_ADD)
async def handle_add_habit_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.message.edit_text(
        text=(
            "<b>Tambah Habit Baru</b>\n\n"
            "Ketik nama habit yang ingin kamu jaga.\n\n"
            "Contoh:\n"
            "• Olahraga\n"
            "• Baca buku 20 menit\n"
            "• Minum 8 gelas air\n"
            "• Meditasi\n\n"
            "<i>Maksimal 50 karakter.</i>"
        ),
        parse_mode=PARSE_MODE,
    )

    await callback.message.answer(
        text="Ketik nama habit kamu:",
        reply_markup=kb_cancel(),
    )

    await state.set_state(AddHabitStates.waiting_name)
    await callback.answer()


@router.message(AddHabitStates.waiting_name)
async def handle_habit_name_input(
    message: Message,
    state: FSMContext,
) -> None:
    user_input = message.text.strip() if message.text else ""

    if user_input == "Batal":
        await state.clear()
        await message.answer(
            text="Pembuatan habit dibatalkan.",
            reply_markup=kb_remove(),
        )
        await message.answer(
            text="<i>Kamu berada di menu utama.</i>",
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )
        return

    clean_name = sanitize_text(user_input)
    is_valid, error_msg = is_valid_habit_name(clean_name)

    if not is_valid:
        await message.answer(
            text=f"<b>{esc(error_msg)}</b>\n\nSilakan coba lagi:",
            parse_mode=PARSE_MODE,
            reply_markup=kb_cancel(),
        )
        return

    await state.update_data(habit_name=clean_name)

    await message.answer(
        text=f'Nama habit: <b>"{esc(clean_name)}"</b>',
        parse_mode=PARSE_MODE,
        reply_markup=kb_remove(),
    )

    await message.answer(
        text=(
            "<b>Pilih Jadwal</b>\n\n"
            "Kapan kamu akan melakukan habit ini?"
        ),
        parse_mode=PARSE_MODE,
        reply_markup=kb_schedule_picker(),
    )

    await state.set_state(AddHabitStates.waiting_schedule)


@router.callback_query(
    AddHabitStates.waiting_schedule,
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_SCHEDULE}:"),
)
async def handle_schedule_picked(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    user_id = callback.from_user.id
    schedule = callback.data.split(":")[1]

    data = await state.get_data()
    habit_name = data.get("habit_name", "")

    if not habit_name:
        await callback.answer("Terjadi kesalahan. Silakan coba lagi.", show_alert=True)
        await state.clear()
        return

    success, message_text, habit_id = await add_habit(
        user_id=user_id,
        name=habit_name,
        schedule=schedule,
    )

    await state.clear()

    if success:
        schedule_display = format_schedule_display(schedule)

        await callback.message.edit_text(
            text=(
                "<b>Habit Berhasil Ditambahkan</b>\n\n"
                f"Nama   : <b>{esc(habit_name)}</b>\n"
                f"Jadwal : {schedule_display}\n\n"
                "Kamu bisa mulai check-in sesuai jadwal habit ini."
            ),
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )
    else:
        await callback.message.edit_text(
            text=f"<b>{esc(message_text)}</b>",
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )

    await callback.answer()
