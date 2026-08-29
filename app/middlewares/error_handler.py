import logging
import traceback
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import (
    CallbackQuery,
    ErrorEvent,
    Message,
    TelegramObject,
)

from app.keyboards.inline import kb_back_to_main

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Middleware yang menangkap semua exception yang tidak tertangkap
    di handler manapun.

    Yang dilakukan:
    1. Log error lengkap dengan traceback
    2. Kirim pesan ramah ke user
    3. Tidak membocorkan detail teknis ke user
    """

    async def __call__(
        self,
        handler:  Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event:    TelegramObject,
        data:     Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)

        except Exception as e:
            # Log error lengkap dengan traceback
            logger.error(
                f"Exception tidak tertangkap: {type(e).__name__}: {e}\n"
                f"Traceback:\n{traceback.format_exc()}"
            )

            # Kirim pesan ke user tergantung jenis event
            await self._notify_user(event, e)

    async def _notify_user(
        self,
        event: TelegramObject,
        error: Exception,
    ) -> None:
        """
        Kirim pesan error yang ramah ke user.
        """
        error_text = (
            "<b>Terjadi kesalahan yang tidak terduga.</b>\n\n"
            "Silakan coba lagi, atau ketuk tombol di bawah "
            "untuk kembali ke menu utama.\n\n"
            "<i>Jika masalah berlanjut, kirim /start untuk memulai ulang.</i>"
        )

        try:
            if isinstance(event, Message):
                await event.answer(
                    text         = error_text,
                    parse_mode   = "HTML",
                    reply_markup = kb_back_to_main(),
                )

            elif isinstance(event, CallbackQuery):
                # Coba edit pesan yang ada dulu
                try:
                    await event.message.edit_text(
                        text         = error_text,
                        parse_mode   = "HTML",
                        reply_markup = kb_back_to_main(),
                    )
                except Exception:
                    # Kalau edit gagal, kirim pesan baru
                    await event.message.answer(
                        text         = error_text,
                        parse_mode   = "HTML",
                        reply_markup = kb_back_to_main(),
                    )

                # Selalu jawab callback query
                try:
                    await event.answer()
                except Exception:
                    pass

        except Exception as notify_error:
            # Kalau bahkan notifikasi error pun gagal, log saja
            logger.error(
                f"Gagal mengirim notifikasi error ke user: {notify_error}"
            )