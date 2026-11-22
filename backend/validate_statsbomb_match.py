"""Validate a locally downloaded StatsBomb event file without claiming full coverage.

Research/development only. Access to public data does not grant commercial rights.
Run: cd backend && python validate_statsbomb_match.py path/to/events.json --match-id 3773386
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statsbomb_adapter import normalize_match

MAX_BYTES = 30_000_000


def validate_file(path: Path, match_id: str) -> dict:
    if not match_id.isascii() or not match_id.isdecimal():
        raise ValueError("match_id must be numeric")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("source exceeds size limit")
    data = path.read_bytes()
    events = json.loads(data)
    if not isinstance(events, list) or not events:
        raise ValueError("source must be a nonempty JSON event array")
    digest = hashlib.sha256(data).hexdigest()
    normalized = normalize_match(events, match_id, f"statsbomb-open-data:{match_id}:{digest}")
    types: dict[str, int] = {}
    for event in normalized:
        kind = event["event_type"]
        types[kind] = types.get(kind, 0) + 1
    periods = sorted({event["period"] for event in normalized})
    return {
        "match_id": match_id,
        "provider": "statsbomb",
        "source_sha256": digest,
        "raw_event_count": len(events),
        "normalized_event_count": len(normalized),
        "periods_observed": periods,
        "event_type_counts": types,
        "duplicate_event_ids": 0,
        "structural_validation": "passed",
        "full_match_coverage_verified": False,
        "tactical_accuracy_verified": False,
        "commercial_use_authorized": False,
        "note": "Structural checks do not prove completeness, event accuracy, or redistribution rights.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--match-id", required=True)
    args = parser.parse_args()
    print(json.dumps(validate_file(args.source, args.match_id), indent=2))
