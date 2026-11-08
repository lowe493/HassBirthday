"""Pure helpers for event filtering and birthday dates."""
from __future__ import annotations
from datetime import date, datetime
import hashlib

def parse_uk_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        return None

def is_birthday_event(event: dict, keyword: str = "birthday") -> bool:
    title = event.get("summary") or ""
    start = event.get("start")
    # Home Assistant exposes all-day events as a date-only ISO string.
    return (isinstance(start, str) and len(start) == 10
            and isinstance(title, str) and keyword.casefold() in title.casefold())

def safe_filename(identifier: str) -> str:
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:24] + ".json"
