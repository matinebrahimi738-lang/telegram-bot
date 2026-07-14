from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class SpamProtectionMiddleware(BaseMiddleware):
    def __init__(self, cooldown_seconds: float = 0.7) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._last_seen: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        last = self._last_seen.get(user_id, 0)
        if now - last < self.cooldown_seconds:
            return None

        self._last_seen[user_id] = now
        return await handler(event, data)
