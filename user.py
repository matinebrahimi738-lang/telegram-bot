from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.config import Config
from telegram_bot.database.db import Database
from telegram_bot.keyboards.inline import directions_keyboard, language_keyboard, user_menu_keyboard
from telegram_bot.services.match_service import MatchService
from telegram_bot.states.forms import RegistrationState
from telegram_bot.utils.i18n import I18n
from telegram_bot.utils.validators import normalize_text, validate_country, validate_name


router = Router()


async def _user_lang(db: Database, tg_id: int) -> str:
    user = await db.get_user_by_tg(tg_id)
    if not user:
        return "en"
    return user["lang"] if user["lang"] in {"fa", "en"} else "en"


@router.callback_query(F.data == "user:language")
async def user_language(call: CallbackQuery, i18n: I18n) -> None:
    await call.message.edit_text(i18n.t("en", "language.choose"), reply_markup=language_keyboard(i18n))
    await call.answer()


@router.callback_query(F.data == "user:guide")
async def user_guide(call: CallbackQuery, db: Database, i18n: I18n) -> None:
    lang = await _user_lang(db, call.from_user.id)
    await call.message.edit_text(i18n.t(lang, "pages.guide"), reply_markup=user_menu_keyboard(lang, i18n))
    await call.answer()


@router.callback_query(F.data == "user:rules")
async def user_rules(call: CallbackQuery, db: Database, i18n: I18n) -> None:
    lang = await _user_lang(db, call.from_user.id)
    await call.message.edit_text(i18n.t(lang, "pages.rules"), reply_markup=user_menu_keyboard(lang, i18n))
    await call.answer()


@router.callback_query(F.data == "user:support")
async def user_support(call: CallbackQuery, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _user_lang(db, call.from_user.id)
    await call.message.edit_text(
        i18n.t(lang, "pages.support", support=config.support_username),
        reply_markup=user_menu_keyboard(lang, i18n),
    )
    await call.answer()


@router.callback_query(F.data == "user:ranking")
async def user_ranking(call: CallbackQuery, db: Database, i18n: I18n) -> None:
    lang = await _user_lang(db, call.from_user.id)
    rows = await db.get_leaderboard(limit=10)
    if not rows:
        text = i18n.t(lang, "ranking.empty")
    else:
        lines = [i18n.t(lang, "ranking.title")]
        for idx, row in enumerate(rows, start=1):
            lines.append(
                i18n.t(
                    lang,
                    "ranking.line",
                    idx=idx,
                    name=row["full_name"] or "-",
                    points=row["points"],
                    played=row["matches_played"],
                    win=row["wins"],
                    draw=row["draws"],
                    loss=row["losses"],
                    gd=row["goal_diff"],
                )
            )
        text = "\n".join(lines)

    await call.message.edit_text(text, reply_markup=user_menu_keyboard(lang, i18n))
    await call.answer()


@router.callback_query(F.data == "user:join")
async def join_competition(call: CallbackQuery, db: Database, i18n: I18n, state: FSMContext) -> None:
    user = await db.ensure_user(call.from_user.id, call.from_user.username)
    lang = user["lang"] if user["lang"] in {"fa", "en"} else "en"

    if int(user["is_registered"]) == 0:
        await state.set_state(RegistrationState.waiting_name)
        await call.message.edit_text(i18n.t(lang, "register.ask_name"))
        await call.answer()
        return

    pending = await db.get_pending_round_for_user(int(user["id"]))
    if not pending:
        await call.message.edit_text(i18n.t(lang, "match.no_active"), reply_markup=user_menu_keyboard(lang, i18n))
        await call.answer()
        return

    already_selected = (
        pending.shooter_direction is not None if pending.shooter_id == int(user["id"]) else pending.keeper_direction is not None
    )
    if already_selected:
        await call.message.edit_text(i18n.t(lang, "match.already_selected"), reply_markup=user_menu_keyboard(lang, i18n))
        await call.answer()
        return

    role_key = "match.role_shooter" if pending.shooter_id == int(user["id"]) else "match.role_keeper"
    await call.message.edit_text(
        i18n.t(lang, "match.choose_direction", role=i18n.t(lang, role_key), round_no=pending.round_no),
        reply_markup=directions_keyboard(lang, i18n, pending.match_id, pending.round_no),
    )
    await call.answer()


@router.message(RegistrationState.waiting_name)
async def register_name(message: Message, db: Database, i18n: I18n, state: FSMContext) -> None:
    lang = await _user_lang(db, message.from_user.id)
    value = normalize_text(message.text or "")
    if not validate_name(value):
        await message.answer(i18n.t(lang, "register.invalid_name"))
        return

    await state.update_data(full_name=value)
    await state.set_state(RegistrationState.waiting_country)
    await message.answer(i18n.t(lang, "register.ask_country"))


@router.message(RegistrationState.waiting_country)
async def register_country(message: Message, db: Database, i18n: I18n, state: FSMContext) -> None:
    lang = await _user_lang(db, message.from_user.id)
    value = normalize_text(message.text or "")
    if not validate_country(value):
        await message.answer(i18n.t(lang, "register.invalid_country"))
        return

    data = await state.get_data()
    full_name = data.get("full_name", "")
    created = await db.register_player(
        message.from_user.id,
        full_name=full_name,
        country=value,
        username=message.from_user.username,
    )
    await state.clear()

    if not created:
        await message.answer(i18n.t(lang, "register.duplicate"), reply_markup=user_menu_keyboard(lang, i18n))
        return

    await message.answer(i18n.t(lang, "register.success"), reply_markup=user_menu_keyboard(lang, i18n))


@router.callback_query(F.data.startswith("dir:"))
async def choose_direction(call: CallbackQuery, db: Database, i18n: I18n, service: MatchService) -> None:
    user = await db.get_user_by_tg(call.from_user.id)
    if not user:
        await call.answer()
        return

    lang = user["lang"] if user["lang"] in {"fa", "en"} else "en"
    _, match_id, round_no, direction = call.data.split(":")
    if direction not in {"left", "center", "right"}:
        await call.answer()
        return

    ok = await db.save_direction(int(match_id), int(round_no), int(user["id"]), direction)
    if not ok:
        await call.message.edit_text(i18n.t(lang, "match.direction_rejected"), reply_markup=user_menu_keyboard(lang, i18n))
        await call.answer()
        return

    await call.message.edit_text(i18n.t(lang, "match.direction_saved"), reply_markup=user_menu_keyboard(lang, i18n))
    await service.notify_admin_if_round_ready(call.bot, int(match_id), int(round_no))
    await call.answer()
