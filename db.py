from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import aiosqlite


@dataclass(slots=True)
class PendingRound:
    match_id: int
    round_no: int
    shooter_id: int
    keeper_id: int
    shooter_direction: Optional[str]
    keeper_direction: Optional[str]


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = asyncio.Lock()

    async def connect(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    async def init(self) -> None:
        Path(os.path.dirname(self.db_path) or ".").mkdir(parents=True, exist_ok=True)
        async with self.connect() as conn:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    country TEXT,
                    lang TEXT NOT NULL DEFAULT 'unset',
                    is_registered INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rounds INTEGER NOT NULL CHECK(rounds IN (3,5)),
                    player1_id INTEGER NOT NULL,
                    player2_id INTEGER NOT NULL,
                    current_round INTEGER NOT NULL DEFAULT 1,
                    score1 INTEGER NOT NULL DEFAULT 0,
                    score2 INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','finished','deleted')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    finished_at TEXT,
                    FOREIGN KEY(player1_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(player2_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS rounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER NOT NULL,
                    round_no INTEGER NOT NULL,
                    shooter_id INTEGER NOT NULL,
                    keeper_id INTEGER NOT NULL,
                    shooter_direction TEXT,
                    keeper_direction TEXT,
                    admin_result TEXT,
                    admin_notified INTEGER NOT NULL DEFAULT 0,
                    resolved_at TEXT,
                    UNIQUE(match_id, round_no),
                    FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE,
                    FOREIGN KEY(shooter_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(keeper_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS player_stats (
                    user_id INTEGER PRIMARY KEY,
                    matches_played INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    draws INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    goals_scored INTEGER NOT NULL DEFAULT 0,
                    goals_conceded INTEGER NOT NULL DEFAULT 0,
                    saves INTEGER NOT NULL DEFAULT 0,
                    outs INTEGER NOT NULL DEFAULT 0,
                    points INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            await conn.commit()

    async def get_user_by_tg(self, tg_id: int) -> Optional[aiosqlite.Row]:
        async with self.connect() as conn:
            cur = await conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
            return await cur.fetchone()

    async def get_user_by_id(self, user_id: int) -> Optional[aiosqlite.Row]:
        async with self.connect() as conn:
            cur = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return await cur.fetchone()

    async def ensure_user(self, tg_id: int, username: Optional[str]) -> aiosqlite.Row:
        async with self._lock:
            async with self.connect() as conn:
                cur = await conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
                row = await cur.fetchone()
                if row:
                    if username is not None:
                        await conn.execute("UPDATE users SET username = ? WHERE tg_id = ?", (username, tg_id))
                        await conn.commit()
                    cur = await conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
                    return await cur.fetchone()

                await conn.execute(
                    "INSERT INTO users (tg_id, username, lang) VALUES (?, ?, 'unset')",
                    (tg_id, username),
                )
                await conn.commit()
                cur = await conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
                return await cur.fetchone()

    async def set_language(self, tg_id: int, lang: str) -> None:
        async with self.connect() as conn:
            await conn.execute("UPDATE users SET lang = ? WHERE tg_id = ?", (lang, tg_id))
            await conn.commit()

    async def register_player(self, tg_id: int, full_name: str, country: str, username: Optional[str]) -> bool:
        async with self._lock:
            async with self.connect() as conn:
                cur = await conn.execute("SELECT is_registered FROM users WHERE tg_id = ?", (tg_id,))
                row = await cur.fetchone()
                if not row:
                    return False
                if int(row["is_registered"]) == 1:
                    return False

                await conn.execute(
                    """
                    UPDATE users
                    SET full_name = ?, country = ?, username = ?, is_registered = 1
                    WHERE tg_id = ?
                    """,
                    (full_name, country, username, tg_id),
                )
                await conn.commit()
                return True

    async def get_registered_users(self) -> list[aiosqlite.Row]:
        async with self.connect() as conn:
            cur = await conn.execute(
                "SELECT * FROM users WHERE is_registered = 1 ORDER BY full_name COLLATE NOCASE"
            )
            return await cur.fetchall()

    async def create_match(self, rounds: int, player1_id: int, player2_id: int) -> int:
        async with self._lock:
            async with self.connect() as conn:
                cur = await conn.execute(
                    """
                    INSERT INTO matches (rounds, player1_id, player2_id)
                    VALUES (?, ?, ?)
                    """,
                    (rounds, player1_id, player2_id),
                )
                match_id = cur.lastrowid
                await conn.commit()
        await self.ensure_round(match_id)
        return int(match_id)

    async def get_match(self, match_id: int) -> Optional[aiosqlite.Row]:
        async with self.connect() as conn:
            cur = await conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
            return await cur.fetchone()

    async def get_active_matches(self) -> list[aiosqlite.Row]:
        async with self.connect() as conn:
            cur = await conn.execute("SELECT * FROM matches WHERE status = 'active' ORDER BY id DESC")
            return await cur.fetchall()

    async def delete_match(self, match_id: int) -> None:
        async with self.connect() as conn:
            await conn.execute("UPDATE matches SET status = 'deleted', finished_at = ? WHERE id = ?", (datetime.utcnow().isoformat(), match_id))
            await conn.commit()

    async def ensure_round(self, match_id: int) -> Optional[PendingRound]:
        async with self._lock:
            async with self.connect() as conn:
                cur = await conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
                match = await cur.fetchone()
                if not match or match["status"] != "active":
                    return None
                round_no = int(match["current_round"])

                cur = await conn.execute(
                    "SELECT * FROM rounds WHERE match_id = ? AND round_no = ?",
                    (match_id, round_no),
                )
                row = await cur.fetchone()
                if row:
                    return PendingRound(
                        match_id=match_id,
                        round_no=round_no,
                        shooter_id=int(row["shooter_id"]),
                        keeper_id=int(row["keeper_id"]),
                        shooter_direction=row["shooter_direction"],
                        keeper_direction=row["keeper_direction"],
                    )

                player1 = int(match["player1_id"])
                player2 = int(match["player2_id"])
                shooter = player1 if round_no % 2 == 1 else player2
                keeper = player2 if round_no % 2 == 1 else player1

                await conn.execute(
                    """
                    INSERT INTO rounds (match_id, round_no, shooter_id, keeper_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (match_id, round_no, shooter, keeper),
                )
                await conn.commit()
                return PendingRound(
                    match_id=match_id,
                    round_no=round_no,
                    shooter_id=shooter,
                    keeper_id=keeper,
                    shooter_direction=None,
                    keeper_direction=None,
                )

    async def get_pending_round_for_user(self, user_id: int) -> Optional[PendingRound]:
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                SELECT m.id AS match_id, m.current_round, r.shooter_id, r.keeper_id, r.shooter_direction, r.keeper_direction
                FROM matches m
                JOIN rounds r ON r.match_id = m.id AND r.round_no = m.current_round
                WHERE m.status = 'active' AND (r.shooter_id = ? OR r.keeper_id = ?)
                ORDER BY m.id DESC
                LIMIT 1
                """,
                (user_id, user_id),
            )
            row = await cur.fetchone()
            if not row:
                return None
            return PendingRound(
                match_id=int(row["match_id"]),
                round_no=int(row["current_round"]),
                shooter_id=int(row["shooter_id"]),
                keeper_id=int(row["keeper_id"]),
                shooter_direction=row["shooter_direction"],
                keeper_direction=row["keeper_direction"],
            )

    async def save_direction(self, match_id: int, round_no: int, user_id: int, direction: str) -> bool:
        async with self._lock:
            async with self.connect() as conn:
                cur = await conn.execute(
                    "SELECT * FROM rounds WHERE match_id = ? AND round_no = ?",
                    (match_id, round_no),
                )
                row = await cur.fetchone()
                if not row:
                    return False

                if int(row["shooter_id"]) == user_id:
                    if row["shooter_direction"] is not None:
                        return False
                    await conn.execute(
                        "UPDATE rounds SET shooter_direction = ? WHERE match_id = ? AND round_no = ?",
                        (direction, match_id, round_no),
                    )
                elif int(row["keeper_id"]) == user_id:
                    if row["keeper_direction"] is not None:
                        return False
                    await conn.execute(
                        "UPDATE rounds SET keeper_direction = ? WHERE match_id = ? AND round_no = ?",
                        (direction, match_id, round_no),
                    )
                else:
                    return False

                await conn.commit()
                return True

    async def get_round(self, match_id: int, round_no: int) -> Optional[aiosqlite.Row]:
        async with self.connect() as conn:
            cur = await conn.execute(
                "SELECT * FROM rounds WHERE match_id = ? AND round_no = ?",
                (match_id, round_no),
            )
            return await cur.fetchone()

    async def mark_admin_notified(self, match_id: int, round_no: int) -> None:
        async with self.connect() as conn:
            await conn.execute(
                "UPDATE rounds SET admin_notified = 1 WHERE match_id = ? AND round_no = ?",
                (match_id, round_no),
            )
            await conn.commit()

    async def resolve_round(self, match_id: int, round_no: int, result: str) -> Optional[aiosqlite.Row]:
        async with self._lock:
            async with self.connect() as conn:
                cur = await conn.execute(
                    "SELECT * FROM rounds WHERE match_id = ? AND round_no = ?",
                    (match_id, round_no),
                )
                round_row = await cur.fetchone()
                if not round_row or round_row["admin_result"] is not None:
                    return None

                await conn.execute(
                    """
                    UPDATE rounds
                    SET admin_result = ?, resolved_at = ?
                    WHERE match_id = ? AND round_no = ?
                    """,
                    (result, datetime.utcnow().isoformat(), match_id, round_no),
                )

                cur = await conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
                match = await cur.fetchone()
                if not match:
                    await conn.commit()
                    return None

                score1 = int(match["score1"])
                score2 = int(match["score2"])
                p1 = int(match["player1_id"])
                shooter = int(round_row["shooter_id"])

                if result == "goal":
                    if shooter == p1:
                        score1 += 1
                    else:
                        score2 += 1

                rounds_total = int(match["rounds"])
                current_round = int(match["current_round"])
                new_status = "active"
                finished_at = None

                if current_round >= rounds_total:
                    new_status = "finished"
                    finished_at = datetime.utcnow().isoformat()
                else:
                    current_round += 1

                await conn.execute(
                    """
                    UPDATE matches
                    SET current_round = ?, score1 = ?, score2 = ?, status = ?, finished_at = ?
                    WHERE id = ?
                    """,
                    (current_round, score1, score2, new_status, finished_at, match_id),
                )
                await conn.commit()

                cur = await conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
                return await cur.fetchone()

    async def update_stats_after_match(self, match_id: int) -> None:
        async with self._lock:
            async with self.connect() as conn:
                cur = await conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
                match = await cur.fetchone()
                if not match or match["status"] != "finished":
                    return

                p1 = int(match["player1_id"])
                p2 = int(match["player2_id"])
                s1 = int(match["score1"])
                s2 = int(match["score2"])

                cur = await conn.execute(
                    "SELECT shooter_id, keeper_id, admin_result FROM rounds WHERE match_id = ?",
                    (match_id,),
                )
                rounds = await cur.fetchall()

                saves_p1 = sum(1 for r in rounds if r["admin_result"] == "save" and int(r["keeper_id"]) == p1)
                saves_p2 = sum(1 for r in rounds if r["admin_result"] == "save" and int(r["keeper_id"]) == p2)
                outs_p1 = sum(1 for r in rounds if r["admin_result"] == "out" and int(r["shooter_id"]) == p1)
                outs_p2 = sum(1 for r in rounds if r["admin_result"] == "out" and int(r["shooter_id"]) == p2)

                await self._upsert_stats_row(conn, p1)
                await self._upsert_stats_row(conn, p2)

                p1_points, p2_points = 0, 0
                p1_win, p2_win = 0, 0
                p1_draw, p2_draw = 0, 0
                p1_loss, p2_loss = 0, 0
                if s1 > s2:
                    p1_points = 3
                    p1_win, p2_loss = 1, 1
                elif s2 > s1:
                    p2_points = 3
                    p2_win, p1_loss = 1, 1
                else:
                    p1_points = p2_points = 1
                    p1_draw = p2_draw = 1

                await conn.execute(
                    """
                    UPDATE player_stats
                    SET matches_played = matches_played + 1,
                        wins = wins + ?,
                        draws = draws + ?,
                        losses = losses + ?,
                        goals_scored = goals_scored + ?,
                        goals_conceded = goals_conceded + ?,
                        saves = saves + ?,
                        outs = outs + ?,
                        points = points + ?,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (p1_win, p1_draw, p1_loss, s1, s2, saves_p1, outs_p1, p1_points, datetime.utcnow().isoformat(), p1),
                )

                await conn.execute(
                    """
                    UPDATE player_stats
                    SET matches_played = matches_played + 1,
                        wins = wins + ?,
                        draws = draws + ?,
                        losses = losses + ?,
                        goals_scored = goals_scored + ?,
                        goals_conceded = goals_conceded + ?,
                        saves = saves + ?,
                        outs = outs + ?,
                        points = points + ?,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (p2_win, p2_draw, p2_loss, s2, s1, saves_p2, outs_p2, p2_points, datetime.utcnow().isoformat(), p2),
                )
                await conn.commit()

    async def _upsert_stats_row(self, conn: aiosqlite.Connection, user_id: int) -> None:
        await conn.execute(
            "INSERT OR IGNORE INTO player_stats (user_id) VALUES (?)",
            (user_id,),
        )

    async def get_leaderboard(self, limit: int = 20) -> list[aiosqlite.Row]:
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                SELECT u.full_name, u.username, u.country,
                       s.matches_played, s.wins, s.draws, s.losses,
                       s.goals_scored, s.goals_conceded, s.saves, s.outs, s.points,
                       (s.goals_scored - s.goals_conceded) AS goal_diff
                FROM player_stats s
                JOIN users u ON u.id = s.user_id
                ORDER BY s.points DESC, goal_diff DESC, s.goals_scored DESC, u.full_name ASC
                LIMIT ?
                """,
                (limit,),
            )
            return await cur.fetchall()

    async def count_overview(self) -> dict[str, int]:
        async with self.connect() as conn:
            users_cur = await conn.execute("SELECT COUNT(*) AS c FROM users")
            reg_cur = await conn.execute("SELECT COUNT(*) AS c FROM users WHERE is_registered = 1")
            active_cur = await conn.execute("SELECT COUNT(*) AS c FROM matches WHERE status = 'active'")
            finished_cur = await conn.execute("SELECT COUNT(*) AS c FROM matches WHERE status = 'finished'")
            return {
                "users": int((await users_cur.fetchone())["c"]),
                "registered": int((await reg_cur.fetchone())["c"]),
                "active": int((await active_cur.fetchone())["c"]),
                "finished": int((await finished_cur.fetchone())["c"]),
            }

    async def get_users_for_broadcast(self, target: str) -> list[aiosqlite.Row]:
        query = "SELECT tg_id, lang FROM users"
        params: tuple[Any, ...] = ()
        if target in {"fa", "en"}:
            query += " WHERE lang = ?"
            params = (target,)
        async with self.connect() as conn:
            cur = await conn.execute(query, params)
            return await cur.fetchall()

    async def active_match_by_user(self, user_id: int) -> Optional[aiosqlite.Row]:
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                SELECT * FROM matches
                WHERE status = 'active' AND (player1_id = ? OR player2_id = ?)
                ORDER BY id DESC LIMIT 1
                """,
                (user_id, user_id),
            )
            return await cur.fetchone()

    async def get_round_needing_admin(self) -> list[aiosqlite.Row]:
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                SELECT * FROM rounds
                WHERE shooter_direction IS NOT NULL
                  AND keeper_direction IS NOT NULL
                  AND admin_result IS NULL
                  AND admin_notified = 0
                ORDER BY match_id, round_no
                """
            )
            return await cur.fetchall()
