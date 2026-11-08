"""Birthday event list with local metadata fallback and honest diagnostics."""
from __future__ import annotations

from datetime import date, timedelta
import json
import logging
from pathlib import Path

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_CALENDAR, CONF_KEYWORD, DEFAULT_KEYWORD
from .helpers import is_birthday_event, parse_uk_date, safe_filename

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    calendar = entry.data[CONF_CALENDAR]
    keyword = (entry.options.get(CONF_KEYWORD) or entry.data.get(CONF_KEYWORD)
               or DEFAULT_KEYWORD).strip()

    async def fetch():
        today = dt_util.now().date()
        start = dt_util.start_of_local_day()
        end = start + timedelta(days=370)
        response = await hass.services.async_call(
            "calendar", "get_events",
            {"entity_id": calendar, "start_date_time": start.isoformat(),
             "end_date_time": end.isoformat()},
            blocking=True, return_response=True,
        )
        events = (response or {}).get(calendar, {}).get("events") or []
        directory = Path(hass.config.path("birthday_tracker", "events"))
        output = []
        seen = set()
        counts = {"calendar_events_scanned": len(events), "non_birthdays_skipped": 0,
                  "timed_events_skipped": 0, "duplicates_skipped": 0,
                  "metadata_loaded": 0, "metadata_missing": 0,
                  "metadata_empty": 0, "metadata_invalid": 0}
        for event in events:
            title = str(event.get("summary") or "")
            start_value = event.get("start")
            if not isinstance(start_value, str) or len(start_value) != 10:
                counts["timed_events_skipped"] += 1
                continue
            if not is_birthday_event(event, keyword):
                counts["non_birthdays_skipped"] += 1
                continue
            try:
                event_day = date.fromisoformat(start_value)
            except ValueError:
                continue
            if event_day < today:
                continue
            # HA's calendar.get_events doesn't include UID; this fallback is based on
            # the title, so events with identical titles share local metadata.
            uid = str(event.get("uid") or title)
            key = (uid, event_day.isoformat())
            if key in seen:
                counts["duplicates_skipped"] += 1
                continue
            seen.add(key)
            file_path = directory / safe_filename(uid)
            meta = {}
            metadata_state = "missing"
            if await hass.async_add_executor_job(file_path.is_file):
                try:
                    raw = await hass.async_add_executor_job(file_path.read_text, "utf-8")
                    if not raw.strip():
                        metadata_state = "empty"
                    else:
                        parsed = json.loads(raw)
                        if isinstance(parsed, dict):
                            meta = parsed
                            metadata_state = "loaded"
                        else:
                            metadata_state = "invalid"
                except (OSError, UnicodeError, json.JSONDecodeError):
                    metadata_state = "invalid"
            counts[f"metadata_{metadata_state}"] += 1
            dob = parse_uk_date(meta.get("date_of_birth"))
            age = event_day.year - dob.year if dob and (dob.month, dob.day) == (event_day.month, event_day.day) else None
            # Age still valid if the calendar birthday day is offset for leap days
            if dob and dob.month == 2 and dob.day == 29 and event_day.month == 2 and event_day.day == 28:
                age = event_day.year - dob.year
            output.append({
                "name": meta.get("full_name") or title,
                "event_title": title,
                "date": event_day.isoformat(),
                "days_until": (event_day - today).days,
                "turning_age": age,
                "date_of_birth": meta.get("date_of_birth") if dob else None,
                "address": meta.get("address") if isinstance(meta.get("address"), dict) else {},
                "relationship": meta.get("relationship", ""),
                "notes": meta.get("notes", ""),
                "gift_ideas": meta.get("gift_ideas") if isinstance(meta.get("gift_ideas"), list) else [],
                "interests": meta.get("interests") if isinstance(meta.get("interests"), list) else [],
                "metadata_status": metadata_state,
                "metadata_filename": file_path.name,
                "uid": uid,
            })
        output.sort(key=lambda item: (item["date"], item["name"]))
        return {"birthdays": output, "diagnostics": counts}

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name=f"Birthday Tracker ({calendar})",
        update_method=fetch, update_interval=timedelta(minutes=30),
    )
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([BirthdayTrackerSensor(coordinator, entry, calendar, keyword)])


class BirthdayTrackerSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:cake-variant"
    _attr_has_entity_name = True
    _attr_name = "Upcoming birthdays"

    def __init__(self, coordinator, entry, calendar, keyword):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_upcoming"
        self._calendar = calendar
        self._keyword = keyword
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Birthday Tracker ({calendar})",
            "manufacturer": "Local custom integration",
        }

    @property
    def native_value(self):
        return len(self.coordinator.data.get("birthdays", []))

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        birthdays = data.get("birthdays", [])
        return {
            "birthdays": birthdays,
            "next_birthday": birthdays[0]["date"] if birthdays else None,
            "title_keyword": self._keyword,
            "calendar_entity": self._calendar,
            "attachment_status": "not_available_through_calendar_get_events",
            "attachment_note": ("Apple Calendar attachments are not included in "
                                "Home Assistant calendar.get_events results. "
                                "This release does not download them."),
            **data.get("diagnostics", {}),
        }
