# app/utils/helpers.py

import html
from typing import List

# ===========================================================================
# SIMBOL STATUS (karakter teks monokrom, bukan emoji)
# Dipakai konsisten di seluruh pesan bot agar tampil modern dan profesional.
# ===========================================================================

DONE_MARK = "[x]"   # habit sudah di-check-in
TODO_MARK = "[ ]"   # habit belum di-check-in
OFF_MARK  = "[·]"   # habit tidak dijadwalkan hari ini / sedang dijeda

CAL_DONE   = "■"    # kalender riwayat: hari check-in
CAL_MISSED = "□"    # kalender riwayat: hari terlewat
CAL_OFF    = "·"    # kalender riwayat: bukan jadwal

BAR_FILLED = "█"    # progress bar terisi
BAR_EMPTY  = "░"    # progress bar kosong


def esc(text) -> str:
    """
    Escape teks agar aman dikirim dengan parse mode HTML.
    Selalu gunakan untuk semua input dari user (nama habit, nama user, dll).
    """
    return html.escape(str(text), quote=True)


def chunk_list(lst: list, size: int) -> List[list]:
    """
    Memecah list panjang menjadi beberapa list kecil.
    Dipakai untuk layout tombol inline keyboard.
    """
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def truncate(text: str, max_length: int = 30, suffix: str = "...") -> str:
    """
    Potong teks jika terlalu panjang.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def progress_bar(done: int, total: int, length: int = 10) -> str:
    """
    Progress bar monokrom berbasis blok teks.
    Contoh: "████████░░"
    """
    if total <= 0:
        return BAR_EMPTY * length

    filled = round((done / total) * length)
    filled = max(0, min(filled, length))
    return BAR_FILLED * filled + BAR_EMPTY * (length - filled)


def format_streak(streak: int) -> str:
    """
    Ubah angka streak menjadi teks yang bersih dan informatif.
    """
    if streak <= 0:
        return "belum ada streak"
    return f"{streak} hari"


def safe_int(value, default: int = 0) -> int:
    """
    Konversi ke int dengan aman.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Validasi dan sanitasi input
# ---------------------------------------------------------------------------

def sanitize_text(text: str) -> str:
    """
    Bersihkan input text dari karakter berbahaya.
    """
    if not text:
        return ""
    text = text.strip()
    text = " ".join(text.split())
    return text


def is_valid_habit_name(name: str) -> tuple[bool, str]:
    """
    Validasi nama habit.
    Return (is_valid, error_message).
    """
    name = sanitize_text(name)

    if not name:
        return False, "Nama habit tidak boleh kosong."

    if len(name) < 2:
        return False, "Nama habit terlalu pendek. Minimal 2 karakter."

    if len(name) > 50:
        return False, "Nama habit terlalu panjang. Maksimal 50 karakter."

    if name.isdigit():
        return False, "Nama habit tidak boleh hanya berupa angka."

    forbidden_chars = ["<", ">", "&", '"', "'", "\\", "/"]
    for char in forbidden_chars:
        if char in name:
            return False, f"Nama habit tidak boleh mengandung karakter '{char}'."

    return True, ""


def is_valid_reminder_time(time_str: str) -> tuple[bool, str]:
    """
    Validasi format jam reminder HH:MM.
    Return (is_valid, error_message).
    """
    if not time_str or ":" not in time_str:
        return False, "Format jam tidak valid. Gunakan format HH:MM."

    parts = time_str.strip().split(":")

    if len(parts) != 2:
        return False, "Format jam tidak valid. Gunakan format HH:MM."

    try:
        hour   = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return False, "Jam harus berupa angka."

    if not (0 <= hour <= 23):
        return False, "Jam harus antara 00 sampai 23."

    if not (0 <= minute <= 59):
        return False, "Menit harus antara 00 sampai 59."

    return True, ""
