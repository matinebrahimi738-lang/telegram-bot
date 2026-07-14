from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from telegram_bot.config import Config
from telegram_bot.database.db import Database
from telegram_bot.keyboards.inline import (
    admin_menu_keyboard,
    broadcast_target_keyboard,
    matches_keyboard,
    players_keyboard,
    rounds_keyboard,
)
from telegram_bot.services.match_service import MatchService
from telegram_bot.states.forms import AdminBroadcastState, AdminCreateMatchState
from telegram_bot.utils.i18n import I18n


router = Router()


async def _admin_lang(db: Database, tg_id: int) -> str:
    user = await db.ensure_user(tg_id, None)
    return user["lang"] if user["lang"] in {"fa", "en"} else "en"


async def _deny_if_not_admin(message_or_call: Message | CallbackQuery, config: Config, i18n: I18n, lang: str) -> bool:
    user_id = message_or_call.from_user.id
    if user_id in config.admin_ids:
        return False
    if isinstance(message_or_call, Message):
        await message_or_call.answer(i18n.t(lang, "errors.not_admin"))
    else:
        await message_or_call.answer(i18n.t(lang, "errors.not_admin"), show_alert=True)
    return True


@router.message(Command("admin"))
async def admin_panel(message: Message, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _admin_lang(db, message.from_user.id)
    if await _deny_if_not_admin(message, config, i18n, lang):
        return

    await message.answer(i18n.t(lang, "admin.panel_title"), reply_markup=admin_menu_keyboard(lang, i18n))


@router.callback_query(F.data == "admin:create_match")
async def admin_create_match(call: CallbackQuery, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return
    await call.message.edit_text(i18n.t(lang, "admin.select_rounds"), reply_markup=rounds_keyboard(lang, i18n))
    await call.answer()


@router.callback_query(F.data.startswith("admin:rounds:"))
async def admin_select_rounds(call: CallbackQuery, db: Database, i18n: I18n, config: Config, state: FSMContext) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    rounds = int(call.data.split(":")[-1])
    players = await db.get_registered_users()
    if len(players) < 2:
        await call.message.edit_text(i18n.t(lang, "admin.not_enough_players"), reply_markup=admin_menu_keyboard(lang, i18n))
        await call.answer()
        return

    await state.set_state(AdminCreateMatchState.waiting_player1)
    await state.update_data(rounds=rounds)
    await call.message.edit_text(
        i18n.t(lang, "admin.select_player1"),
        reply_markup=players_keyboard(lang, i18n, [dict(p) for p in players], "admin:pick1"),
    )
    await call.answer()


@router.callback_query(AdminCreateMatchState.waiting_player1, F.data.startswith("admin:pick1:"))
async def admin_pick_player1(call: CallbackQuery, db: Database, i18n: I18n, config: Config, state: FSMContext) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    player1_id = int(call.data.split(":")[-1])
    players = await db.get_registered_users()
    remaining = [dict(p) for p in players if int(p["id"]) != player1_id]

    await state.set_state(AdminCreateMatchState.waiting_player2)
    await state.update_data(player1_id=player1_id)
    await call.message.edit_text(
        i18n.t(lang, "admin.select_player2"),
        reply_markup=players_keyboard(lang, i18n, remaining, "admin:pick2"),
    )
    await call.answer()


@router.callback_query(AdminCreateMatchState.waiting_player2, F.data.startswith("admin:pick2:"))
async def admin_pick_player2(call: CallbackQuery, db: Database, i18n: I18n, config: Config, state: FSMContext, service: MatchService) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    player2_id = int(call.data.split(":")[-1])
    data = await state.get_data()
    rounds = int(data.get("rounds", 3))
    player1_id = int(data.get("player1_id"))
    await state.clear()

    if player1_id == player2_id:
        await call.message.edit_text(i18n.t(lang, "admin.same_player_error"), reply_markup=admin_menu_keyboard(lang, i18n))
        await call.answer()
        return

    match_id = await db.create_match(rounds, player1_id, player2_id)
    pending = await db.ensure_round(match_id)
    if pending:
        await service.notify_players_round_start(call.bot, pending)

    await call.message.edit_text(
        i18n.t(lang, "admin.match_created", match_id=match_id, rounds=rounds),
        reply_markup=admin_menu_keyboard(lang, i18n),
    )
    await call.answer()


@router.callback_query(F.data == "admin:active_matches")
async def admin_active_matches(call: CallbackQuery, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    matches = await db.get_active_matches()
    if not matches:
        await call.message.edit_text(i18n.t(lang, "admin.no_active_matches"), reply_markup=admin_menu_keyboard(lang, i18n))
        await call.answer()
        return

    lines = [i18n.t(lang, "admin.active_matches_title")]
    for m in matches:
        lines.append(
            i18n.t(
                lang,
                "admin.active_match_line",
                match_id=m["id"],
                round_now=m["current_round"],
                rounds=m["rounds"],
                score1=m["score1"],
                score2=m["score2"],
            )
        )

    await call.message.edit_text("\n".join(lines), reply_markup=admin_menu_keyboard(lang, i18n))
    await call.answer()


@router.callback_query(F.data == "admin:players")
async def admin_players(call: CallbackQuery, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return
    players = await db.get_registered_users()
    if not players:
        await call.message.edit_text(i18n.t(lang, "admin.no_players"), reply_markup=admin_menu_keyboard(lang, i18n))
        await call.answer()
        return

    lines = [i18n.t(lang, "admin.players_title")]
    for p in players:
        lines.append(
            i18n.t(
                lang,
                "admin.player_line",
                id=p["id"],
                name=p["full_name"] or "-",
                username=(f"@{p['username']}" if p["username"] else "-"),
                country=p["country"] or "-",
            )
        )
    await call.message.edit_text("\n".join(lines), reply_markup=admin_menu_keyboard(lang, i18n))
    await call.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(call: CallbackQuery, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return
    data = await db.count_overview()
    await call.message.edit_text(
        i18n.t(
            lang,
            "admin.stats_text",
            users=data["users"],
            registered=data["registered"],
            active=data["active"],
            finished=data["finished"],
        ),
        reply_markup=admin_menu_keyboard(lang, i18n),
    )
    await call.answer()


@router.callback_query(F.data == "admin:ranking")
async def admin_ranking(call: CallbackQuery, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    rows = await db.get_leaderboard(limit=20)
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

    await call.message.edit_text(text, reply_markup=admin_menu_keyboard(lang, i18n))
    await call.answer()


@router.callback_query(F.data == "admin:settings")
async def admin_settings(call: CallbackQuery, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    await call.message.edit_text(
        i18n.t(lang, "admin.settings_text", support=config.support_username),
        reply_markup=admin_menu_keyboard(lang, i18n),
    )
    await call.answer()


@router.callback_query(F.data == "admin:delete_match")
async def admin_delete_match_start(call: CallbackQuery, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    matches = await db.get_active_matches()
    if not matches:
        await call.message.edit_text(i18n.t(lang, "admin.no_active_matches"), reply_markup=admin_menu_keyboard(lang, i18n))
        await call.answer()
        return

    ids = [int(m["id"]) for m in matches]
    await call.message.edit_text(
        i18n.t(lang, "admin.select_match_delete"),
        reply_markup=matches_keyboard(lang, i18n, ids, "admin:delete_pick"),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:delete_pick:"))
async def admin_delete_match_apply(call: CallbackQuery, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    match_id = int(call.data.split(":")[-1])
    await db.delete_match(match_id)
    await call.message.edit_text(i18n.t(lang, "admin.match_deleted", match_id=match_id), reply_markup=admin_menu_keyboard(lang, i18n))
    await call.answer()


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(call: CallbackQuery, db: Database, i18n: I18n, config: Config) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    await call.message.edit_text(
        i18n.t(lang, "broadcast.select_target"),
        reply_markup=broadcast_target_keyboard(lang, i18n),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:broadcast_target:"))
async def admin_broadcast_target(call: CallbackQuery, db: Database, i18n: I18n, config: Config, state: FSMContext) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    target = call.data.split(":")[-1]
    await state.set_state(AdminBroadcastState.waiting_message)
    await state.update_data(target=target)
    await call.message.edit_text(i18n.t(lang, "broadcast.ask_message"))
    await call.answer()


@router.message(AdminBroadcastState.waiting_message)
async def admin_broadcast_send(message: Message, db: Database, i18n: I18n, config: Config, state: FSMContext) -> None:
    lang = await _admin_lang(db, message.from_user.id)
    if await _deny_if_not_admin(message, config, i18n, lang):
        return

    data = await state.get_data()
    target = data.get("target", "all")
    text = (message.text or "").strip()
    if not text:
        await message.answer(i18n.t(lang, "broadcast.empty"))
        return

    users = await db.get_users_for_broadcast(target)
    sent = 0
    failed = 0
    for user in users:
        try:
            await message.bot.send_message(int(user["tg_id"]), text)
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        i18n.t(lang, "broadcast.done", sent=sent, failed=failed),
        reply_markup=admin_menu_keyboard(lang, i18n),
    )


@router.callback_query(F.data.startswith("admin:result:"))
async def admin_round_result(call: CallbackQuery, db: Database, i18n: I18n, config: Config, service: MatchService) -> None:
    lang = await _admin_lang(db, call.from_user.id)
    if await _deny_if_not_admin(call, config, i18n, lang):
        return

    _, _, match_id, round_no, result = call.data.split(":")
    updated_match = await db.resolve_round(int(match_id), int(round_no), result)
    if not updated_match:
        await call.answer(i18n.t(lang, "admin.result_rejected"), show_alert=True)
        return

    await service.announce_round_result(call.bot, int(match_id), int(round_no), result)

    if updated_match["status"] == "finished":
        await service.announce_match_finished(call.bot, int(match_id))
        await call.message.edit_text(
            i18n.t(lang, "admin.match_finished", match_id=match_id),
            reply_markup=admin_menu_keyboard(lang, i18n),
        )
    else:
        pending = await db.ensure_round(int(match_id))
        if pending:
            await service.notify_players_round_start(call.bot, pending)
        await call.message.edit_text(
            i18n.t(lang, "admin.result_saved_next_round", match_id=match_id),
            reply_markup=admin_menu_keyboard(lang, i18n),
        )
    await call.answer()
