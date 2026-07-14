from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from telegram_bot.config import Config, load_config
from telegram_bot.database.db import Database
from telegram_bot.handlers import admin, errors, start, user
from telegram_bot.middlewares.spam import SpamProtectionMiddleware
from telegram_bot.services.match_service import MatchService
from telegram_bot.utils.i18n import I18n
from telegram_bot.utils.logger import setup_logging


async def run() -> None:
    config: Config = load_config()
    setup_logging(config.log_level)

    i18n = I18n()
    db = Database(config.sqlite_path)
    await db.init()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    spam = SpamProtectionMiddleware(cooldown_seconds=0.6)
    dp.message.middleware(spam)
    dp.callback_query.middleware(spam)

    service = MatchService(db=db, i18n=i18n, admin_ids=config.admin_ids)

    dp.include_router(start.router)
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(errors.router)

    await dp.start_polling(bot, db=db, i18n=i18n, config=config, service=service)


if __name__ == "__main__":
    asyncio.run(run())
