"""Direct, read-only CalDAV lookup for event ATTACH properties.

The Home Assistant calendar API excludes attachments. CalDAV servers may expose
ATTACH properties as a URL or inline base64. iCloud can omit managed attachments
from CalDAV responses; status makes this explicit. This module never writes events.
"""
from __future__ import annotations
import base64
import json
from datetime import date, timedelta
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET

from aiohttp import BasicAuth, ClientError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

MAX_JSON_BYTES = 64 * 1024
MAX_ICS_BYTES = 4 * 1024 * 1024
NS = {'d': 'DAV:', 'c': 'urn:ietf:params:xml:ns:caldav'}
REPORT = """<?xml version="1.0" encoding="utf-8"?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop><d:getetag/><c:calendar-data/></d:prop>
  <c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT"/></c:comp-filter></c:filter>
</c:calendar-query>"""


def valid_url(url):
    parsed = urlparse(url)
    return (parsed.scheme == 'https' and bool(parsed.hostname)
            and not parsed.username and not parsed.password and not parsed.fragment)


def _filename(prop):
    params = getattr(prop, 'params', {})
    name = str(params.get('FILENAME') or params.get('X-FILENAME') or '')
    if name:
        return name.rsplit('/', 1)[-1].lower()
    value = str(prop)
    return urlparse(value).path.rsplit('/', 1)[-1].lower()


def _extract_attachment_props(component):
    raw = component.get('ATTACH')
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def _birthday_ics(ical_text, keyword):
    from icalendar import Calendar
    cal = Calendar.from_ical(ical_text)
    items = []
    for event in cal.walk('VEVENT'):
        name = str(event.get('SUMMARY', '')).strip()
        if keyword.casefold() not in name.casefold():
            continue
        starts = event.get('DTSTART')
        if not starts or not isinstance(starts.dt, date):
            continue
        if hasattr(starts.dt, 'hour'):  # ignore timed appointments
            continue
        items.append({'summary': name, 'attachments': _extract_attachment_props(event),
                      'uid': str(event.get('UID', ''))})
    return items


async def _get_json(session, url, auth, calendar_origin):
    if not valid_url(url):
        return None, 'unsafe_attachment_url'
    # Never send credentials to a different host, even on an HTTPS redirect.
    if urlparse(url).hostname != calendar_origin:
        return None, 'external_attachment_url'
    try:
        async with session.get(url, auth=auth, allow_redirects=False, timeout=20) as response:
            if response.status in (301, 302, 303, 307, 308):
                return None, 'attachment_redirect_unsupported'
            if response.status != 200:
                return None, f'attachment_http_{response.status}'
            content = await response.content.read(MAX_JSON_BYTES + 1)
    except (ClientError, TimeoutError):
        return None, 'attachment_network_error'
    if len(content) > MAX_JSON_BYTES:
        return None, 'attachment_too_large'
    return _decode_json(content)


def _decode_json(content):
    try:
        if not content.strip():
            return None, 'empty'
        parsed = json.loads(content.decode('utf-8-sig'))
        if not isinstance(parsed, (dict, list)):
            return None, 'invalid'
        return parsed, 'loaded'
    except (UnicodeError, ValueError):
        return None, 'invalid'


async def _read_attach(session, prop, auth, calendar_origin):
    """Read JSON only when filename explicitly equals birthday.json."""
    if _filename(prop) != 'birthday.json':
        return None, 'not_birthday_json'
    params = getattr(prop, 'params', {})
    if str(params.get('ENCODING', '')).upper() == 'BASE64' or str(params.get('VALUE', '')).upper() == 'BINARY':
        try:
            encoded = str(prop)
            if len(encoded) > MAX_JSON_BYTES * 2:
                return None, 'attachment_too_large'
            return _decode_json(base64.b64decode(encoded, validate=True))
        except (ValueError, base64.binascii.Error):
            return None, 'invalid'
    return await _get_json(session, str(prop), auth, calendar_origin)


async def load_calendars_attachments(hass, url, username, password, keyword):
    """Return title-to-metadata mapping and diagnostics.

    Deliberately refuses ambiguous titles: HA get_events does not supply UID,
    so titles are the only safe matching key for an event occurrence.
    """
    if not valid_url(url):
        return {}, {'attachment_status': 'invalid_calendar_url'}
    session = async_get_clientsession(hass)
    auth = BasicAuth(username, password)
    try:
        async with session.request('REPORT', url, auth=auth, headers={
                'Depth': '1', 'Content-Type': 'application/xml; charset=utf-8'},
                data=REPORT.encode(), allow_redirects=False, timeout=35) as response:
            if response.status != 207:
                return {}, {'attachment_status': f'caldav_http_{response.status}'}
            body = await response.content.read(MAX_ICS_BYTES + 1)
        if len(body) > MAX_ICS_BYTES:
            return {}, {'attachment_status': 'caldav_response_too_large'}
        root = ET.fromstring(body)
    except (ClientError, TimeoutError, ET.ParseError):
        return {}, {'attachment_status': 'caldav_request_failed'}

    by_title = {}
    stats = {'attachment_status': 'caldav_connected', 'caldav_events_found': 0,
             'caldav_events_with_attach': 0, 'caldav_json_found': 0,
             'caldav_json_loaded': 0, 'caldav_ambiguous_titles': 0}
    origin = urlparse(url).hostname
    for calendar_data in root.findall('.//c:calendar-data', NS):
        if not calendar_data.text:
            continue
        try:
            parsed = _birthday_ics(calendar_data.text, keyword)
        except (ValueError, TypeError, ImportError):
            continue
        for event in parsed:
            stats['caldav_events_found'] += 1
            attachments = event['attachments']
            if attachments:
                stats['caldav_events_with_attach'] += 1
            key = event['summary'].casefold().strip()
            item = {'uid': event['uid'], 'metadata': None, 'status': 'no_birthday_json_attach'}
            for prop in attachments:
                if _filename(prop) == 'birthday.json':
                    stats['caldav_json_found'] += 1
                    item['metadata'], item['status'] = await _read_attach(session, prop, auth, origin)
                    if item['status'] == 'loaded':
                        stats['caldav_json_loaded'] += 1
                    break
            by_title.setdefault(key, []).append(item)
    result = {}
    for key, items in by_title.items():
        # Repeated iCalendar VEVENTs with same title+UID may represent exceptions.
        uids = {i['uid'] for i in items}
        if len(uids) != 1 or len(items) > 1:
            stats['caldav_ambiguous_titles'] += 1
            result[key] = {'metadata': None, 'status': 'ambiguous_event_title'}
        else:
            result[key] = items[0]
    if stats['caldav_events_found'] and not stats['caldav_json_found']:
        stats['attachment_status'] = 'no_named_json_attachments_exposed'
    return result, stats
