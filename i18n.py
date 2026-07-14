from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class I18n:
    def __init__(self, locales_dir: str = "telegram_bot/locales") -> None:
        self.locales_dir = Path(locales_dir)
        self._cache: dict[str, dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        self._cache.clear()
        for code in ("fa", "en"):
            file_path = self.locales_dir / f"{code}.json"
            with file_path.open("r", encoding="utf-8") as f:
                self._cache[code] = json.load(f)

    def t(self, lang: str, key: str, **kwargs: Any) -> str:
        data = self._cache.get(lang) or self._cache.get("en", {})
        value = self._resolve(data, key)
        if value is None:
            value = self._resolve(self._cache.get("en", {}), key)
        if value is None:
            return key
        if isinstance(value, str):
            return value.format(**kwargs)
        return str(value)

    def _resolve(self, data: dict[str, Any], key: str) -> Any:
        current: Any = data
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current
