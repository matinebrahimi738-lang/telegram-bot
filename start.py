from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from telegram_bot.database.db import Database
from telegram_bot.keyboards.inline import language_keyboard, user_menu_keyboard
from telegram_bot.utils.i18n import I18n


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, db: Database, i18n: I18n) -> None:
    user = await db.ensure_user(message.from_user.id, message.from_user.username)

    if user["lang"] not in {"fa", "en"}:
        await message.answer(
            i18n.t("en", "language.choose"),
            reply_markup=language_keyboard(i18n),
        )
        return

    lang = user["lang"]
    await message.answer(
        i18n.t(lang, "welcome.main"),
        reply_markup=user_menu_keyboard(lang, i18n),
    )


@router.callback_query(F.data.startswith("lang:set:"))
async def set_language_handler(call: CallbackQuery, db: Database, i18n: I18n) -> None:
    lang = call.data.split(":")[-1]
    if lang not in {"fa", "en"}:
        await call.answer()
        return

    await db.ensure_user(call.from_user.id, call.from_user.username)
    await db.set_language(call.from_user.id, lang)
    await call.message.edit_text(
        i18n.t(lang, "language.changed"),
        reply_markup=user_menu_keyboard(lang, i18n),
    )
    await call.answer()
