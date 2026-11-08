import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("birthday_helpers", ROOT / "custom_components" / "birthday_tracker" / "helpers.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class HelpersTests(unittest.TestCase):
    def test_filter(self):
        self.assertTrue(mod.is_birthday_event({"summary":"Laura’s birthday", "start":"2026-11-12"}))
        self.assertTrue(mod.is_birthday_event({"summary":"STEPHEN'S BIRTHDAY", "start":"2026-11-08"}))
        self.assertFalse(mod.is_birthday_event({"summary":"Red Bin", "start":"2026-11-12"}))
        self.assertFalse(mod.is_birthday_event({"summary":"Birthday Party", "start":"2026-11-12T15:00:00+00:00"}))
    def test_uk_date(self):
        self.assertEqual(mod.parse_uk_date("12/11/1994").isoformat(), "1994-11-12")
        self.assertIsNone(mod.parse_uk_date("11/30/1994"))
        self.assertIsNone(mod.parse_uk_date("31/02/2001"))

if __name__ == "__main__": unittest.main()
