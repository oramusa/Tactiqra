"""Offline validation tests; no network access or real-match completeness claims."""
import json
import tempfile
import unittest
from pathlib import Path
from validate_statsbomb_match import validate_file


def event(identifier: str, index: int) -> dict:
    return {
        "id": identifier, "index": index, "period": 1,
        "timestamp": "00:00:01.000", "type": {"name": "Pass"},
        "team": {"id": 1}, "possession": 1, "possession_team": {"id": 1},
        "location": [60, 40],
    }


class ValidationTests(unittest.TestCase):
    def write(self, directory: str, events) -> Path:
        path = Path(directory) / "events.json"
        path.write_text(json.dumps(events), encoding="utf-8")
        return path

    def test_valid_partial_events_do_not_claim_full_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            result = validate_file(self.write(directory, [event("a", 1), event("b", 2)]), "3773386")
        self.assertEqual(result["normalized_event_count"], 2)
        self.assertFalse(result["full_match_coverage_verified"])
        self.assertFalse(result["commercial_use_authorized"])

    def test_duplicate_ids_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, [event("a", 1), event("a", 2)])
            with self.assertRaises(ValueError):
                validate_file(path, "3773386")

    def test_empty_array_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, [])
            with self.assertRaises(ValueError):
                validate_file(path, "3773386")


if __name__ == "__main__":
    unittest.main()
