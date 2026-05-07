from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def kb_cancel() -> ReplyKeyboardMarkup:
    """
    Keyboard dengan satu tombol Cancel.

    Ditampilkan saat user sedang dalam proses input,
    misalnya saat mengetik nama habit baru.
    User bisa tekan Cancel untuk keluar dari proses tersebut.
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❌ Batal")
    )

    return builder.as_markup(
        resize_keyboard  = True,   # tombol menyesuaikan ukuran
        one_time_keyboard = True,  # keyboard hilang setelah dipakai
    )


def kb_remove() -> ReplyKeyboardRemove:
    """
    Menghapus reply keyboard yang sedang aktif.

    Setelah proses input selesai, kita hapus reply keyboard
    supaya tampilan kembali normal.
    """
    return ReplyKeyboardRemove()