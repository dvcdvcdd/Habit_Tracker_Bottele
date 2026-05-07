import logging
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware untuk mencatat semua aktivitas user.

    Mencatat:
    - Setiap pesan yang masuk
    - Setiap callback yang ditekan
    - Berapa lama handler memproses request

    Berguna untuk:
    - Debugging
    - Memantau penggunaan bot
    - Mendeteksi pola error
    """

    async def __call__(
        self,
        handler:  Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event:    TelegramObject,
        data:     Dict[str, Any],
    ) -> Any:
        # Catat waktu mulai
        start_time = time.monotonic()

        # Log request masuk
        log_msg = self._build_log_message(event)
        if log_msg:
            logger.info(log_msg)

        # Jalankan handler
        result = await handler(event, data)

        # Hitung durasi
        duration_ms = (time.monotonic() - start_time) * 1000

        # Log durasi kalau lebih dari 1 detik (mungkin ada masalah)
        if duration_ms > 1000:
            logger.warning(
                f"Handler lambat: {duration_ms:.0f}ms untuk {log_msg}"
            )

        return result

    def _build_log_message(self, event: TelegramObject) -> str | None:
        """
        Bangun pesan log berdasarkan jenis event.
        """
        if isinstance(event, Message):
            user = event.from_user
            if not user:
                return None

            name = user.first_name
            uid  = user.id
            text = event.text or "[non-text]"

            # Potong teks panjang
            if len(text) > 50:
                text = text[:50] + "..."

            return f"MSG | user={uid} ({name}) | text={text!r}"

        if isinstance(event, CallbackQuery):
            user = event.from_user
            if not user:
                return None

            name = user.first_name
            uid  = user.id
            data = event.data or "[no data]"

            return f"CBQ | user={uid} ({name}) | data={data!r}"

        return None