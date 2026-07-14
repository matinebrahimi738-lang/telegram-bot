from __future__ import annotations

import re

NAME_PATTERN = re.compile(r"^[\w\s\-'.\u0600-\u06FF]{2,40}$", re.UNICODE)
COUNTRY_PATTERN = re.compile(r"^[\w\s\-'.\u0600-\u06FF]{2,40}$", re.UNICODE)


def validate_name(value: str) -> bool:
    return bool(NAME_PATTERN.match(value.strip()))


def validate_country(value: str) -> bool:
    return bool(COUNTRY_PATTERN.match(value.strip()))


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split())
