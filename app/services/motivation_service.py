import random
from app.utils.enums import StreakStatus


_MESSAGES_CHECKIN = [
    "Bagus. Satu langkah kecil tetap berarti.",
    "Done. Konsistensi dibangun dari momen seperti ini.",
    "Tercatat. Lanjutkan ritme ini.",
    "Sip. Kamu sudah melakukannya hari ini.",
    "Baik. Satu hari lagi terlewati dengan baik.",
    "Noted. Kecil tapi nyata.",
    "Good. Jangan berhenti di sini.",
]

_MESSAGES_STREAK_ACTIVE = [
    "Streak kamu masih hidup. Pertahankan.",
    "Ritme kamu sedang bagus. Jaga terus.",
    "Konsistensi adalah kemenangan yang sunyi.",
    "Setiap hari yang kamu selesaikan adalah bukti.",
    "Kamu lebih konsisten dari yang kamu kira.",
]

_MESSAGES_STREAK_MILESTONE = {
    7:   "7 hari. Satu minggu penuh. Ini sudah lebih dari rata-rata orang.",
    14:  "2 minggu. Habit ini mulai jadi bagian dari dirimu.",
    21:  "21 hari. Penelitian bilang ini titik awal kebiasaan terbentuk.",
    30:  "30 hari. Satu bulan penuh. Ini serius.",
    60:  "60 hari. Kamu bukan lagi pemula di habit ini.",
    90:  "90 hari. Tiga bulan. Luar biasa.",
    100: "100 hari. Tidak banyak orang sampai di sini.",
}

_MESSAGES_STREAK_BROKEN = [
    "Streak kamu putus. Tidak apa-apa, itu bagian dari prosesnya.",
    "Terlewat satu hari. Mulai lagi dari satu, bukan dari nol.",
    "Gagal sekali bukan berarti gagal selamanya. Kembali hari ini.",
    "Tidak ada streak yang sempurna. Yang penting kembali.",
    "Hari kemarin sudah berlalu. Hari ini masih bisa dimulai.",
]

_MESSAGES_COMEBACK = [
    "Kamu kembali. Itu yang paling penting.",
    "Tidak perlu sempurna. Cukup mulai lagi hari ini.",
    "Setiap hari adalah kesempatan baru untuk memulai.",
    "Yang membedakan orang konsisten bukan tidak pernah berhenti, tapi selalu kembali.",
    "Bolong beberapa hari bukan akhir. Check-in hari ini adalah bukti kamu masih mau.",
    "Gapapa. Yuk lanjut dari sini.",
]

_MESSAGES_REMINDER = [
    "Waktunya check-in habit hari ini.",
    "Jangan lupa habit kamu hari ini.",
    "Sebentar saja. Check-in dulu sebelum hari ini berakhir.",
    "Habit kamu menunggu. Yuk selesaikan.",
    "Hari ini belum selesai. Masih ada waktu untuk check-in.",
]

_MESSAGES_SUMMARY_PERFECT = [
    "Semua habit hari ini selesai. Kerja bagus.",
    "Hari yang produktif. Semua terceklis.",
    "100%. Hari ini kamu berhasil.",
    "Tidak ada yang terlewat hari ini. Pertahankan besok.",
]

_MESSAGES_SUMMARY_PARTIAL = [
    "Hampir. Masih ada yang bisa diselesaikan sebelum hari ini berakhir.",
    "Progress hari ini lumayan. Coba sempurnakan sebelum tidur.",
    "Belum semua selesai, tapi kamu sudah memulai. Itu yang penting.",
]

_MESSAGES_SUMMARY_EMPTY = [
    "Belum ada check-in hari ini. Masih ada waktu.",
    "Hari ini belum ada yang tercentang. Mulai dari satu dulu.",
    "Tidak ada yang terlambat selama hari ini belum berakhir.",
]


def get_checkin_message() -> str:
    return random.choice(_MESSAGES_CHECKIN)


def get_streak_message(streak_status: str, streak_count: int = 0) -> str:
    if streak_status == StreakStatus.BROKEN:
        return random.choice(_MESSAGES_STREAK_BROKEN)
    if streak_status == StreakStatus.COMEBACK:
        return random.choice(_MESSAGES_COMEBACK)
    if streak_status == StreakStatus.NEW:
        return "Habit baru dimulai. Semoga konsisten."
    if streak_status == StreakStatus.ACTIVE:
        milestone_msg = _MESSAGES_STREAK_MILESTONE.get(streak_count)
        if milestone_msg:
            return milestone_msg
        return random.choice(_MESSAGES_STREAK_ACTIVE)
    return random.choice(_MESSAGES_STREAK_ACTIVE)


def get_comeback_message(days_absent: int) -> str:
    if days_absent >= 7:
        return (
            f"Sudah {days_absent} hari sejak check-in terakhir. "
            "Tidak apa-apa. Yang penting kamu kembali hari ini."
        )
    return random.choice(_MESSAGES_COMEBACK)


def get_reminder_message(first_name: str) -> str:
    base = random.choice(_MESSAGES_REMINDER)
    return f"{first_name}, {base[0].lower()}{base[1:]}"


def get_summary_message(done: int, total: int) -> str:
    if total == 0:
        return "Tidak ada habit yang dijadwalkan hari ini."
    if done == total:
        return random.choice(_MESSAGES_SUMMARY_PERFECT)
    if done == 0:
        return random.choice(_MESSAGES_SUMMARY_EMPTY)
    return random.choice(_MESSAGES_SUMMARY_PARTIAL)


def get_milestone_message(streak: int) -> str | None:
    return _MESSAGES_STREAK_MILESTONE.get(streak)