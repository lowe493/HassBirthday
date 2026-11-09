import importlib.util
from pathlib import Path
from datetime import date

path=Path(__file__).resolve().parents[1]/'custom_components/birthday_tracker/helpers.py'
spec=importlib.util.spec_from_file_location('birthday_helpers',path)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def test_dates():
    assert mod.parse_uk_date('12/11/1994') == date(1994,11,12)
    assert mod.parse_uk_date('31/02/1994') is None

def test_age():
    assert mod.birthday_on_event(date(1994,11,12),date(2026,11,12))==32
    assert mod.birthday_on_event(date(1994,11,12),date(2026,11,13)) == 32

def test_people():
    assert len(mod.normalize_people({'people':[{'full_name':'A'},{'full_name':'B'}]}))==2

def test_filter():
    assert mod.is_birthday_event({'summary':'Laura’s Birthday','start':'2026-11-12'})
    assert not mod.is_birthday_event({'summary':'Dentist','start':'2026-11-12'})


def test_mismatched_date_still_gives_age():
    dob = date(1996, 11, 9)
    event = date(2026, 11, 12)
    assert mod.birthday_on_event(dob, event) == 30
    assert mod.birthday_date_mismatch(dob, event) is True


def test_matching_date_is_not_flagged():
    dob = date(1993, 11, 8)
    event = date(2026, 11, 8)
    assert mod.birthday_on_event(dob, event) == 33
    assert mod.birthday_date_mismatch(dob, event) is False


def test_invalid_or_future_birth_year():
    assert mod.birthday_on_event(None, date(2026, 11, 12)) is None
    assert mod.birthday_on_event(date(2030, 1, 1), date(2026, 11, 12)) is None
    assert mod.birthday_date_mismatch(None, date(2026, 11, 12)) is False


def test_leap_day_convention():
    assert mod.birthday_on_event(date(2000, 2, 29), date(2027, 2, 28)) == 27
    assert mod.birthday_date_mismatch(date(2000, 2, 29), date(2027, 2, 28)) is False
    assert mod.birthday_date_mismatch(date(2000, 2, 29), date(2028, 2, 28)) is True
