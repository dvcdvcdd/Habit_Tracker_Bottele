import logging

from aiogram import Router
from aiogram.types import CallbackQuery

from app.keyboards.inline import (
    CB_MENU_CHECKIN,
    CB_PREFIX_CHECKIN,
    kb_after_checkin,
    kb_back_to_main,
    kb_checkin_done,
    kb_checkin_habits,
)
from app.services.habit_service import (
    do_checkin,
    get_today_habits_with_status,
    build_today_checkin_text,
)
from app.utils.helpers import format_streak

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(lambda c: c.data == CB_MENU_CHECKIN)
async def handle_show_checkin(callback: CallbackQuery) -> None:
    """
    Menampilkan daftar habit yang dijadwalkan hari ini
    beserta status check-in masing-masing.
    """
    user_id = callback.from_user.id

    habits_today = await get_today_habits_with_status(user_id)
    text         = build_today_checkin_text(habits_today)
    all_done     = all(h.is_done_today for h in habits_today) if habits_today else False

    if all_done and habits_today:
        await callback.message.edit_text(
            text         = text,
            parse_mode   = "Markdown",
            reply_markup = kb_checkin_done(),
        )
    elif not habits_today:
        await callback.message.edit_text(
            text         = text,
            parse_mode   = "Markdown",
            reply_markup = kb_back_to_main(),
        )
    else:
        await callback.message.edit_text(
            text         = text,
            parse_mode   = "Markdown",
            reply_markup = kb_checkin_habits(habits_today),
        )

    await callback.answer()


@router.callback_query(
    lambda c: c.data and c.data.startswith(f"{CB_PREFIX_CHECKIN}:")
)
async def handle_do_checkin(callback: CallbackQuery) -> None:
    """
    Memproses check-in untuk satu habit tertentu.
    """
    user_id = callback.from_user.id

    try:
        habit_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Terjadi kesalahan.", show_alert=True)
        return

    result = await do_checkin(user_id, habit_id)

    if result.already_done:
        await callback.answer(
            text       = result.motivation_msg,
            show_alert = False,
        )
        return

    if not result.success:
        await callback.answer(
            text       = result.motivation_msg,
            show_alert = True,
        )
        return

    # Check-in berhasil
    streak_text  = format_streak(result.new_streak)
    notif_parts  = [f"✅ {result.habit_name}  {streak_text}"]

    if result.gained_points > 0:
        notif_parts.append(f"🎯 +{result.gained_points} Poin")

    if result.level_up_msg:
        notif_parts.append(result.level_up_msg)

    if result.milestone_msg:
        notif_parts.append(f"🎉 {result.milestone_msg}")
    elif not result.level_up_msg:
        # Only show generic motivation if they didn't just level up
        notif_parts.append(result.motivation_msg)

    await callback.answer(
        text       = "\n".join(notif_parts),
        show_alert = len(notif_parts) > 1,
    )

    # Refresh tampilan
    habits_today = await get_today_habits_with_status(user_id)
    text         = build_today_checkin_text(habits_today)
    all_done     = all(h.is_done_today for h in habits_today) if habits_today else False

    try:
        if all_done and habits_today:
            await callback.message.edit_text(
                text         = text,
                parse_mode   = "Markdown",
                reply_markup = kb_checkin_done(),
            )
        else:
            await callback.message.edit_text(
                text         = text,
                parse_mode   = "Markdown",
                reply_markup = kb_checkin_habits(habits_today),
            )
    except Exception:
        pass