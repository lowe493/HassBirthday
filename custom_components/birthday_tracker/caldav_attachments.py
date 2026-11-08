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


# iCloud may reject an unbounded REPORT. Try a bounded range, then a
# limited, read-only PROPFIND + GET fallback. Never log private URLs.
from .caldav_discovery import _safe_url
from datetime import datetime, timezone

MAX_FALLBACK_OBJECTS = 200
PROPFIND_OBJECTS = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/><d:getcontenttype/></d:prop></d:propfind>"""


def _bounded_report():
    today = date.today()
    a = today.strftime('%Y%m%d') + 'T000000Z'
    b = (today + timedelta(days=375)).strftime('%Y%m%d') + 'T000000Z'
    return f"""<?xml version="1.0" encoding="utf-8"?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop><d:getetag/><c:calendar-data/></d:prop>
  <c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT">
  <c:time-range start="{a}" end="{b}"/>
  </c:comp-filter></c:comp-filter></c:filter>
</c:calendar-query>"""


async def _fetch_ics(session, url, collection_url, auth):
    if not _safe_url(url, collection_url):
        return None, 'unsafe_object_url'
    # Reject out-of-collection paths, even on an otherwise trusted host.
    from urllib.parse import unquote
    if (urlparse(url).netloc != urlparse(collection_url).netloc or
            not unquote(urlparse(url).path).startswith(unquote(urlparse(collection_url).path).rstrip('/') + '/')):
        return None, 'object_outside_collection'
    try:
        async with session.get(url, auth=auth, allow_redirects=False, timeout=15) as response:
            if response.status != 200:
                return None, f'object_http_{response.status}'
            body = await response.content.read(MAX_ICS_BYTES + 1)
        if len(body) > MAX_ICS_BYTES:
            return None, 'object_too_large'
        return body.decode('utf-8-sig'), None
    except (ClientError, TimeoutError, UnicodeError, ValueError) as err:
        return None, f'object_request_{type(err).__name__}'


async def _request_calendar_data(session, url, auth):
    # The first attempt preserves historical behaviour, the bounded REPORT
    # avoids iCloud refusing a query of the complete calendar history.
    attempts = [('bounded_report', _bounded_report()), ('unbounded_report', REPORT)]
    errors = []
    for method, body in attempts:
        try:
            async with session.request('REPORT', url, auth=auth, headers={
                    'Depth': '1', 'Content-Type': 'application/xml; charset=utf-8'},
                    data=body.encode(), allow_redirects=False, timeout=30) as response:
                if response.status != 207:
                    errors.append(f'{method}_http_{response.status}')
                    continue
                payload = await response.content.read(MAX_ICS_BYTES + 1)
            if len(payload) > MAX_ICS_BYTES:
                errors.append(f'{method}_too_large')
                continue
            root = ET.fromstring(payload)
            texts = [e.text for e in root.findall('.//c:calendar-data', NS) if e.text]
            return texts, {'caldav_request_method': method, 'caldav_request_fallback': method != 'bounded_report'}
        except (ClientError, TimeoutError, ET.ParseError, ValueError) as err:
            errors.append(f'{method}_{type(err).__name__}')

    # A small CalDAV collection might support collection PROPFIND but no REPORT.
    try:
        async with session.request('PROPFIND', url, auth=auth, allow_redirects=False,
                                   headers={'Depth': '1', 'Content-Type': 'application/xml; charset=utf-8'},
                                   data=PROPFIND_OBJECTS.encode(), timeout=30) as response:
            if response.status != 207:
                errors.append(f'propfind_http_{response.status}')
                return [], {'attachment_status': 'caldav_fetch_failed',
                            'caldav_failure_stage': 'event_retrieval',
                            'caldav_request_errors': errors}
            payload = await response.content.read(MAX_ICS_BYTES + 1)
        if len(payload) > MAX_ICS_BYTES:
            errors.append('propfind_too_large')
            return [], {'attachment_status': 'caldav_fetch_failed', 'caldav_failure_stage': 'event_retrieval',
                        'caldav_request_errors': errors}
        root = ET.fromstring(payload)
        hrefs = []
        for res in root.findall('d:response', NS):
            href = res.findtext('d:href', namespaces=NS)
            if href and urlparse(href).path.lower().endswith('.ics'):
                full = urljoin(url, href)
                if full not in hrefs:
                    hrefs.append(full)
        if len(hrefs) > MAX_FALLBACK_OBJECTS:
            return [], {'attachment_status': 'caldav_fallback_limit_exceeded',
                        'caldav_failure_stage': 'event_retrieval',
                        'caldav_fallback_objects_found': len(hrefs),
                        'caldav_request_errors': errors}
        texts, object_errors = [], []
        for href in hrefs:
            data, error = await _fetch_ics(session, href, url, auth)
            if data:
                texts.append(data)
            elif error:
                object_errors.append(error)
        if object_errors and not texts:
            return [], {'attachment_status': 'caldav_fetch_failed', 'caldav_failure_stage': 'object_get',
                        'caldav_request_errors': errors + list(dict.fromkeys(object_errors))}
        return texts, {'caldav_request_method': 'propfind_get', 'caldav_request_fallback': True,
                       'caldav_fallback_objects_found': len(hrefs),
                       'caldav_fallback_objects_loaded': len(texts),
                       'caldav_fallback_object_errors': len(object_errors),
                       'caldav_previous_request_errors': errors}
    except (ClientError, TimeoutError, ET.ParseError, ValueError) as err:
        errors.append(f'propfind_{type(err).__name__}')
        return [], {'attachment_status': 'caldav_fetch_failed',
                    'caldav_failure_stage': 'event_retrieval',
                    'caldav_request_errors': errors}


async def load_calendars_attachments(hass, url, username, password, keyword):
    """Return title-to-metadata mapping and safe, structured diagnostics."""
    if not valid_url(url):
        return {}, {'attachment_status': 'invalid_calendar_url'}
    session = async_get_clientsession(hass)
    auth = BasicAuth(username, password)
    ics_texts, request_stats = await _request_calendar_data(session, url, auth)
    if 'attachment_status' in request_stats:
        return {}, request_stats
    by_title = {}
    stats = {**request_stats, 'attachment_status': 'caldav_connected', 'caldav_events_found': 0,
             'caldav_events_with_attach': 0, 'caldav_json_found': 0,
             'caldav_json_loaded': 0, 'caldav_ambiguous_titles': 0,
             'caldav_ics_parse_errors': 0}
    origin = urlparse(url).hostname
    for ical_text in ics_texts:
        try:
            parsed = _birthday_ics(ical_text, keyword)
        except (ValueError, TypeError, ImportError, KeyError):
            stats['caldav_ics_parse_errors'] += 1
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
        # Distinct UIDs with the same title are ambiguous; don't apply the
        # wrong person's information to an event.
        uids = {i['uid'] for i in items}
        if len(uids) != 1:
            stats['caldav_ambiguous_titles'] += 1
            result[key] = {'metadata': None, 'status': 'ambiguous_event_title'}
        else:
            # Multiple VEVENT components with same UID may represent exceptions.
            result[key] = next((i for i in items if i['status'] == 'loaded'), items[0])
    if stats['caldav_events_found'] and not stats['caldav_json_found']:
        stats['attachment_status'] = 'no_named_json_attachments_exposed'
    return result, stats
