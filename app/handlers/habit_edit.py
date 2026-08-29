# app/handlers/habit_edit.py

import logging
from datetime import date, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.database.queries import (
    get_habit_by_id_any_status,
    get_all_habits_including_paused,
    get_checkin_history_30days,
    update_habit_name,
    update_habit_schedule,
    pause_habit,
    resume_habit,
    soft_delete_habit,
    update_last_active,
)
from app.keyboards.inline import (
    CB_PREFIX_HABIT_DETAIL,
    CB_PREFIX_EDIT_NAME,
    CB_PREFIX_EDIT_SCHEDULE,
    CB_PREFIX_PAUSE,
    CB_PREFIX_RESUME,
    CB_PREFIX_DELETE,
    CB_PREFIX_DELETE_CONFIRM,
    CB_PREFIX_HISTORY,
    CB_MENU_HABITS,
    kb_habit_detail,
    kb_habit_picker,
    kb_edit_schedule,
    kb_back_to_main,
    kb_delete_confirm,
    kb_history_back,
)
from app.keyboards.reply import kb_cancel, kb_remove
from app.services.habit_service import (
    format_schedule_display,
    build_habit_list_text,
    get_habits_with_status,
)
from app.services.streak_service import is_habit_scheduled_today_for_date
from app.utils.helpers import (
    sanitize_text,
    is_valid_habit_name,
    esc,
    format_streak,
)
from app.utils.dates import today_str, format_date_display

logger = logging.getLogger(__name__)

router = Router()

PARSE_MODE = "HTML"


class EditHabitStates(StatesGroup):
    waiting_new_name = State()


async def _get_raw_active_status(habit_id: int, user_id: int) -> int:
    from app.database.init_db import get_db_connection
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT is_active FROM habits WHERE habit_id = ? AND user_id = ?",
            (habit_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return row["is_active"] if row else 0


# ---------------------------------------------------------------------------
# Daftar habit
# ---------------------------------------------------------------------------

async def _render_habit_list(user_id: int) -> tuple[str, object]:
    """
    Menyusun teks daftar habit beserta keyboard-nya.
    Dipakai bersama oleh tombol menu dan perintah /habits.
    """
    habits_with_status = await get_habits_with_status(user_id)
    text = build_habit_list_text(habits_with_status)

    all_habits = await get_all_habits_including_paused(user_id)

    if all_habits:
        text += "\n\n<i>Ketuk habit untuk melihat detail.</i>"
        reply_markup = kb_habit_picker(all_habits, CB_PREFIX_HABIT_DETAIL)
    else:
        reply_markup = kb_back_to_main()

    return text, reply_markup


@router.callback_query(lambda c: c.data == CB_MENU_HABITS)
async def handle_show_habits(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    text, reply_markup = await _render_habit_list(user_id)

    await callback.message.edit_text(
        text=text,
        parse_mode=PARSE_MODE,
        reply_markup=reply_markup,
    )
    await callback.answer()


@router.message(Command("habits"))
async def handle_habits_command(message: Message) -> None:
    """
    Menampilkan daftar habit via perintah /habits.
    """
    user_id = message.from_user.id

    text, reply_markup = await _render_habit_list(user_id)

    await message.answer(
        text=text,
        parse_mode=PARSE_MODE,
        reply_markup=reply_markup,
    )


# ---------------------------------------------------------------------------
# Detail satu habit
# ---------------------------------------------------------------------------

@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_HABIT_DETAIL}:")
)
async def handle_habit_detail(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    habit = await get_habit_by_id_any_status(habit_id, user_id)
    if habit is None:
        await callback.answer("Habit tidak ditemukan.", show_alert=True)
        return

    raw_status = await _get_raw_active_status(habit_id, user_id)
    is_paused = (raw_status == 2)

    schedule_text = format_schedule_display(habit.schedule)
    streak_text = format_streak(habit.current_streak)

    text = (
        "<b>Detail Habit</b>\n\n"
        "<code>"
        f"Nama    : {esc(habit.name)}\n"
        f"Jadwal  : {schedule_text}\n"
        f"Streak  : {streak_text}\n"
        f"Terbaik : {habit.longest_streak} hari\n"
        f"Status  : {'Dijeda' if is_paused else 'Aktif'}\n"
        f"Dibuat  : {habit.created_at}"
        "</code>"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode=PARSE_MODE,
        reply_markup=kb_habit_detail(habit_id, is_paused),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Riwayat 30 hari
# ---------------------------------------------------------------------------

@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_HISTORY}:")
)
async def handle_history(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    habit = await get_habit_by_id_any_status(habit_id, user_id)
    if habit is None:
        await callback.answer("Habit tidak ditemukan.", show_alert=True)
        return

    history = await get_checkin_history_30days(habit_id)

    calendar_text = _build_calendar_text(habit, history)

    await callback.message.edit_text(
        text=calendar_text,
        parse_mode=PARSE_MODE,
        reply_markup=kb_history_back(habit_id),
    )
    await callback.answer()


def _build_calendar_text(habit, history: dict) -> str:
    """
    Bangun tampilan kalender 30 hari.

    Format:
    Riwayat 30 Hari
    Habit: Olahraga
    1 Agustus — 29 Agustus 2026

    Sen Sel Rab Kam Jum Sab Min
     ■   ■   □   ■   ■   ·   ·
     ■   ■   ■   □   ■   ·   ·

    Total: 18/22 (82%)

    ■ check-in   □ terlewat   · bukan jadwal
    """
    end = date.fromisoformat(today_str())
    start = end - timedelta(days=29)

    lines = [
        "<b>Riwayat 30 Hari</b>",
        f"Habit: <b>{esc(habit.name)}</b>",
        f"<i>{format_date_display(start.isoformat())} — "
        f"{format_date_display(end.isoformat())}</i>",
        "",
        "<code>Sen Sel Rab Kam Jum Sab Min</code>",
    ]

    # Bangun grid per minggu
    current = start

    # Mulai dari Senin pertama
    first_weekday = current.weekday()  # 0=Senin
    if first_weekday > 0:
        # Tambah padding di awal
        current = current - timedelta(days=first_weekday)

    total_scheduled = 0
    total_done = 0
    row = ""

    while current <= end + timedelta(days=(6 - end.weekday())):
        date_str = current.isoformat()

        if current < start or current > end:
            # Di luar rentang 30 hari
            row += "  · "
        elif date_str in history:
            is_scheduled = is_habit_scheduled_today_for_date(
                habit.schedule, habit.custom_days, current
            )

            if is_scheduled:
                total_scheduled += 1
                if history[date_str]:
                    row += "  ■"
                    total_done += 1
                else:
                    row += "  □"
            else:
                # Bukan jadwal
                if history[date_str]:
                    row += "  ■"  # bonus check-in
                    total_done += 1
                else:
                    row += "  · "
        else:
            row += "  · "

        # Akhir minggu (Minggu)
        if current.weekday() == 6:
            lines.append(f"<code>{row}</code>")
            row = ""

        current += timedelta(days=1)

    # Sisa row yang belum ditambahkan
    if row:
        lines.append(f"<code>{row}</code>")

    # Statistik
    lines.append("")
    if total_scheduled > 0:
        pct = int((total_done / total_scheduled) * 100)
        lines.append(f"Total: <b>{total_done}/{total_scheduled}</b> ({pct}%)")
    else:
        lines.append(f"Total check-in: <b>{total_done}</b>")

    # Keterangan
    lines.append("")
    lines.append("■ check-in   □ terlewat   · bukan jadwal")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Edit Nama
# ---------------------------------------------------------------------------

@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_EDIT_NAME}:")
)
async def handle_edit_name_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    habit = await get_habit_by_id_any_status(habit_id, callback.from_user.id)
    if habit is None:
        await callback.answer("Habit tidak ditemukan.", show_alert=True)
        return

    await callback.message.edit_text(
        text=(
            "<b>Edit Nama Habit</b>\n\n"
            f"Nama sekarang: <b>{esc(habit.name)}</b>\n\n"
            "Ketik nama baru, atau tekan tombol <b>Batal</b> di keyboard."
        ),
        parse_mode=PARSE_MODE,
    )

    await callback.message.answer(
        text="Ketik nama baru atau tekan Batal:",
        reply_markup=kb_cancel(),
    )

    await state.update_data(edit_habit_id=habit_id)
    await state.set_state(EditHabitStates.waiting_new_name)
    await callback.answer()


@router.message(EditHabitStates.waiting_new_name)
async def handle_edit_name_input(
    message: Message,
    state: FSMContext,
) -> None:
    user_input = message.text.strip() if message.text else ""

    if user_input == "Batal":
        await state.clear()
        await message.answer(
            text="Perubahan nama dibatalkan.",
            reply_markup=kb_remove(),
        )
        await message.answer(
            text="<i>Kembali ke menu.</i>",
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

    data = await state.get_data()
    habit_id = data.get("edit_habit_id")

    if not habit_id:
        await state.clear()
        await message.answer(text="Terjadi kesalahan.", reply_markup=kb_remove())
        return

    user_id = message.from_user.id
    success = await update_habit_name(habit_id, user_id, clean_name)
    await state.clear()

    if success:
        await update_last_active(user_id)
        await message.answer(
            text=f'Nama habit berhasil diubah menjadi <b>"{esc(clean_name)}"</b>.',
            parse_mode=PARSE_MODE,
            reply_markup=kb_remove(),
        )
        logger.info(f"User {user_id} edit nama habit {habit_id} -> {clean_name}")
    else:
        await message.answer(
            text="<b>Gagal mengubah nama.</b> Silakan coba lagi.",
            parse_mode=PARSE_MODE,
            reply_markup=kb_remove(),
        )

    await message.answer(
        text="<i>Kembali ke menu.</i>",
        parse_mode=PARSE_MODE,
        reply_markup=kb_back_to_main(),
    )


# ---------------------------------------------------------------------------
# Edit Jadwal
# ---------------------------------------------------------------------------

@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_EDIT_SCHEDULE}:")
    and "_" not in c.data.split(":")[0].replace(CB_PREFIX_EDIT_SCHEDULE, "")
)
async def handle_edit_schedule_start(callback: CallbackQuery) -> None:
    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    habit = await get_habit_by_id_any_status(habit_id, callback.from_user.id)
    if habit is None:
        await callback.answer("Habit tidak ditemukan.", show_alert=True)
        return

    current_schedule = format_schedule_display(habit.schedule)

    await callback.message.edit_text(
        text=(
            "<b>Edit Jadwal</b>\n\n"
            f"Habit: <b>{esc(habit.name)}</b>\n"
            f"Jadwal sekarang: {current_schedule}\n\n"
            "Pilih jadwal baru:"
        ),
        parse_mode=PARSE_MODE,
        reply_markup=kb_edit_schedule(habit_id),
    )
    await callback.answer()


@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_EDIT_SCHEDULE}_")
)
async def handle_edit_schedule_pick(callback: CallbackQuery) -> None:
    try:
        parts = callback.data.split(":")
        habit_id = int(parts[1])
        schedule_raw = parts[0]
        schedule = schedule_raw.replace(f"{CB_PREFIX_EDIT_SCHEDULE}_", "")
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    user_id = callback.from_user.id
    success = await update_habit_schedule(habit_id, user_id, schedule)

    if success:
        await update_last_active(user_id)
        schedule_text = format_schedule_display(schedule)
        await callback.message.edit_text(
            text=(
                f"Jadwal berhasil diubah menjadi <b>{schedule_text}</b>.\n\n"
                "<i>Streak tetap terjaga.</i>"
            ),
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )
        logger.info(f"User {user_id} edit jadwal habit {habit_id} -> {schedule}")
    else:
        await callback.message.edit_text(
            text="<b>Gagal mengubah jadwal.</b> Silakan coba lagi.",
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )
    await callback.answer()


# ---------------------------------------------------------------------------
# Pause
# ---------------------------------------------------------------------------

@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_PAUSE}:")
)
async def handle_pause_habit(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    habit = await get_habit_by_id_any_status(habit_id, user_id)
    if habit is None:
        await callback.answer("Habit tidak ditemukan.", show_alert=True)
        return

    success = await pause_habit(habit_id, user_id)

    if success:
        await update_last_active(user_id)
        await callback.message.edit_text(
            text=(
                "<b>Habit Dijeda</b>\n\n"
                f"Habit <b>{esc(habit.name)}</b> tidak akan muncul "
                "di check-in harian sampai kamu mengaktifkannya kembali.\n\n"
                "<i>Streak kamu tetap aman selama dijeda.</i>"
            ),
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )
        logger.info(f"User {user_id} pause habit {habit_id}")
    else:
        await callback.message.edit_text(
            text="<b>Gagal menjeda habit.</b> Silakan coba lagi.",
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )
    await callback.answer()


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------

@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_RESUME}:")
)
async def handle_resume_habit(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    habit = await get_habit_by_id_any_status(habit_id, user_id)
    if habit is None:
        await callback.answer("Habit tidak ditemukan.", show_alert=True)
        return

    success = await resume_habit(habit_id, user_id)

    if success:
        await update_last_active(user_id)
        await callback.message.edit_text(
            text=(
                "<b>Habit Aktif Kembali</b>\n\n"
                f"Habit <b>{esc(habit.name)}</b> sudah aktif lagi.\n\n"
                f"<i>Streak sebelumnya: {format_streak(habit.current_streak)}</i>"
            ),
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )
        logger.info(f"User {user_id} resume habit {habit_id}")
    else:
        await callback.message.edit_text(
            text="<b>Gagal mengaktifkan habit.</b> Silakan coba lagi.",
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )
    await callback.answer()


# ---------------------------------------------------------------------------
# Hapus
# ---------------------------------------------------------------------------

@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_DELETE}:")
    and "confirm" not in c.data
)
async def handle_delete_from_detail(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    habit = await get_habit_by_id_any_status(habit_id, user_id)
    if habit is None:
        await callback.answer("Habit tidak ditemukan.", show_alert=True)
        return

    schedule_display = format_schedule_display(habit.schedule)

    await callback.message.edit_text(
        text=(
            "<b>Konfirmasi Hapus</b>\n\n"
            f"Habit <b>{esc(habit.name)}</b> akan dihapus secara permanen.\n\n"
            "<code>"
            f"Jadwal : {schedule_display}\n"
            f"Streak : {habit.current_streak} hari"
            "</code>\n\n"
            "<i>Riwayat streak akan ikut hilang. "
            "Tindakan ini tidak dapat dibatalkan.</i>"
        ),
        parse_mode=PARSE_MODE,
        reply_markup=kb_delete_confirm(habit_id, habit.name),
    )
    await callback.answer()


@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_DELETE_CONFIRM}:")
)
async def handle_delete_confirm(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    habit = await get_habit_by_id_any_status(habit_id, user_id)
    success = await soft_delete_habit(habit_id, user_id)

    if success:
        await update_last_active(user_id)
        habit_name = habit.name if habit else "Habit"
        await callback.message.edit_text(
            text=f"Habit <b>{esc(habit_name)}</b> berhasil dihapus.",
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )
        logger.info(f"User {user_id} hapus habit {habit_id}")
    else:
        await callback.message.edit_text(
            text="<b>Gagal menghapus habit.</b> Silakan coba lagi.",
            parse_mode=PARSE_MODE,
            reply_markup=kb_back_to_main(),
        )
    await callback.answer()
