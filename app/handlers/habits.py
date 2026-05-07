import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards.inline import (
    CB_HABIT_ADD,
    CB_HABIT_DELETE,
    CB_HABIT_LIST,
    CB_MENU_HABITS,
    CB_PREFIX_DELETE,
    CB_PREFIX_DELETE_CONFIRM,
    CB_PREFIX_SCHEDULE,
    kb_back_to_main,
    kb_delete_confirm,
    kb_delete_habit_picker,
    kb_habit_list_menu,
    kb_schedule_picker,
)
from app.keyboards.reply import kb_cancel, kb_remove
from app.database.queries import get_habits, get_habit_by_id
from app.services.habit_service import (
    add_habit,
    build_habit_list_text,
    get_habits_with_status,
    remove_habit,
    format_schedule_display,
)
from app.utils.enums import SCHEDULE_DISPLAY, HabitSchedule

logger = logging.getLogger(__name__)

router = Router()

class AddHabitStates(StatesGroup):
    """
    State untuk proses tambah habit.
    Urutan: waiting_name → waiting_schedule → (selesai)
    """
    waiting_name     = State()
    waiting_schedule = State()

@router.callback_query(lambda c: c.data == CB_MENU_HABITS)
async def handle_show_habits(callback: CallbackQuery) -> None:
    """
    Menampilkan daftar semua habit user.
    Dipanggil saat user menekan tombol 'Habit Saya' di menu utama.
    """
    user_id = callback.from_user.id

    habits_with_status = await get_habits_with_status(user_id)
    text               = build_habit_list_text(habits_with_status)

    await callback.message.edit_text(
        text         = text,
        parse_mode   = "Markdown",
        reply_markup = kb_habit_list_menu(),
    )

    await callback.answer()

@router.callback_query(lambda c: c.data == CB_HABIT_ADD)
async def handle_add_habit_start(
    callback: CallbackQuery,
    state:    FSMContext,
) -> None:
    """
    Langkah 1: User menekan tombol 'Tambah Habit'.
    Bot meminta nama habit.
    State berubah ke waiting_name.
    """
    # Hapus keyboard inline dari pesan sebelumnya
    await callback.message.edit_text(
        text       = (
            "➕ *Tambah Habit Baru*\n\n"
            "Ketik nama habit yang ingin kamu track.\n\n"
            "Contoh:\n"
            "• Olahraga\n"
            "• Baca buku 20 menit\n"
            "• Minum 8 gelas air\n"
            "• Meditasi\n\n"
            "_Maksimal 50 karakter._"
        ),
        parse_mode = "Markdown",
    )

    # Tampilkan reply keyboard dengan tombol Batal
    await callback.message.answer(
        text         = "Ketik nama habit kamu:",
        reply_markup = kb_cancel(),
    )

    # Set state FSM
    await state.set_state(AddHabitStates.waiting_name)
    await callback.answer()


@router.message(AddHabitStates.waiting_name)
async def handle_habit_name_input(
    message: Message,
    state:   FSMContext,
) -> None:
    """
    Langkah 2: User mengetik nama habit.
    """
    from app.utils.helpers import sanitize_text, is_valid_habit_name, escape_markdown

    user_input = message.text.strip() if message.text else ""

    # Cek apakah user menekan Batal
    if user_input == "❌ Batal":
        await state.clear()
        await message.answer(
            text         = "Dibatalkan.",
            reply_markup = kb_remove(),
        )
        await message.answer(
            text         = "Kamu di menu utama:",
            parse_mode   = "Markdown",
            reply_markup = kb_back_to_main(),
        )
        return

    # Sanitasi dan validasi input
    clean_name           = sanitize_text(user_input)
    is_valid, error_msg  = is_valid_habit_name(clean_name)

    if not is_valid:
        await message.answer(
            text         = f"⚠️ {error_msg}\n\nCoba lagi:",
            reply_markup = kb_cancel(),
        )
        return  # Tetap di state waiting_name

    # Simpan nama yang sudah disanitasi ke FSM storage
    await state.update_data(habit_name=clean_name)

    # Tampilkan konfirmasi nama
    safe_name = escape_markdown(clean_name)
    await message.answer(
        text         = f'Nama habit: *"{safe_name}"*',
        parse_mode   = "Markdown",
        reply_markup = kb_remove(),
    )

    # Tampilkan pilihan jadwal
    await message.answer(
        text         = (
            "📅 *Pilih jadwal habit ini:*\n\n"
            "Kapan kamu ingin melakukan habit ini?"
        ),
        parse_mode   = "Markdown",
        reply_markup = kb_schedule_picker(),
    )

    await state.set_state(AddHabitStates.waiting_schedule)


@router.callback_query(
    AddHabitStates.waiting_schedule,
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_SCHEDULE}:"),
)
async def handle_schedule_picked(
    callback: CallbackQuery,
    state:    FSMContext,
) -> None:
    """
    Langkah 3: User memilih jadwal habit.

    Ambil data nama dari FSM, buat habit baru di database,
    tampilkan konfirmasi, lalu clear state.
    """
    user_id = callback.from_user.id

    # Parse schedule dari callback data
    # Format: "schedule:everyday"
    schedule = callback.data.split(":")[1]

    # Ambil nama habit yang disimpan di state
    data       = await state.get_data()
    habit_name = data.get("habit_name", "")

    if not habit_name:
        await callback.answer("Terjadi kesalahan. Coba lagi.", show_alert=True)
        await state.clear()
        return

    # Buat habit baru via service
    success, message_text, habit_id = await add_habit(
        user_id  = user_id,
        name     = habit_name,
        schedule = schedule,
    )

    # Clear state setelah selesai
    await state.clear()

    if success:
        schedule_display = format_schedule_display(schedule)

        await callback.message.edit_text(
            text = (
                f"✅ *Habit berhasil ditambahkan!*\n\n"
                f"📌 Nama    : *{habit_name}*\n"
                f"📅 Jadwal  : {schedule_display}\n\n"
                f"_Sekarang kamu bisa mulai check-in habit ini._"
            ),
            parse_mode   = "Markdown",
            reply_markup = kb_back_to_main(),
        )
    else:
        await callback.message.edit_text(
            text         = f"⚠️ {message_text}",
            parse_mode   = "Markdown",
            reply_markup = kb_back_to_main(),
        )

    await callback.answer()

@router.callback_query(lambda c: c.data == CB_HABIT_DELETE)
async def handle_delete_start(callback: CallbackQuery) -> None:
    """
    Langkah 1: User menekan tombol 'Hapus Habit'.
    Tampilkan daftar habit untuk dipilih.
    """
    user_id = callback.from_user.id
    habits  = await get_habits(user_id, active_only=True)

    if not habits:
        await callback.message.edit_text(
            text         = (
                "📭 *Belum ada habit*\n\n"
                "Kamu belum punya habit yang bisa dihapus."
            ),
            parse_mode   = "Markdown",
            reply_markup = kb_back_to_main(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        text         = (
            "🗑 *Hapus Habit*\n\n"
            "Pilih habit yang ingin dihapus:\n\n"
            "⚠️ _Data checkin lama tetap tersimpan "
            "untuk keperluan statistik._"
        ),
        parse_mode   = "Markdown",
        reply_markup = kb_delete_habit_picker(habits),
    )

    await callback.answer()


@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_DELETE}:"),
)
async def handle_delete_pick(callback: CallbackQuery) -> None:
    """
    Langkah 2: User memilih habit yang akan dihapus.
    Tampilkan konfirmasi.
    """
    user_id  = callback.from_user.id

    # Parse habit_id dari callback data
    # Format: "delete:42"
    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    # Ambil detail habit untuk konfirmasi
    habit = await get_habit_by_id(habit_id, user_id)

    if habit is None:
        await callback.answer("Habit tidak ditemukan.", show_alert=True)
        return

    schedule_display = format_schedule_display(habit.schedule)

    await callback.message.edit_text(
        text = (
            f"🗑 *Konfirmasi Hapus*\n\n"
            f"Kamu yakin ingin menghapus habit ini?\n\n"
            f"📌 Nama   : *{habit.name}*\n"
            f"📅 Jadwal : {schedule_display}\n"
            f"🔥 Streak : {habit.current_streak} hari\n\n"
            f"⚠️ _Streak akan hilang. "
            f"Checkin lama tetap tersimpan._"
        ),
        parse_mode   = "Markdown",
        reply_markup = kb_delete_confirm(habit_id, habit.name),
    )

    await callback.answer()


@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_DELETE_CONFIRM}:"),
)
async def handle_delete_confirm(callback: CallbackQuery) -> None:
    """
    Langkah 3: User mengkonfirmasi penghapusan.
    Lakukan soft delete dan tampilkan hasil.
    """
    user_id = callback.from_user.id

    # Parse habit_id
    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    # Lakukan penghapusan via service
    success, message_text = await remove_habit(user_id, habit_id)

    if success:
        await callback.message.edit_text(
            text         = f"✅ {message_text}",
            parse_mode   = "Markdown",
            reply_markup = kb_back_to_main(),
        )
    else:
        await callback.message.edit_text(
            text         = f"⚠️ {message_text}",
            parse_mode   = "Markdown",
            reply_markup = kb_back_to_main(),
        )

    await callback.answer()