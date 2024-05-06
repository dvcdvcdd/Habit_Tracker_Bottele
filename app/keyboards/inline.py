# app/keyboards/inline.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.enums import HabitSchedule, SCHEDULE_DISPLAY
from app.utils.helpers import chunk_list, truncate


# ===========================================================================
# SECTION 1 — CALLBACK DATA CONSTANTS
# ===========================================================================

CB_MENU_MAIN        = "menu:main"
CB_MENU_CHECKIN     = "menu:checkin"
CB_MENU_HABITS      = "menu:habits"
CB_MENU_STATS       = "menu:stats"
CB_MENU_SUMMARY     = "menu:summary"
CB_MENU_PROFILE     = "menu:profile"

CB_HABIT_ADD        = "habit:add"
CB_HABIT_LIST       = "habit:list"
CB_HABIT_DELETE     = "habit:delete"

CB_PREFIX_CHECKIN         = "checkin"
CB_PREFIX_DELETE          = "delete"
CB_PREFIX_DELETE_CONFIRM  = "delete_confirm"
CB_PREFIX_DELETE_CANCEL   = "delete_cancel"

CB_PREFIX_HABIT_DETAIL   = "habit_detail"
CB_PREFIX_EDIT_NAME      = "edit_name"
CB_PREFIX_EDIT_SCHEDULE  = "edit_schedule"
CB_PREFIX_PAUSE          = "pause"
CB_PREFIX_RESUME         = "resume"
CB_PREFIX_HISTORY        = "history"

CB_PREFIX_SCHEDULE  = "schedule"

CB_BACK_MAIN        = "nav:main"
CB_CLOSE            = "nav:close"

CB_REMINDER_SET     = "reminder:set"

CB_ONBOARDING_SKIP  = "onboarding:skip"


# ===========================================================================
# SECTION 2 — MENU UTAMA
# ===========================================================================

def kb_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Check-in Hari Ini",
            callback_data=CB_MENU_CHECKIN,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📋 Habit Saya",
            callback_data=CB_MENU_HABITS,
        ),
        InlineKeyboardButton(
            text="➕ Tambah Habit",
            callback_data=CB_HABIT_ADD,
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="📊 Statistik",
            callback_data=CB_MENU_STATS,
        ),
        InlineKeyboardButton(
            text="📝 Summary",
            callback_data=CB_MENU_SUMMARY,
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="👤 Profile",
            callback_data=CB_MENU_PROFILE,
        ),
    )

    return builder.as_markup()


def kb_onboarding() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ Tambah Habit Pertama",
            callback_data=CB_HABIT_ADD,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="⏭ Lewati, Langsung ke Menu",
            callback_data=CB_ONBOARDING_SKIP,
        )
    )

    return builder.as_markup()


# ===========================================================================
# SECTION 3 — CHECK-IN
# ===========================================================================

def kb_checkin_habits(habits: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for item in habits:
        icon = "✅" if item.is_done_today else "⬜"
        name = truncate(item.habit.name, 28)

        builder.row(
            InlineKeyboardButton(
                text=f"{icon} {name}",
                callback_data=f"{CB_PREFIX_CHECKIN}:{item.habit.habit_id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🏠 Menu Utama",
            callback_data=CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


def kb_checkin_done() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📊 Lihat Statistik",
            callback_data=CB_MENU_STATS,
        ),
        InlineKeyboardButton(
            text="🏠 Menu Utama",
            callback_data=CB_BACK_MAIN,
        ),
    )

    return builder.as_markup()


# ===========================================================================
# SECTION 4 — HABIT MANAGEMENT
# ===========================================================================

def kb_habit_list_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ Tambah Habit",
            callback_data=CB_HABIT_ADD,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🗑 Hapus Habit",
            callback_data=CB_HABIT_DELETE,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🏠 Menu Utama",
            callback_data=CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


def kb_delete_habit_picker(habits: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    buttons = [
        InlineKeyboardButton(
            text=truncate(h.name, 20),
            callback_data=f"{CB_PREFIX_DELETE}:{h.habit_id}",
        )
        for h in habits
    ]

    for row_buttons in chunk_list(buttons, 2):
        builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(
            text="❌ Batal",
            callback_data=CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


def kb_delete_confirm(habit_id: int, habit_name: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Ya, Hapus",
            callback_data=f"{CB_PREFIX_DELETE_CONFIRM}:{habit_id}",
        ),
        InlineKeyboardButton(
            text="❌ Batal",
            callback_data=CB_BACK_MAIN,
        ),
    )

    return builder.as_markup()


def kb_habit_picker(habits: list, callback_prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    buttons = [
        InlineKeyboardButton(
            text=truncate(h.name, 25),
            callback_data=f"{callback_prefix}:{h.habit_id}",
        )
        for h in habits
    ]

    for row_buttons in chunk_list(buttons, 2):
        builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(
            text="🏠 Menu Utama",
            callback_data=CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


def kb_habit_detail(habit_id: int, is_paused: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📅 Riwayat 30 Hari",
            callback_data=f"{CB_PREFIX_HISTORY}:{habit_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="✏️ Edit Nama",
            callback_data=f"{CB_PREFIX_EDIT_NAME}:{habit_id}",
        ),
        InlineKeyboardButton(
            text="📅 Edit Jadwal",
            callback_data=f"{CB_PREFIX_EDIT_SCHEDULE}:{habit_id}",
        ),
    )

    if is_paused:
        builder.row(
            InlineKeyboardButton(
                text="▶️ Aktifkan Kembali",
                callback_data=f"{CB_PREFIX_RESUME}:{habit_id}",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="⏸ Pause Habit",
                callback_data=f"{CB_PREFIX_PAUSE}:{habit_id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🗑 Hapus",
            callback_data=f"{CB_PREFIX_DELETE}:{habit_id}",
        ),
        InlineKeyboardButton(
            text="🔙 Kembali",
            callback_data=CB_MENU_HABITS,
        ),
    )

    return builder.as_markup()


def kb_edit_schedule(habit_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    schedule_options = [
        (HabitSchedule.EVERYDAY,    "📅 Setiap Hari"),
        (HabitSchedule.WEEKDAY,     "💼 Senin – Jumat"),
        (HabitSchedule.MON_WED_FRI, "🔄 Senin, Rabu, Jumat"),
        (HabitSchedule.TUE_THU_SAT, "🔄 Selasa, Kamis, Sabtu"),
        (HabitSchedule.WEEKEND,     "🎉 Sabtu & Minggu"),
    ]

    for schedule_value, label in schedule_options:
        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=f"{CB_PREFIX_EDIT_SCHEDULE}_{schedule_value}:{habit_id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="❌ Batal",
            callback_data=f"{CB_PREFIX_HABIT_DETAIL}:{habit_id}",
        )
    )

    return builder.as_markup()


# ===========================================================================
# SECTION 5 — SCHEDULE PICKER
# ===========================================================================

def kb_schedule_picker() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    schedule_options = [
        (HabitSchedule.EVERYDAY,    "📅 Setiap Hari"),
        (HabitSchedule.WEEKDAY,     "💼 Senin – Jumat"),
        (HabitSchedule.MON_WED_FRI, "🔄 Senin, Rabu, Jumat"),
        (HabitSchedule.TUE_THU_SAT, "🔄 Selasa, Kamis, Sabtu"),
        (HabitSchedule.WEEKEND,     "🎉 Sabtu & Minggu"),
    ]

    for schedule_value, label in schedule_options:
        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=f"{CB_PREFIX_SCHEDULE}:{schedule_value}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="❌ Batal",
            callback_data=CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


# ===========================================================================
# SECTION 6 — STATS, PROFILE & NAVIGATION
# ===========================================================================

def kb_stats_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📝 Summary Hari Ini",
            callback_data=CB_MENU_SUMMARY,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="✅ Check-in Sekarang",
            callback_data=CB_MENU_CHECKIN,
        ),
        InlineKeyboardButton(
            text="🏠 Menu Utama",
            callback_data=CB_BACK_MAIN,
        ),
    )

    return builder.as_markup()


def kb_profile_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="⏰ Ubah Jam Reminder",
            callback_data=CB_REMINDER_SET,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📋 Habit Saya",
            callback_data=CB_MENU_HABITS,
        ),
        InlineKeyboardButton(
            text="🏠 Menu Utama",
            callback_data=CB_BACK_MAIN,
        ),
    )

    return builder.as_markup()


def kb_back_to_main() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🏠 Menu Utama",
            callback_data=CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


def kb_after_checkin(all_done: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if all_done:
        builder.row(
            InlineKeyboardButton(
                text="📊 Lihat Statistik",
                callback_data=CB_MENU_STATS,
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Lanjut Check-in",
                callback_data=CB_MENU_CHECKIN,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🏠 Menu Utama",
            callback_data=CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


def kb_history_back(habit_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔙 Kembali ke Detail",
            callback_data=f"{CB_PREFIX_HABIT_DETAIL}:{habit_id}",
        ),
        InlineKeyboardButton(
            text="🏠 Menu Utama",
            callback_data=CB_BACK_MAIN,
        ),
    )

    return builder.as_markup()