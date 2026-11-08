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
    assert mod.birthday_on_event(date(1994,11,12),date(2026,11,13)) is None

def test_people():
    assert len(mod.normalize_people({'people':[{'full_name':'A'},{'full_name':'B'}]}))==2

def test_filter():
    assert mod.is_birthday_event({'summary':'Laura’s Birthday','start':'2026-11-12'})
    assert not mod.is_birthday_event({'summary':'Dentist','start':'2026-11-12'})
