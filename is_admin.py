from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject


class IsAdminFilter(BaseFilter):
    def __init__(self, admin_ids: list[int]) -> None:
        self.admin_ids = set(admin_ids)

    async def __call__(self, event: TelegramObject) -> bool:
        if isinstance(event, Message) and event.from_user:
            return event.from_user.id in self.admin_ids
        if isinstance(event, CallbackQuery) and event.from_user:
            return event.from_user.id in self.admin_ids
        return False
