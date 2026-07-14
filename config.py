from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(slots=True)
class Config:
    bot_token: str
    admin_ids: List[int]
    support_username: str
    sqlite_path: str
    log_level: str



def _parse_admin_ids(raw: str) -> List[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip().isdigit()]



def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_ids = _parse_admin_ids(os.getenv("ADMIN_ID", ""))
    support_username = os.getenv("SUPPORT_USERNAME", "@support").strip()
    sqlite_path = os.getenv("SQLITE_PATH", str(Path("telegram_bot") / "data" / "bot.db")).strip()
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    if not admin_ids:
        raise RuntimeError("ADMIN_ID is required")

    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        support_username=support_username,
        sqlite_path=sqlite_path,
        log_level=log_level,
    )
