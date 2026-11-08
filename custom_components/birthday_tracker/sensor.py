"""Read calendar events and optional locally supplied JSON metadata."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import logging
from pathlib import Path

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.util import dt as dt_util
from .const import DOMAIN, CONF_CALENDAR

_LOGGER = logging.getLogger(__name__)


def parse_uk_date(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        return None


def next_birthday(dob: date, today: date):
    """For 29 February birthdays, use 28 February in non-leap years."""
    def anniversary(year):
        try:
            return date(year, dob.month, dob.day)
        except ValueError:
            return date(year, 2, 28)
    value = anniversary(today.year)
    if value < today:
        value = anniversary(today.year + 1)
    return value


def safe_filename(uid: str) -> str:
    """A stable, filesystem-safe key for metadata; no path traversal."""
    import hashlib
    return hashlib.sha256(uid.encode("utf-8")).hexdigest()[:24] + ".json"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    calendar = entry.data[CONF_CALENDAR]

    async def fetch():
        today = dt_util.now().date()
        start = dt_util.start_of_local_day()
        end = start + timedelta(days=370)
        response = await hass.services.async_call(
            "calendar", "get_events",
            {"entity_id": calendar,
             "start_date_time": start.isoformat(),
             "end_date_time": end.isoformat()},
            blocking=True, return_response=True,
        )
        events = (response or {}).get(calendar, {}).get("events", [])
        directory = Path(hass.config.path("birthday_tracker", "events"))
        output = []
        seen = set()
        for event in events:
            title = event.get("summary") or "Birthday"
            begin = str(event.get("start", ""))[:10]
            try:
                event_day = date.fromisoformat(begin)
            except ValueError:
                continue
            # An occurrence is unique by UID + day; when UID is unavailable,
            # use the event title + occurrence day.
            uid = str(event.get("uid") or title)
            key = (uid, event_day.isoformat())
            if key in seen:
                continue
            seen.add(key)
            file_path = directory / safe_filename(uid)
            meta = {}
            metadata_state = "missing"
            if file_path.is_file():
                try:
                    raw = await hass.async_add_executor_job(file_path.read_text, "utf-8")
                    if not raw.strip():
                        metadata_state = "empty"
                    else:
                        value = json.loads(raw)
                        if isinstance(value, dict):
                            meta = value
                            metadata_state = "loaded"
                        else:
                            metadata_state = "invalid"
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    metadata_state = "invalid"
            dob = parse_uk_date(meta.get("date_of_birth"))
            # Calendar occurrence is authoritative for the upcoming date.
            # Compute turning age only with a validated date of birth.
            age = event_day.year - dob.year if dob else None
            remaining = (event_day - today).days
            if remaining < 0:
                continue
            output.append({
                "name": meta.get("full_name") or title,
                "event_title": title,
                "date": event_day.isoformat(),
                "days_until": remaining,
                "turning_age": age,
                "date_of_birth": meta.get("date_of_birth") if dob else None,
                "address": meta.get("address") if isinstance(meta.get("address"), dict) else {},
                "relationship": meta.get("relationship", ""),
                "notes": meta.get("notes", ""),
                "gift_ideas": meta.get("gift_ideas", []),
                "interests": meta.get("interests", []),
                "metadata_status": metadata_state,
                "metadata_filename": file_path.name,
                "uid": uid,
            })
        output.sort(key=lambda item: (item["date"], item["name"]))
        return output

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name=f"Birthday Tracker ({calendar})",
        update_method=fetch, update_interval=timedelta(minutes=30),
    )
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([BirthdayTrackerSensor(coordinator, entry, calendar)])


class BirthdayTrackerSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:cake-variant"
    _attr_has_entity_name = True
    _attr_name = "Upcoming birthdays"

    def __init__(self, coordinator, entry, calendar):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_upcoming"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Birthday Tracker ({calendar})",
            "manufacturer": "Local custom integration",
        }

    @property
    def native_value(self):
        return len(self.coordinator.data or [])

    @property
    def extra_state_attributes(self):
        birthdays = self.coordinator.data or []
        return {"birthdays": birthdays, "next_birthday": birthdays[0]["date"] if birthdays else None}
