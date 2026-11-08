"""Pure date and birthday filtering helpers."""
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
    return (isinstance(start, str) and len(start) == 10
            and isinstance(title, str) and keyword.casefold() in title.casefold())


def safe_filename(identifier: str) -> str:
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:24] + ".json"


def normalize_people(metadata):
    if isinstance(metadata, dict) and isinstance(metadata.get('people'), list):
        return [p for p in metadata['people'] if isinstance(p, dict)]
    if isinstance(metadata, list):
        return [p for p in metadata if isinstance(p, dict)]
    return [metadata] if isinstance(metadata, dict) else []


def birthday_on_event(dob, event_day):
    """Return age on the event date if month/day corresponds to this birthday."""
    if not dob or dob > event_day:
        return None
    if (dob.month, dob.day) == (event_day.month, event_day.day):
        return event_day.year - dob.year
    if (dob.month, dob.day) == (2, 29) and (event_day.month, event_day.day) in ((2, 28), (3, 1)):
        return event_day.year - dob.year
    return None
