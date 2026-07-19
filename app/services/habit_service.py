import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.database.models import Habit
from app.database.queries import (
    create_habit,
    get_habit_by_id,
    get_habits,
    get_habits_scheduled_today,
    get_checkin_today,
    soft_delete_habit,
    update_last_active,
)
from app.utils.dates import is_habit_scheduled_today, today_str
from app.utils.enums import (
    CheckinStatus,
    HabitSchedule,
    SCHEDULE_DISPLAY,
    StreakStatus,
)
from app.utils.helpers import format_streak

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclass hasil operasi
# ---------------------------------------------------------------------------

@dataclass
class HabitWithStatus:
    """
    Habit yang sudah dilengkapi dengan status check-in hari ini.
    """
    habit:          Habit
    is_done_today:  bool
    is_scheduled:   bool
    streak_display: str


@dataclass
class CheckInResult:
    """
    Hasil dari operasi check-in.
    """
    success:          bool
    already_done:     bool
    habit_name:       str
    new_streak:       int
    longest_streak:   int
    streak_status:    str
    motivation_msg:   str
    milestone_msg:    Optional[str]
    gained_points:    int = 0
    level_up_msg:     Optional[str] = None


# ---------------------------------------------------------------------------
# Fungsi service
# ---------------------------------------------------------------------------

async def add_habit(
    user_id:     int,
    name:        str,
    schedule:    str = HabitSchedule.EVERYDAY,
    custom_days: str = "",
) -> Tuple[bool, str, Optional[int]]:
    """
    Menambahkan habit baru untuk user.
    Mengembalikan (success, message, habit_id).
    """
    name = name.strip()

    if not name:
        return False, "Nama habit tidak boleh kosong.", None

    if len(name) > 50:
        return False, "Nama habit terlalu panjang. Maksimal 50 karakter.", None

    existing = await get_habits(user_id, active_only=True)

    if len(existing) >= 10:
        return (
            False,
            "Kamu sudah punya 10 habit aktif. Hapus yang tidak dipakai dulu.",
            None,
        )

    names_lower = [h.name.lower() for h in existing]
    if name.lower() in names_lower:
        return False, f'Habit "{name}" sudah ada di daftar kamu.', None

    try:
        habit_id = await create_habit(
            user_id     = user_id,
            name        = name,
            schedule    = schedule,
            custom_days = custom_days,
        )
        await update_last_active(user_id)
        logger.info(f"Habit baru dibuat: user={user_id}, name={name}, id={habit_id}")
        return True, f'Habit "{name}" berhasil ditambahkan.', habit_id

    except Exception as e:
        logger.error(f"Error saat tambah habit: {e}")
        return False, "Terjadi kesalahan. Coba lagi.", None


async def remove_habit(user_id: int, habit_id: int) -> Tuple[bool, str]:
    """
    Menghapus (soft delete) habit milik user.
    Mengembalikan (success, message).
    """
    habit = await get_habit_by_id(habit_id, user_id)

    if habit is None:
        return False, "Habit tidak ditemukan."

    success = await soft_delete_habit(habit_id, user_id)

    if success:
        await update_last_active(user_id)
        logger.info(f"Habit dihapus: user={user_id}, habit_id={habit_id}")
        return True, f'Habit "{habit.name}" berhasil dihapus.'

    return False, "Gagal menghapus habit. Coba lagi."


async def get_habits_with_status(user_id: int) -> List[HabitWithStatus]:
    """
    Mengambil semua habit aktif user beserta status hari ini.
    """
    habits = await get_habits(user_id, active_only=True)
    result = []

    for habit in habits:
        is_scheduled = is_habit_scheduled_today(habit.schedule, habit.custom_days)
        is_done      = False

        if is_scheduled:
            checkin = await get_checkin_today(habit.habit_id)
            is_done = checkin is not None and checkin.status == CheckinStatus.DONE

        result.append(
            HabitWithStatus(
                habit          = habit,
                is_done_today  = is_done,
                is_scheduled   = is_scheduled,
                streak_display = format_streak(habit.current_streak),
            )
        )

    return result


async def get_today_habits_with_status(user_id: int) -> List[HabitWithStatus]:
    """
    Mengambil habit yang dijadwalkan hari ini beserta status check-in.
    """
    habits_today = await get_habits_scheduled_today(user_id)
    result       = []

    for habit in habits_today:
        checkin = await get_checkin_today(habit.habit_id)
        is_done = checkin is not None and checkin.status == CheckinStatus.DONE

        result.append(
            HabitWithStatus(
                habit          = habit,
                is_done_today  = is_done,
                is_scheduled   = True,
                streak_display = format_streak(habit.current_streak),
            )
        )

    return result


async def do_checkin(user_id: int, habit_id: int) -> CheckInResult:
    """
    Melakukan check-in untuk satu habit.
    """
    from app.database.queries import create_checkin, add_user_points
    from app.services.streak_service import process_checkin_streak
    from app.services.motivation_service import get_checkin_message, get_milestone_message

    habit = await get_habit_by_id(habit_id, user_id)

    if habit is None:
        return CheckInResult(
            success        = False,
            already_done   = False,
            habit_name     = "Unknown",
            new_streak     = 0,
            longest_streak = 0,
            streak_status  = StreakStatus.NEW,
            motivation_msg = "Habit tidak ditemukan.",
            milestone_msg  = None,
        )

    existing = await get_checkin_today(habit_id)
    if existing:
        return CheckInResult(
            success        = False,
            already_done   = True,
            habit_name     = habit.name,
            new_streak     = habit.current_streak,
            longest_streak = habit.longest_streak,
            streak_status  = StreakStatus.ACTIVE,
            motivation_msg = "Kamu sudah check-in habit ini hari ini. 👍",
            milestone_msg  = None,
        )

    checkin_success = await create_checkin(habit_id, user_id)

    if not checkin_success:
        return CheckInResult(
            success        = False,
            already_done   = True,
            habit_name     = habit.name,
            new_streak     = habit.current_streak,
            longest_streak = habit.longest_streak,
            streak_status  = StreakStatus.ACTIVE,
            motivation_msg = "Kamu sudah check-in habit ini hari ini. 👍",
            milestone_msg  = None,
        )

    new_streak, new_longest, streak_status = await process_checkin_streak(habit)
    motivation = get_checkin_message()
    milestone  = get_milestone_message(new_streak)

    # Gamification points logic
    points_to_add = 10
    if new_streak > 0 and new_streak % 7 == 0:
        points_to_add += 40

    new_points, new_level, level_up_occurred = await add_user_points(user_id, points_to_add)
    level_up_msg = f"🎉 Naik Level! Kamu sekarang Level {new_level}!" if level_up_occurred else None

    await update_last_active(user_id)

    logger.info(
        f"Check-in berhasil: user={user_id}, habit={habit.name}, "
        f"streak={new_streak}, status={streak_status}, gained_points={points_to_add}, new_level={new_level}"
    )

    return CheckInResult(
        success        = True,
        already_done   = False,
        habit_name     = habit.name,
        new_streak     = new_streak,
        longest_streak = new_longest,
        streak_status  = streak_status,
        motivation_msg = motivation,
        milestone_msg  = milestone,
        gained_points  = points_to_add,
        level_up_msg   = level_up_msg,
    )


def format_schedule_display(schedule: str) -> str:
    """
    Mengubah nilai enum jadwal menjadi teks yang enak dibaca.
    """
    return SCHEDULE_DISPLAY.get(schedule, schedule)


def build_habit_list_text(habits_with_status: List[HabitWithStatus]) -> str:
    """
    Membuat teks daftar habit yang siap dikirim ke Telegram.
    """
    if not habits_with_status:
        return (
            "Kamu belum punya habit.\n\n"
            "Gunakan tombol di bawah untuk menambahkan habit pertamamu."
        )

    lines = ["📋 *Semua habit kamu*\n"]

    for item in habits_with_status:
        if item.is_scheduled:
            status_icon = "✅" if item.is_done_today else "⬜"
        else:
            status_icon = "💤"

        schedule_text = format_schedule_display(item.habit.schedule)
        streak_text   = item.streak_display

        lines.append(
            f"{status_icon} *{item.habit.name}*\n"
            f"   📅 {schedule_text}  {streak_text}"
        )

    lines.append(
        "\n✅ selesai  ⬜ belum  💤 tidak dijadwalkan hari ini"
    )

    return "\n\n".join(lines[:-1]) + "\n" + lines[-1]


def build_today_checkin_text(habits_with_status: List[HabitWithStatus]) -> str:
    """
    Membuat teks untuk tampilan check-in hari ini.
    """
    from app.utils.dates import weekday_name_today, format_date_display, today_str
    from app.utils.helpers import emoji_progress_bar

    day_name = weekday_name_today()
    date_str = format_date_display(today_str())

    if not habits_with_status:
        return (
            f"📅 *{day_name}, {date_str}*\n\n"
            "Tidak ada habit yang dijadwalkan hari ini.\n"
            "Istirahat dengan tenang 😌"
        )

    total = len(habits_with_status)
    done  = sum(1 for h in habits_with_status if h.is_done_today)

    progress = emoji_progress_bar(done, total)

    lines = [
        f"📅 *{day_name}, {date_str}*",
        f"`{progress}`",
        "",
    ]

    for item in habits_with_status:
        icon = "✅" if item.is_done_today else "⬜"
        lines.append(f"{icon} {item.habit.name}  {item.streak_display}")

    if done == total:
        lines.append("\n🎉 Semua selesai hari ini!")
    else:
        remaining = total - done
        lines.append(f"\n{remaining} habit lagi menunggu check-in.")

    return "\n".join(lines)