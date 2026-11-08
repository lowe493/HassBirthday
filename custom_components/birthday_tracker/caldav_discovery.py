"""Read-only WebDAV/CalDAV discovery, starting from an account endpoint.

Do not infer private collection paths from publicly shared webcal links.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

from aiohttp import BasicAuth, ClientError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

NS = {'d': 'DAV:', 'c': 'urn:ietf:params:xml:ns:caldav'}
PROPFIND_PRINCIPAL = '''<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop><d:current-user-principal/><d:principal-URL/><c:calendar-home-set/></d:prop></d:propfind>'''
PROPFIND_HOME = '''<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop><c:calendar-home-set/></d:prop></d:propfind>'''
PROPFIND_CALENDARS = '''<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop><d:displayname/><d:resourcetype/></d:prop></d:propfind>'''
MAX_XML_BYTES = 1024 * 1024


def _safe_url(url, seed):
    """Never forward password to a foreign host, non-HTTPS or userinfo URL."""
    p, original = urlparse(url), urlparse(seed)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.fragment:
        return False
    if original.hostname == 'caldav.icloud.com' or (original.hostname or '').endswith(('-caldav.icloud.com', '.caldav.icloud.com')):
        return p.hostname == 'caldav.icloud.com' or p.hostname.endswith(('-caldav.icloud.com', '.caldav.icloud.com'))
    return p.hostname == original.hostname and p.port == original.port


def _href(root, path, current):
    el = root.find(path, NS)
    if el is None or not el.text:
        return None
    return urljoin(current, el.text.strip())


async def _propfind(session, url, seed, auth, body, depth='0'):
    """Manually follow a few safe iCloud redirects, without sending auth elsewhere."""
    for _ in range(4):
        if not _safe_url(url, seed):
            return None, url, 'discovery_unsafe_redirect'
        try:
            async with session.request('PROPFIND', url, data=body.encode('utf-8'),
                                       auth=auth, allow_redirects=False,
                                       headers={'Depth': depth, 'Content-Type': 'application/xml; charset=utf-8'},
                                       timeout=25) as response:
                if response.status in (301, 302, 307, 308):
                    target = response.headers.get('Location')
                    if not target:
                        return None, url, 'discovery_redirect_without_location'
                    url = urljoin(url, target)
                    continue
                if response.status != 207:
                    return None, url, f'discovery_http_{response.status}'
                payload = await response.content.read(MAX_XML_BYTES + 1)
            if len(payload) > MAX_XML_BYTES:
                return None, url, 'discovery_response_too_large'
            return ET.fromstring(payload), url, None
        except (ClientError, TimeoutError, ET.ParseError, ValueError):
            return None, url, 'discovery_request_failed'
    return None, url, 'discovery_too_many_redirects'


def _prop_element(response, tag):
    for propstat in response.findall('d:propstat', NS):
        status = propstat.findtext('d:status', default='', namespaces=NS)
        if ' 200 ' in status or status.endswith(' 200 OK'):
            el = propstat.find('d:prop/' + tag, NS)
            if el is not None:
                return el
    return None


def _prop_href(root, tag, base):
    for response in root.findall('d:response', NS):
        element = _prop_element(response, tag)
        if element is not None:
            href = element.findtext('d:href', namespaces=NS)
            if href:
                return urljoin(base, href.strip())
    return None


def _homes(root, base):
    result = []
    for response in root.findall('d:response', NS):
        element = _prop_element(response, 'c:calendar-home-set')
        if element is not None:
            result.extend(urljoin(base, h.text.strip()) for h in element.findall('d:href', NS) if h.text)
    return list(dict.fromkeys(result))


def _collections(root, base):
    result = []
    for response in root.findall('d:response', NS):
        typ = _prop_element(response, 'd:resourcetype')
        if typ is None or typ.find('c:calendar', NS) is None:
            continue
        href = response.findtext('d:href', namespaces=NS)
        if not href:
            continue
        name = _prop_element(response, 'd:displayname')
        result.append({'url': urljoin(base, href.strip()),
                       'name': (name.text or '').strip() if name is not None else ''})
    return result


def _norm(value):
    return ''.join(ch for ch in value.casefold() if ch.isalnum())


def choose_calendar(calendars, entity_id, friendly_name=''):
    """Do not silently scan a different calendar when names are ambiguous."""
    names = [_norm(entity_id.partition('.')[2]), _norm(friendly_name)]
    matches = [c for c in calendars if _norm(c['name']) in names and _norm(c['name'])]
    if len(matches) == 1:
        return matches[0], 'matched_calendar_name'
    if len(calendars) == 1:
        return calendars[0], 'only_calendar_available'
    if not matches:
        return None, 'calendar_name_not_matched'
    return None, 'ambiguous_calendar_name'


async def discover_calendar(hass, base_url, username, password, entity_id, friendly_name=''):
    """Return a collection URL if unambiguously resolved, plus safe diagnostics."""
    session, auth = async_get_clientsession(hass), BasicAuth(username, password)
    root, final_url, error = await _propfind(session, base_url, base_url, auth, PROPFIND_PRINCIPAL)
    if error:
        return None, {'attachment_status': error}
    homes = _homes(root, final_url)
    if not homes:
        principal = (_prop_href(root, 'd:current-user-principal', final_url)
                     or _prop_href(root, 'd:principal-URL', final_url))
        if not principal:
            return None, {'attachment_status': 'discovery_principal_not_found'}
        principal_root, principal_url, error = await _propfind(
            session, principal, base_url, auth, PROPFIND_HOME)
        if error:
            return None, {'attachment_status': error}
        homes = _homes(principal_root, principal_url)
    if not homes:
        return None, {'attachment_status': 'discovery_calendar_home_not_found'}
    calendars = []
    for home in homes[:5]:
        result, resolved, error = await _propfind(session, home, base_url, auth,
                                                  PROPFIND_CALENDARS, depth='1')
        if error:
            return None, {'attachment_status': error}
        calendars.extend(c for c in _collections(result, resolved)
                         if _safe_url(c['url'], base_url))
    selected, reason = choose_calendar(calendars, entity_id, friendly_name)
    diagnostics = {'discovered_calendars_count': len(calendars),
                   'discovered_calendar_names': [c['name'] for c in calendars[:20]],
                   'calendar_match_status': reason}
    if not selected:
        return None, {'attachment_status': reason, **diagnostics}
    return selected['url'], {'attachment_status': 'calendar_discovered',
                             'discovered_calendar_name': selected['name'], **diagnostics}
