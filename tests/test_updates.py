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


if __name__ == "__main__":
    unittest.main()
