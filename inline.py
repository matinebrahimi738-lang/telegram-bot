from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from telegram_bot.utils.i18n import I18n


def language_keyboard(i18n: I18n) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=i18n.t("fa", "language.fa"), callback_data="lang:set:fa")
    kb.button(text=i18n.t("en", "language.en"), callback_data="lang:set:en")
    kb.adjust(2)
    return kb.as_markup()


def user_menu_keyboard(lang: str, i18n: I18n) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=i18n.t(lang, "menu.join"), callback_data="user:join")
    kb.button(text=i18n.t(lang, "menu.guide"), callback_data="user:guide")
    kb.button(text=i18n.t(lang, "menu.rules"), callback_data="user:rules")
    kb.button(text=i18n.t(lang, "menu.ranking"), callback_data="user:ranking")
    kb.button(text=i18n.t(lang, "menu.language"), callback_data="user:language")
    kb.button(text=i18n.t(lang, "menu.support"), callback_data="user:support")
    kb.adjust(2, 2, 2)
    return kb.as_markup()


def directions_keyboard(lang: str, i18n: I18n, match_id: int, round_no: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for direction in ("left", "center", "right"):
        kb.button(
            text=i18n.t(lang, f"directions.{direction}"),
            callback_data=f"dir:{match_id}:{round_no}:{direction}",
        )
    kb.adjust(3)
    return kb.as_markup()


def admin_menu_keyboard(lang: str, i18n: I18n) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=i18n.t(lang, "admin.create_match"), callback_data="admin:create_match")
    kb.button(text=i18n.t(lang, "admin.active_matches"), callback_data="admin:active_matches")
    kb.button(text=i18n.t(lang, "admin.manage_players"), callback_data="admin:players")
    kb.button(text=i18n.t(lang, "admin.stats"), callback_data="admin:stats")
    kb.button(text=i18n.t(lang, "admin.ranking"), callback_data="admin:ranking")
    kb.button(text=i18n.t(lang, "admin.broadcast"), callback_data="admin:broadcast")
    kb.button(text=i18n.t(lang, "admin.settings"), callback_data="admin:settings")
    kb.button(text=i18n.t(lang, "admin.delete_match"), callback_data="admin:delete_match")
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup()


def rounds_keyboard(lang: str, i18n: I18n) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=i18n.t(lang, "admin.rounds_3"), callback_data="admin:rounds:3")
    kb.button(text=i18n.t(lang, "admin.rounds_5"), callback_data="admin:rounds:5")
    kb.adjust(2)
    return kb.as_markup()


def players_keyboard(lang: str, i18n: I18n, players: list[dict], prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in players:
        display = p.get("full_name") or f"#{p['id']}"
        kb.button(text=f"👤 {display}", callback_data=f"{prefix}:{p['id']}")
    kb.adjust(1)
    return kb.as_markup()


def round_result_keyboard(lang: str, i18n: I18n, match_id: int, round_no: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=i18n.t(lang, "results.goal"), callback_data=f"admin:result:{match_id}:{round_no}:goal")
    kb.button(text=i18n.t(lang, "results.save"), callback_data=f"admin:result:{match_id}:{round_no}:save")
    kb.button(text=i18n.t(lang, "results.out"), callback_data=f"admin:result:{match_id}:{round_no}:out")
    kb.adjust(3)
    return kb.as_markup()


def broadcast_target_keyboard(lang: str, i18n: I18n) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=i18n.t(lang, "broadcast.fa"), callback_data="admin:broadcast_target:fa")
    kb.button(text=i18n.t(lang, "broadcast.en"), callback_data="admin:broadcast_target:en")
    kb.button(text=i18n.t(lang, "broadcast.all"), callback_data="admin:broadcast_target:all")
    kb.adjust(1)
    return kb.as_markup()


def matches_keyboard(lang: str, i18n: I18n, match_ids: list[int], prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for mid in match_ids:
        kb.button(text=f"🎯 {i18n.t(lang, 'common.match')} #{mid}", callback_data=f"{prefix}:{mid}")
    kb.adjust(1)
    return kb.as_markup()
