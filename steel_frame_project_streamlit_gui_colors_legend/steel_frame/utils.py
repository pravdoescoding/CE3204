from __future__ import annotations

import re
from typing import Any


def normalize_name(value: str | None) -> str:
    if value is None:
        return ""
    s = str(value).replace("\xa0", " ").strip().upper()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*/\s*", "/", s)
    return s


def safe_float(value: Any) -> float:
    if value is None:
        raise ValueError("Found an empty numeric cell in the database.")
    return float(value)


def safe_int(value: Any) -> int:
    if value is None:
        raise ValueError("Found an empty integer cell in the database.")
    return int(value)
