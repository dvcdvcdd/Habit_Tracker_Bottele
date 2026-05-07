import logging
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class RateLimiterMiddleware(BaseMiddleware):
    """
    Middleware untuk membatasi frekuensi request dari satu user.

    Mencegah user menekan tombol terlalu cepat berkali-kali
    yang bisa menyebabkan race condition di database.

    Konfigurasi default:
    - Max 1 request per 0.5 detik per user
    - Kalau terlalu cepat, request diabaikan dengan notifikasi singkat
    """

    def __init__(
        self,
        rate_limit:  float = 0.5,  # detik antar request
        notify_user: bool  = True,  # apakah user diberi tahu saat kena limit
    ):
        self.rate_limit  = rate_limit
        self.notify_user = notify_user

        # Menyimpan timestamp request terakhir per user
        # Format: {user_id: timestamp}
        self._last_request: Dict[int, float] = {}

        super().__init__()

    async def __call__(
        self,
        handler:  Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event:    TelegramObject,
        data:     Dict[str, Any],
    ) -> Any:
        # Ambil user_id dari event
        user_id = self._get_user_id(event)

        if user_id is None:
            # Tidak bisa identifikasi user, lewati saja
            return await handler(event, data)

        now  = time.monotonic()
        last = self._last_request.get(user_id, 0)

        # Cek apakah terlalu cepat
        if now - last < self.rate_limit:
            logger.debug(
                f"Rate limit hit: user={user_id}, "
                f"jarak={(now - last):.3f}s dari limit {self.rate_limit}s"
            )

            if self.notify_user:
                await self._notify_rate_limited(event)

            return  # Abaikan request ini

        # Update timestamp dan lanjutkan
        self._last_request[user_id] = now
        return await handler(event, data)

    def _get_user_id(self, event: TelegramObject) -> int | None:
        """
        Ekstrak user_id dari berbagai jenis event.
        """
        if isinstance(event, Message):
            return event.from_user.id if event.from_user else None
        if isinstance(event, CallbackQuery):
            return event.from_user.id if event.from_user else None
        return None

    async def _notify_rate_limited(self, event: TelegramObject) -> None:
        """
        Beri tahu user bahwa request terlalu cepat.
        Pesan singkat dan tidak mengganggu.
        """
        try:
            if isinstance(event, CallbackQuery):
                await event.answer(
                    text       = "Pelan-pelan ya. 😅",
                    show_alert = False,
                )
        except Exception:
            pass

    def cleanup_old_entries(self, max_age: float = 60.0) -> None:
        """
        Bersihkan entry lama dari _last_request untuk hemat memori.
        Dipanggil secara periodik dari scheduler.
        """
        now     = time.monotonic()
        to_delete = [
            uid for uid, ts in self._last_request.items()
            if now - ts > max_age
        ]
        for uid in to_delete:
            del self._last_request[uid]

        if to_delete:
            logger.debug(f"Rate limiter cleanup: {len(to_delete)} entry dihapus")