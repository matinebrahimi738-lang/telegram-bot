from __future__ import annotations

from aiogram import Bot

from telegram_bot.database.db import Database, PendingRound
from telegram_bot.keyboards.inline import round_result_keyboard
from telegram_bot.utils.i18n import I18n


class MatchService:
    def __init__(self, db: Database, i18n: I18n, admin_ids: list[int]) -> None:
        self.db = db
        self.i18n = i18n
        self.admin_ids = admin_ids

    async def notify_admin_if_round_ready(self, bot: Bot, match_id: int, round_no: int) -> None:
        round_row = await self.db.get_round(match_id, round_no)
        if not round_row:
            return
        if not round_row["shooter_direction"] or not round_row["keeper_direction"]:
            return
        if round_row["admin_result"]:
            return
        if int(round_row["admin_notified"]) == 1:
            return

        shooter = await self.db.get_user_by_id(int(round_row["shooter_id"]))
        keeper = await self.db.get_user_by_id(int(round_row["keeper_id"]))
        lang = "en"
        text = self.i18n.t(
            lang,
            "admin.round_ready",
            match_id=match_id,
            round_no=round_no,
            shooter=(shooter["full_name"] if shooter else "-"),
            keeper=(keeper["full_name"] if keeper else "-"),
            shooter_dir=self.i18n.t(lang, f"directions.{round_row['shooter_direction']}"),
            keeper_dir=self.i18n.t(lang, f"directions.{round_row['keeper_direction']}"),
        )

        kb = round_result_keyboard(lang, self.i18n, match_id, round_no)
        for admin_id in self.admin_ids:
            await bot.send_message(admin_id, text, reply_markup=kb)

        await self.db.mark_admin_notified(match_id, round_no)

    async def notify_players_round_start(self, bot: Bot, pending: PendingRound) -> None:
        shooter = await self.db.get_user_by_id(pending.shooter_id)
        keeper = await self.db.get_user_by_id(pending.keeper_id)
        if not shooter or not keeper:
            return

        shooter_text = self.i18n.t(
            shooter["lang"],
            "match.round_start_shooter",
            round_no=pending.round_no,
        )
        keeper_text = self.i18n.t(
            keeper["lang"],
            "match.round_start_keeper",
            round_no=pending.round_no,
        )
        await bot.send_message(int(shooter["tg_id"]), shooter_text)
        await bot.send_message(int(keeper["tg_id"]), keeper_text)

    async def announce_round_result(self, bot: Bot, match_id: int, round_no: int, result: str) -> None:
        match = await self.db.get_match(match_id)
        round_row = await self.db.get_round(match_id, round_no)
        if not match or not round_row:
            return

        p1 = await self.db.get_user_by_id(int(match["player1_id"]))
        p2 = await self.db.get_user_by_id(int(match["player2_id"]))
        if not p1 or not p2:
            return

        for p in (p1, p2):
            text = self.i18n.t(
                p["lang"],
                "match.round_result",
                round_no=round_no,
                result=self.i18n.t(p["lang"], f"results.{result}").split(" ", 1)[-1],
                score1=match["score1"],
                score2=match["score2"],
            )
            await bot.send_message(int(p["tg_id"]), text)

    async def announce_match_finished(self, bot: Bot, match_id: int) -> None:
        match = await self.db.get_match(match_id)
        if not match:
            return
        p1 = await self.db.get_user_by_id(int(match["player1_id"]))
        p2 = await self.db.get_user_by_id(int(match["player2_id"]))
        if not p1 or not p2:
            return

        if int(match["score1"]) > int(match["score2"]):
            winner_name = p1["full_name"] or p1["username"] or "-"
        elif int(match["score2"]) > int(match["score1"]):
            winner_name = p2["full_name"] or p2["username"] or "-"
        else:
            winner_name = "-"

        for p in (p1, p2):
            text = self.i18n.t(
                p["lang"],
                "match.final_result",
                score1=match["score1"],
                score2=match["score2"],
                winner=winner_name,
            )
            await bot.send_message(int(p["tg_id"]), text)

        await self.db.update_stats_after_match(match_id)
