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


def birthday_date_mismatch(dob: date | None, event_day: date) -> bool:
    """Flag a different calendar month/day without blocking the age calculation.

    A 29 February birthday observed on 28 February or 1 March in non-leap
    years is accepted as a valid calendar convention.
    """
    if dob is None:
        return False
    if (dob.month, dob.day) == (event_day.month, event_day.day):
        return False
    return not (dob.month == 2 and dob.day == 29
                and (event_day.month, event_day.day) in ((2, 28), (3, 1))
                and not _is_leap_year(event_day.year))


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def birthday_on_event(dob: date | None, event_day: date) -> int | None:
    """Age reached in the calendar event year, even when its date is wrong.

    This deliberately does *not* use the event's month/day to suppress ages.
    That disagreement is exposed separately via birthday_date_mismatch.
    A calendar event predating the person's birth year has no valid age.
    """
    if dob is None or event_day.year < dob.year:
        return None
    return event_day.year - dob.year
