import importlib.util
import sys
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
scripts_path = str(ROOT / "scripts")
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)
spec = importlib.util.spec_from_file_location("validate_updates", ROOT / "scripts" / "validate_updates.py")
updates = importlib.util.module_from_spec(spec)
assert spec.loader
sys.modules[spec.name] = updates
spec.loader.exec_module(updates)


def dataset() -> dict:
    return {
        "events": [
            {
                "id": "test-event",
                "title": "Original title",
                "start": "2026-09-01T10:00",
                "last_verified": "2026-08-09",
                "last_modified": "2026-08-09",
                "sequence": 0,
            }
        ]
    }


class UpdateValidationTests(unittest.TestCase):
    def test_changed_event_requires_revision_bump(self):
        old = dataset()
        new = deepcopy(old)
        new["events"][0]["title"] = "Updated title"
        errors = updates.validate_updates(new, old)
        self.assertTrue(any("sequence must increase" in error for error in errors))
        self.assertTrue(any("last_modified must be later" in error for error in errors))

    def test_changed_event_with_revision_bump_passes(self):
        old = dataset()
        new = deepcopy(old)
        new["events"][0].update(
            title="Updated title",
            sequence=1,
            last_modified="2026-08-09T23:00:00Z",
        )
        self.assertEqual(updates.validate_updates(new, old), [])

    def test_removed_event_id_is_rejected(self):
        self.assertTrue(updates.validate_updates({"events": []}, dataset()))

    def test_removed_event_id_is_allowed_when_retired(self):
        retired = {"events": [], "retired": [{"id": "test-event", "reason": "no longer relevant", "retired_on": "2026-08-15"}]}
        self.assertEqual(updates.validate_updates(retired, dataset()), [])

    def test_retiring_a_series_covers_its_generated_occurrences(self):
        old = {
            "events": [
                {
                    "id": "test-series",
                    "title": "Series",
                    "start_time": "16:30",
                    "end_time": "19:30",
                    "occurrences": [{"date": "2026-08-13"}, {"date": "2026-08-14"}],
                    "last_verified": "2026-08-09",
                    "last_modified": "2026-08-09",
                    "sequence": 0,
                }
            ]
        }
        retired = {"events": [], "retired": [{"id": "test-series", "reason": "dropped", "retired_on": "2026-08-15"}]}
        self.assertEqual(updates.validate_updates(retired, old), [])

    def test_retiring_one_occurrence_does_not_cover_its_siblings(self):
        old = {
            "events": [
                {
                    "id": "test-series",
                    "title": "Series",
                    "start_time": "16:30",
                    "end_time": "19:30",
                    "occurrences": [{"date": "2026-08-13"}, {"date": "2026-08-14"}],
                    "last_verified": "2026-08-09",
                    "last_modified": "2026-08-09",
                    "sequence": 0,
                }
            ]
        }
        retired = {
            "events": [],
            "retired": [{"id": "test-series-2026-08-13", "reason": "dropped", "retired_on": "2026-08-15"}],
        }
        errors = updates.validate_updates(retired, old)
        self.assertTrue(any("test-series-2026-08-14" in error for error in errors))
        self.assertFalse(any("test-series-2026-08-13" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
