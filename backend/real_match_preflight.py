#!/usr/bin/env python3
"""Validate a StatsBomb event file before enabling local historical APIs.
Does not assert match identity from event JSON alone.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
from uuid import UUID

MAX_BYTES = 30_000_000

def inspect_file(path: Path, expected_teams=None):
    if not path.is_file():
        raise ValueError('File does not exist')
    size = path.stat().st_size
    if not 0 < size <= MAX_BYTES:
        raise ValueError('File is empty or exceeds 30 MB')
    raw = path.read_bytes()
    events = json.loads(raw)
    if not isinstance(events, list) or not events:
        raise ValueError('Expected nonempty StatsBomb event list')
    if len(events) > 200_000:
        raise ValueError('Too many events')
    ids = set()
    teams = collections.Counter()
    types = collections.Counter()
    failures = collections.Counter()
    for event in events:
        if not isinstance(event, dict):
            failures['invalid_event'] += 1
            continue
        eid = event.get('id')
        try:
            UUID(str(eid))
        except (TypeError, ValueError, AttributeError):
            failures['invalid_id'] += 1
        if eid in ids:
            failures['duplicate_id'] += 1
        ids.add(eid)
        team = event.get('team')
        kind = event.get('type')
        if not isinstance(team, dict) or not isinstance(team.get('name'), str) or type(team.get('id')) is not int:
            failures['invalid_team'] += 1
        else:
            teams[(team['id'], team['name'])] += 1
        if not isinstance(kind, dict) or not isinstance(kind.get('name'), str):
            failures['invalid_type'] += 1
        else:
            types[kind['name']] += 1
        loc = event.get('location')
        if loc is not None and (not isinstance(loc, list) or len(loc) < 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in loc[:2]) or not (0 <= loc[0] <= 120 and 0 <= loc[1] <= 80)):
            failures['invalid_location'] += 1
    if expected_teams is not None and {name for _, name in teams} != set(expected_teams):
        failures['unexpected_teams'] += 1
    return {
        'status': 'structurally_valid' if not failures else 'rejected',
        'identity_status': 'unverified_requires_independent_match_metadata',
        'file': path.name, 'bytes': size, 'sha256': hashlib.sha256(raw).hexdigest(),
        'events': len(events), 'teams': [{'id': tid, 'name': name, 'events': n} for (tid, name), n in sorted(teams.items())],
        'event_types': dict(types), 'failures': dict(failures),
        'note': 'This check cannot independently prove source authenticity, match ID, score, or tactical correctness.'
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = inspect_file(args.file)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + '\n', encoding='utf-8')
    print(rendered)
    raise SystemExit(0 if result['status'] == 'structurally_valid' else 2)

if __name__ == '__main__':
    main()
