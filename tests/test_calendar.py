import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("generate_calendar", ROOT / "scripts" / "generate_calendar.py")
generator = importlib.util.module_from_spec(spec)
assert spec.loader
sys.modules[spec.name] = generator
spec.loader.exec_module(generator)


class CalendarGeneratorTests(unittest.TestCase):
    def test_text_escaping(self):
        self.assertEqual(
            generator.escape_text("a, b; c\\d\nnext"),
            "a\\, b\\; c\\\\d\\nnext",
        )

    def test_folding_is_byte_safe_and_within_limit(self):
        lines = generator.fold_line("DESCRIPTION:" + "Big Bear 🌲 " * 20)
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(len(line.encode("utf-8")) <= 75 for line in lines))
        self.assertTrue(all(line.startswith(" ") for line in lines[1:]))
        self.assertEqual(lines[0] + "".join(line[1:] for line in lines[1:]), "DESCRIPTION:" + "Big Bear 🌲 " * 20)

    def test_all_day_end_is_exclusive(self):
        data = {
            "id": "test",
            "title": "Test",
            "summary": "Test",
            "all_day": True,
            "start_date": "2026-08-14",
            "end_date": "2026-08-16",
            "sources": [{"label": "Official", "url": "https://example.com"}],
            "last_verified": "2026-08-09",
        }
        lines = generator.event_lines(
            data,
            {"timezone": "America/Los_Angeles"},
            {"test": data},
        )
        self.assertIn("DTSTART;VALUE=DATE:20260814", lines)
        self.assertIn("DTEND;VALUE=DATE:20260817", lines)

    def test_irregular_series_expands_to_stable_events(self):
        source = {
            "id": "series",
            "start_time": "16:30",
            "end_time": "19:30",
            "occurrences": [
                {"date": "2026-09-04"},
                {"date": "2026-09-06", "status": "details_tbd"},
            ],
        }
        events = generator.expand_occurrences([source])
        self.assertEqual([event["id"] for event in events], ["series-2026-09-04", "series-2026-09-06"])
        self.assertEqual(events[0]["start"], "2026-09-04T16:30")
        self.assertEqual(events[1]["status"], "details_tbd")

    def test_conflict_note_is_rendered(self):
        event = {
            "title": "Test",
            "summary": "Summary",
            "start": "2026-09-01T10:00",
            "conflicts": [{"note": "Same-day traffic may be heavy."}],
            "sources": [{"label": "Official", "url": "https://example.com"}],
            "status": "confirmed",
            "last_verified": "2026-08-09",
        }
        description = generator.build_description(event, {})
        self.assertIn("Same-day traffic may be heavy.", description)

    def test_source_semantics_reject_invalid_values(self):
        base_event = {
            "id": "test",
            "title": "Test",
            "status": "confirmed",
            "summary": "Summary",
            "start": "2026-09-01T10:00",
            "end": "2026-09-01T11:00",
            "location": {"name": "Test venue"},
            "sources": [{"label": "Official", "url": "https://example.com"}],
            "categories": ["Community"],
            "last_verified": "2026-08-09",
            "last_modified": "2026-08-09",
            "sequence": 0,
        }
        calendar = {
            "name": "Test",
            "description": "Test feed",
            "timezone": "America/Los_Angeles",
            "product_id": "-//Test//EN",
            "refresh_interval": "PT1H",
            "last_updated": "2026-08-09",
        }
        mutations = [
            ("status", "unknown"),
            ("end", "2026-09-01T09:00"),
            ("start", "2026-09-01"),
            ("start", "2026-09-01T17:00+00:00"),
            ("sources", [{"label": "Official", "url": "example.com"}]),
            ("sequence", -1),
            ("details", "Not a list"),
            ("conflicts", {"test": "Not a list"}),
        ]
        for field, value in mutations:
            with self.subTest(field=field):
                event = dict(base_event)
                event[field] = value
                with self.assertRaises(ValueError):
                    generator.validate_source({"calendar": calendar, "events": [event]})

        all_day = dict(base_event)
        all_day.pop("start")
        all_day.pop("end")
        all_day.update(all_day=True, start_date="2026-09-02", end_date="2026-09-01")
        with self.assertRaises(ValueError):
            generator.validate_source({"calendar": calendar, "events": [all_day]})


if __name__ == "__main__":
    unittest.main()
