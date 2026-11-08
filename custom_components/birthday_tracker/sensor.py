"""Birthday event sensor with optional direct CalDAV attachment retrieval."""
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
from .const import (DOMAIN, CONF_CALENDAR, CONF_KEYWORD, DEFAULT_KEYWORD,
                    CONF_CALDAV_URL, CONF_CALDAV_USER, CONF_CALDAV_PASSWORD)
from .helpers import (is_birthday_event, parse_uk_date, safe_filename,
                      normalize_people, birthday_on_event)
from .caldav_attachments import load_calendars_attachments
from .caldav_discovery import discover_calendar

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
            "calendar", "get_events", {
                "entity_id": calendar, "start_date_time": start.isoformat(),
                "end_date_time": end.isoformat()}, blocking=True, return_response=True)
        events = (response or {}).get(calendar, {}).get("events") or []
        directory = Path(hass.config.path("birthday_tracker", "events"))
        output, seen = [], set()
        counts = {"calendar_events_scanned": len(events), "non_birthdays_skipped": 0,
                  "timed_events_skipped": 0, "duplicates_skipped": 0,
                  "recurring_occurrences_skipped": 0,
                  "metadata_loaded": 0, "metadata_missing": 0,
                  "metadata_empty": 0, "metadata_invalid": 0}
        cal_url = entry.options.get(CONF_CALDAV_URL, "").strip()
        cal_user = entry.options.get(CONF_CALDAV_USER, "").strip()
        cal_pass = entry.options.get(CONF_CALDAV_PASSWORD, "")
        lookup, attachment_stats = {}, {"attachment_status": "not_configured"}
        if cal_url and cal_user and cal_pass:
            # A normal iCloud URL is a discovery endpoint, not a collection.
            # Resolve the selected calendar without guessing private URLs.
            state = hass.states.get(calendar)
            friendly_name = (state.attributes.get('friendly_name', '') if state else '')
            collection_url, discovery_stats = await discover_calendar(
                hass, cal_url, cal_user, cal_pass, calendar, friendly_name)
            if collection_url:
                lookup, attachment_stats = await load_calendars_attachments(
                    hass, collection_url, cal_user, cal_pass, keyword)
                attachment_stats = {**discovery_stats, **attachment_stats}
            else:
                attachment_stats = discovery_stats
        for event in events:
            title = str(event.get("summary") or "")
            value = event.get("start")
            if not isinstance(value, str) or len(value) != 10:
                counts["timed_events_skipped"] += 1
                continue
            if not is_birthday_event(event, keyword):
                counts["non_birthdays_skipped"] += 1
                continue
            try:
                day = date.fromisoformat(value)
            except ValueError:
                continue
            if day < today:
                continue
            # Keep one upcoming occurrence per title, not the next year's repeat.
            # Where different people share a title, CalDAV attachment matching is
            # deliberately marked ambiguous and local metadata is a fallback.
            uid = str(event.get("uid") or title)
            key = title.casefold().strip()
            if key in seen:
                counts["recurring_occurrences_skipped"] += 1
                continue
            seen.add(key)
            filename = safe_filename(uid)
            file_path = directory / filename
            raw = {}
            state = "missing"
            source = "none"
            attachment_match = lookup.get(key)
            if attachment_match:
                state = attachment_match['status']
                if state == 'loaded':
                    raw = attachment_match['metadata']
                    source = 'caldav'
            if source == 'none' and await hass.async_add_executor_job(file_path.is_file):
                try:
                    text = await hass.async_add_executor_job(file_path.read_text, 'utf-8')
                    if not text.strip():
                        state = 'empty'
                    else:
                        raw = json.loads(text)
                        if isinstance(raw, (dict, list)):
                            state, source = 'loaded', 'local'
                        else:
                            state = 'invalid'
                except (OSError, UnicodeError, json.JSONDecodeError):
                    state = 'invalid'
            if state not in ('loaded', 'empty', 'invalid'):
                counts['metadata_missing'] += 1
            else:
                counts[f'metadata_{state}'] += 1
            persons = normalize_people(raw) if state == 'loaded' else [{}]
            if not persons:
                persons = [{}]
            for person in persons:
                dob = parse_uk_date(person.get('date_of_birth'))
                output.append({
                    'name': person.get('full_name') or title,
                    'event_title': title,
                    'date': day.isoformat(), 'days_until': (day - today).days,
                    'turning_age': birthday_on_event(dob, day),
                    'date_of_birth': person.get('date_of_birth') if dob else None,
                    'address': person.get('address') if isinstance(person.get('address'), dict) else {},
                    'relationship': person.get('relationship', ''),
                    'notes': person.get('notes', ''),
                    'gift_ideas': person.get('gift_ideas') if isinstance(person.get('gift_ideas'), list) else [],
                    'interests': person.get('interests') if isinstance(person.get('interests'), list) else [],
                    'metadata_status': state, 'metadata_source': source,
                    'metadata_filename': filename, 'uid': uid,
                })
        output.sort(key=lambda x: (x['date'], x['name']))
        return {'birthdays': output, 'diagnostics': {**counts, **attachment_stats}}

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name=f'Birthday Tracker ({calendar})',
        update_method=fetch, update_interval=timedelta(minutes=30))
    await coordinator.async_refresh()
    async_add_entities([BirthdayTrackerSensor(coordinator, entry, calendar, keyword)])


class BirthdayTrackerSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = 'mdi:cake-variant'
    _attr_has_entity_name = True
    _attr_name = 'Upcoming birthdays'

    def __init__(self, coordinator, entry, calendar, keyword):
        super().__init__(coordinator)
        self._attr_unique_id = f'{entry.entry_id}_upcoming'
        self._calendar = calendar
        self._keyword = keyword
        self._attr_device_info = {
            'identifiers': {(DOMAIN, entry.entry_id)},
            'name': f'Birthday Tracker ({calendar})',
            'manufacturer': 'Local custom integration',
        }

    @property
    def native_value(self):
        return len(self.coordinator.data.get('birthdays', [])) if self.coordinator.data else None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        birthdays = data.get('birthdays', [])
        return {
            'birthdays': birthdays,
            'next_birthday': birthdays[0]['date'] if birthdays else None,
            'title_keyword': self._keyword,
            'calendar_entity': self._calendar,
            'attachment_note': ('Direct CalDAV is optional and read-only. '
                                'Apple may omit ATTACH data even when an attachment is visible in Calendar.'),
            **data.get('diagnostics', {}),
        }
