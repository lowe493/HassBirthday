"""Regression checks for the safer CalDAV retrieval fallback."""
import importlib.util
import sys
import types
from pathlib import Path

ha = types.ModuleType('homeassistant')
helpers = types.ModuleType('homeassistant.helpers')
client = types.ModuleType('homeassistant.helpers.aiohttp_client')
client.async_get_clientsession = lambda hass: None
sys.modules.setdefault('homeassistant', ha)
sys.modules.setdefault('homeassistant.helpers', helpers)
sys.modules.setdefault('homeassistant.helpers.aiohttp_client', client)
root = Path(__file__).resolve().parents[1] / 'custom_components/birthday_tracker'
# Module uses a relative import to discovery; package-like testing namespace.
pkg = types.ModuleType('bt_tests')
pkg.__path__ = [str(root)]
sys.modules.setdefault('bt_tests', pkg)
for name in ['caldav_discovery', 'caldav_attachments']:
    spec = importlib.util.spec_from_file_location('bt_tests.' + name, root / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
att = sys.modules['bt_tests.caldav_attachments']


def test_bounded_report_has_time_range():
    report = att._bounded_report()
    assert 'time-range start=' in report
    assert 'VEVENT' in report


def test_object_urls_stay_in_collection():
    from bt_tests.caldav_discovery import _safe_url
    url = 'https://p171-caldav.icloud.com/a/calendars/abc/'
    assert _safe_url(url + 'event.ics', url)
    assert not _safe_url('http://p171-caldav.icloud.com/a/other.ics', url)


def test_birthday_ics_parsing():
    text = ('BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:abc\n'
            'DTSTART;VALUE=DATE:20261112\nSUMMARY:Laura birthday\n'
            'END:VEVENT\nEND:VCALENDAR\n')
    import pytest
    pytest.importorskip("icalendar")
    assert att._birthday_ics(text, 'birthday')[0]['summary'] == 'Laura birthday'
