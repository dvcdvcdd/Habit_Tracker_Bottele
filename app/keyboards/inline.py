from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models import Habit
from app.services.habit_service import HabitWithStatus
from app.utils.enums import HabitSchedule, SCHEDULE_DISPLAY
from app.utils.helpers import chunk_list, truncate

# Menu utama
CB_MENU_MAIN        = "menu:main"
CB_MENU_CHECKIN     = "menu:checkin"
CB_MENU_HABITS      = "menu:habits"
CB_MENU_STATS       = "menu:stats"
CB_MENU_SUMMARY     = "menu:summary"

# Habit actions
CB_HABIT_ADD        = "habit:add"
CB_HABIT_LIST       = "habit:list"
CB_HABIT_DELETE     = "habit:delete"

# Prefix untuk callback yang butuh ID
# Format: "checkin:{habit_id}" atau "delete_confirm:{habit_id}"
CB_PREFIX_CHECKIN       = "checkin"
CB_PREFIX_DELETE        = "delete"
CB_PREFIX_DELETE_CONFIRM = "delete_confirm"
CB_PREFIX_DELETE_CANCEL  = "delete_cancel"

# Schedule picker
CB_PREFIX_SCHEDULE  = "schedule"

# Navigasi
CB_BACK_MAIN        = "nav:main"
CB_CLOSE            = "nav:close"

# Reminder setting
CB_REMINDER_SET     = "reminder:set"

def kb_main_menu() -> InlineKeyboardMarkup:
    """
    Keyboard untuk menu utama bot.

    Layout:
    [✅ Check-in Hari Ini]
    [📋 Habit Saya    ] [➕ Tambah Habit]
    [📊 Statistik     ] [📝 Summary Hari Ini]
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text          = "✅ Check-in Hari Ini",
            callback_data = CB_MENU_CHECKIN,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text          = "📋 Habit Saya",
            callback_data = CB_MENU_HABITS,
        ),
        InlineKeyboardButton(
            text          = "➕ Tambah Habit",
            callback_data = CB_HABIT_ADD,
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text          = "📊 Statistik",
            callback_data = CB_MENU_STATS,
        ),
        InlineKeyboardButton(
            text          = "📝 Summary",
            callback_data = CB_MENU_SUMMARY,
        ),
    )

    return builder.as_markup()

def kb_checkin_habits(habits: list[HabitWithStatus]) -> InlineKeyboardMarkup:
    """
    Keyboard untuk tampilan check-in harian.

    Setiap habit tampil sebagai tombol.
    Habit yang sudah done ditandai dengan ✅ di nama tombol.
    Habit yang belum done ditandai dengan ⬜.

    Di bawah ada tombol kembali ke menu.

    Layout contoh (3 habit):
    [✅ Olahraga          ]
    [⬜ Baca Buku         ]
    [✅ Minum Air         ]
    [🏠 Menu Utama        ]
    """
    builder = InlineKeyboardBuilder()

    for item in habits:
        icon = "✅" if item.is_done_today else "⬜"
        name = truncate(item.habit.name, 28)

        # Kalau sudah done, callback tetap dikirim tapi service akan
        # menolak dengan pesan "sudah check-in"
        builder.row(
            InlineKeyboardButton(
                text          = f"{icon} {name}",
                callback_data = f"{CB_PREFIX_CHECKIN}:{item.habit.habit_id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text          = "🏠 Menu Utama",
            callback_data = CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


def kb_checkin_done() -> InlineKeyboardMarkup:
    """
    Keyboard setelah semua habit selesai di-checkin hari ini.
    Hanya ada tombol kembali ke menu.
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text          = "📊 Lihat Statistik",
            callback_data = CB_MENU_STATS,
        ),
        InlineKeyboardButton(
            text          = "🏠 Menu Utama",
            callback_data = CB_BACK_MAIN,
        ),
    )

    return builder.as_markup()

def kb_habit_list_menu() -> InlineKeyboardMarkup:
    """
    Keyboard untuk halaman daftar habit.
    Menu aksi yang bisa dilakukan user pada habit.

    Layout:
    [➕ Tambah Habit]
    [🗑 Hapus Habit ]
    [🏠 Menu Utama  ]
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text          = "➕ Tambah Habit",
            callback_data = CB_HABIT_ADD,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text          = "🗑 Hapus Habit",
            callback_data = CB_HABIT_DELETE,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text          = "🏠 Menu Utama",
            callback_data = CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


def kb_delete_habit_picker(habits: list[Habit]) -> InlineKeyboardMarkup:
    """
    Keyboard untuk memilih habit mana yang akan dihapus.

    Setiap habit tampil sebagai tombol.
    User harus memilih dulu, lalu nanti ada konfirmasi.

    Layout:
    [Olahraga    ] [Baca Buku   ]
    [Minum Air   ]
    [❌ Batal     ]
    """
    builder = InlineKeyboardBuilder()

    # Tombol per habit, 2 kolom
    buttons = [
        InlineKeyboardButton(
            text          = truncate(h.name, 20),
            callback_data = f"{CB_PREFIX_DELETE}:{h.habit_id}",
        )
        for h in habits
    ]

    # Susun 2 tombol per baris
    for row_buttons in chunk_list(buttons, 2):
        builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(
            text          = "❌ Batal",
            callback_data = CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


def kb_delete_confirm(habit_id: int, habit_name: str) -> InlineKeyboardMarkup:
    """
    Keyboard konfirmasi sebelum menghapus habit.

    Kita selalu minta konfirmasi sebelum menghapus data penting.
    Ini mencegah hapus tidak sengaja.

    Layout:
    [✅ Ya, Hapus ] [❌ Batal]
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text          = "✅ Ya, Hapus",
            callback_data = f"{CB_PREFIX_DELETE_CONFIRM}:{habit_id}",
        ),
        InlineKeyboardButton(
            text          = "❌ Batal",
            callback_data = CB_BACK_MAIN,
        ),
    )

    return builder.as_markup()

def kb_schedule_picker() -> InlineKeyboardMarkup:
    """
    Keyboard untuk memilih jadwal habit baru.

    Menampilkan semua pilihan jadwal yang tersedia.
    Setiap pilihan memiliki deskripsi singkat.

    Layout:
    [📅 Setiap Hari        ]
    [💼 Senin – Jumat      ]
    [🔄 Senin, Rabu, Jumat ]
    [🔄 Selasa, Kamis, Sabtu]
    [🎉 Sabtu & Minggu     ]
    [❌ Batal              ]
    """
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
                text          = label,
                callback_data = f"{CB_PREFIX_SCHEDULE}:{schedule_value}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text          = "❌ Batal",
            callback_data = CB_BACK_MAIN,
        )
    )

    return builder.as_markup()

def kb_stats_menu() -> InlineKeyboardMarkup:
    """
    Keyboard di bawah halaman statistik.

    Layout:
    [📝 Summary Hari Ini]
    [✅ Check-in        ]
    [🏠 Menu Utama      ]
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text          = "📝 Summary Hari Ini",
            callback_data = CB_MENU_SUMMARY,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text          = "✅ Check-in Sekarang",
            callback_data = CB_MENU_CHECKIN,
        ),
        InlineKeyboardButton(
            text          = "🏠 Menu Utama",
            callback_data = CB_BACK_MAIN,
        ),
    )

    return builder.as_markup()


def kb_back_to_main() -> InlineKeyboardMarkup:
    """
    Keyboard sederhana hanya berisi tombol kembali ke menu utama.
    Dipakai di berbagai situasi sebagai fallback.
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text          = "🏠 Menu Utama",
            callback_data = CB_BACK_MAIN,
        )
    )

    return builder.as_markup()


def kb_after_checkin(all_done: bool) -> InlineKeyboardMarkup:
    """
    Keyboard yang muncul setelah user melakukan check-in.

    Kalau semua habit sudah selesai, tampilkan opsi statistik.
    Kalau belum semua, tampilkan opsi kembali ke check-in.

    Parameter:
    - all_done: True jika semua habit hari ini sudah selesai
    """
    builder = InlineKeyboardBuilder()

    if all_done:
        builder.row(
            InlineKeyboardButton(
                text          = "📊 Lihat Statistik",
                callback_data = CB_MENU_STATS,
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text          = "✅ Lanjut Check-in",
                callback_data = CB_MENU_CHECKIN,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text          = "🏠 Menu Utama",
            callback_data = CB_BACK_MAIN,
        )
    )

    return builder.as_markup()