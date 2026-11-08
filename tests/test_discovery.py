"""Exercise collection matching and DAV XML parsing without contacting iCloud."""
import importlib.util
import sys
import types
from pathlib import Path

# Test the pure discovery helpers with the HA session integration stubbed out.
ha = types.ModuleType('homeassistant')
helpers = types.ModuleType('homeassistant.helpers')
client = types.ModuleType('homeassistant.helpers.aiohttp_client')
client.async_get_clientsession = lambda hass: None
sys.modules.setdefault('homeassistant', ha)
sys.modules.setdefault('homeassistant.helpers', helpers)
sys.modules.setdefault('homeassistant.helpers.aiohttp_client', client)

path = Path(__file__).resolve().parents[1] / 'custom_components/birthday_tracker/caldav_discovery.py'
spec = importlib.util.spec_from_file_location('birthday_discovery', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_choose_matching_name():
    collections = [{'url': 'https://p171-caldav.icloud.com/a/', 'name': 'Shared'},
                   {'url': 'https://p171-caldav.icloud.com/b/', 'name': 'Home'}]
    choice, reason = module.choose_calendar(collections, 'calendar.shared')
    assert choice['name'] == 'Shared'
    assert reason == 'matched_calendar_name'
    choice, reason = module.choose_calendar(collections, 'calendar.missing')
    assert choice is None and reason == 'calendar_name_not_matched'


def test_safe_redirect_host():
    base = 'https://caldav.icloud.com/'
    assert module._safe_url('https://p171-caldav.icloud.com/calendar/', base)
    assert not module._safe_url('https://caldav.icloud.com.evil.org/', base)
    assert not module._safe_url('http://p171-caldav.icloud.com/', base)


def test_parse_propfind_responses():
    import xml.etree.ElementTree as ET
    xml = '''<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
    <d:response><d:href>/home/</d:href><d:propstat><d:prop>
    <c:calendar-home-set><d:href>/home/</d:href></c:calendar-home-set>
    </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>
    </d:multistatus>'''
    assert module._homes(ET.fromstring(xml), 'https://caldav.icloud.com/') == ['https://caldav.icloud.com/home/']
