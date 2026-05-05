# app/utils/helpers.py

from typing import List


def chunk_list(lst: list, size: int) -> List[list]:
    """
    Memecah list panjang menjadi beberapa list kecil dengan ukuran tertentu.

    Ini dipakai untuk membuat tombol inline keyboard yang rapi.
    Telegram membatasi layout tombol, jadi kita perlu mengatur
    berapa tombol per baris.

    Contoh:
    chunk_list([1, 2, 3, 4, 5], 2)
    # hasilnya: [[1, 2], [3, 4], [5]]
    """
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def truncate(text: str, max_length: int = 30, suffix: str = "...") -> str:
    """
    Memotong teks jika terlalu panjang.

    Dipakai agar nama habit yang panjang tidak merusak tampilan tombol.

    Contoh:
    truncate("Olahraga pagi sebelum sarapan", 20)
    # hasilnya: "Olahraga pagi sebelu..."
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def emoji_progress_bar(done: int, total: int, length: int = 10) -> str:
    """
    Membuat progress bar sederhana menggunakan emoji.

    Parameter:
    - done: jumlah yang sudah selesai
    - total: total keseluruhan
    - length: panjang bar dalam karakter

    Contoh:
    emoji_progress_bar(3, 5, 10)
    # hasilnya: "██████░░░░ 3/5"
    """
    if total == 0:
        return f"{'░' * length} 0/0"

    filled = round((done / total) * length)
    filled = max(0, min(filled, length))  # clamp antara 0 dan length
    bar = "█" * filled + "░" * (length - filled)
    return f"{bar} {done}/{total}"


def format_streak(streak: int) -> str:
    """
    Mengubah angka streak menjadi teks yang enak dibaca, dengan emoji.

    Contoh:
    format_streak(0)  → "Belum ada streak"
    format_streak(1)  → "🔥 1 hari"
    format_streak(7)  → "🔥 7 hari"
    format_streak(30) → "🏆 30 hari"
    """
    if streak == 0:
        return "Belum ada streak"
    if streak >= 30:
        return f"🏆 {streak} hari"
    if streak >= 7:
        return f"⭐ {streak} hari"
    return f"🔥 {streak} hari"


def safe_int(value, default: int = 0) -> int:
    """
    Mengkonversi value ke int dengan aman.
    Kalau gagal, kembalikan nilai default.

    Dipakai untuk menghindari crash saat data dari database tidak terduga.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default