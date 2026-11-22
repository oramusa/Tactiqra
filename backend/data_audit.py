"""Offline, read-only FootballIQ provider/event data audit. No API keys required."""
import argparse
import json
from collections import Counter
from pathlib import Path


def audit_events(path: Path, expected_match_id: int | None = None) -> dict:
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, list):
        raise ValueError('StatsBomb event file must be a JSON list')
    ids, missing, invalid_location, types = set(), 0, 0, Counter()
    duplicates = 0
    for e in raw:
        if not isinstance(e, dict):
            raise ValueError('Event must be an object')
        eid = e.get('id')
        if not isinstance(eid, str) or not eid:
            missing += 1
        elif eid in ids:
            duplicates += 1
        else:
            ids.add(eid)
        types[str((e.get('type') or {}).get('name', 'Unknown'))] += 1
        loc = e.get('location')
        if loc is not None and (not isinstance(loc, list) or len(loc) < 2 or
                                any(type(v) not in (int, float) for v in loc[:2]) or
                                not (0 <= loc[0] <= 120 and 0 <= loc[1] <= 80)):
            invalid_location += 1
    issues = []
    if not raw: issues.append('empty_event_file')
    if missing: issues.append('missing_event_ids')
    if duplicates: issues.append('duplicate_event_ids')
    if invalid_location: issues.append('invalid_event_locations')
    # StatsBomb event exports do not necessarily contain a match_id on each event.
    # Filename is a hint, never proof of identity.
    if expected_match_id is not None and path.stem != str(expected_match_id):
        issues.append('filename_match_id_mismatch_unverified_identity')
    return {'source': 'local_statsbomb_json', 'file': str(path),
            'expectedMatchId': expected_match_id, 'identityVerified': False,
            'eventCount': len(raw), 'uniqueEventIds': len(ids),
            'missingEventIds': missing, 'duplicateEventIds': duplicates,
            'invalidLocations': invalid_location, 'eventTypes': dict(types.most_common()),
            'issues': issues, 'status': 'needs_review' if issues else 'structure_only_pass',
            'warning': 'Structure-only checks; cannot verify match identity, event completeness or tactical correctness.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('events', type=Path)
    p.add_argument('--match-id', type=int)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = audit_events(args.events, args.match_id)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(rendered + '\n', encoding='utf-8')
    print(rendered)
    return 0 if not result['issues'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
