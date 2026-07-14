from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

from telegram_bot.database.db import Database
from telegram_bot.utils.i18n import I18n


router = Router()
logger = logging.getLogger(__name__)


@router.errors()
async def global_error_handler(event: ErrorEvent, db: Database, i18n: I18n) -> bool:
    logger.exception("Unhandled error", exc_info=event.exception)

    update = event.update
    from_user = None
    if update.message and update.message.from_user:
        from_user = update.message.from_user
    elif update.callback_query and update.callback_query.from_user:
        from_user = update.callback_query.from_user

    if not from_user:
        return True

    user = await db.get_user_by_tg(from_user.id)
    lang = user["lang"] if user and user["lang"] in {"fa", "en"} else "en"
    text = i18n.t(lang, "errors.generic")

    try:
        if update.message:
            await update.message.answer(text)
        elif update.callback_query:
            await update.callback_query.message.answer(text)
    except Exception:
        logger.exception("Failed to send error message")

    return True
