"""Read-only evidence-chain resolver for a separately configured historical pilot."""
from fastapi import APIRouter, HTTPException, Query
from app.evidence_api import load_report
from match_identity import verify_match_identity
import json

router = APIRouter(prefix='/api/v1/evidence', tags=['historical-evidence'])

@router.get('/chain')
def evidence_chain(start_event_id: str = Query(..., min_length=1, max_length=150)):
    report = load_report()
    if report is None:
        return {'status': 'insufficient_data', 'reason': 'Historical report not configured', 'items': []}
    candidates = [t for t in report['transitions'] if str(t.get('start_event_id')) == start_event_id]
    if not candidates:
        raise HTTPException(404, 'Transition not found in historical report')
    if len(candidates) != 1:
        raise HTTPException(409, 'Ambiguous transition start event ID')
    transition = candidates[0]
    # A local events file alone has no authoritative match identity. Require an
    # explicit match binding from deployment configuration, never infer from team names.
    import os
    configured_match = os.getenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '').strip()
    if not configured_match or configured_match != str(report['match_id']):
        return {'status': 'match_unverified', 'reason': 'Event file match ID is not explicitly bound to the pilot report', 'items': []}
    # Bind evidence to exact source bytes, not merely an operator-entered match ID.
    # A separately recorded SHA-256 digest prevents accidental file substitution.
    import hashlib
    from pathlib import Path
    source_path = os.getenv('FOOTBALLIQ_HISTORICAL_EVENTS', '').strip()
    expected_digest = os.getenv('FOOTBALLIQ_HISTORICAL_EVENTS_SHA256', '').strip().lower()
    if not source_path or len(expected_digest) != 64 or any(c not in '0123456789abcdef' for c in expected_digest):
        return {'status': 'source_unverified', 'reason': 'Event file SHA-256 binding is missing or invalid', 'items': []}
    try:
        source = Path(source_path)
        if not source.is_file() or source.stat().st_size > 30_000_000:
            return {'status': 'source_unverified', 'reason': 'Event file unavailable or too large', 'items': []}
        source_bytes = source.read_bytes()
        actual_digest = hashlib.sha256(source_bytes).hexdigest()
    except OSError:
        return {'status': 'source_unverified', 'reason': 'Event file cannot be read', 'items': []}
    if actual_digest != expected_digest:
        return {'status': 'source_mismatch', 'reason': 'Event file SHA-256 differs from configured digest', 'items': []}
    # Parse the exact bytes that passed the digest check. Never trust a separate
    # in-memory event loader, which could point to a different file or revision.
    try:
        raw = json.loads(source_bytes)
    except (ValueError, UnicodeDecodeError):
        return {'status': 'source_unverified', 'reason': 'Verified event file is not valid JSON', 'items': []}
    if not isinstance(raw, list) or not all(isinstance(event, dict) for event in raw):
        return {'status': 'source_unverified', 'reason': 'Verified event file is not an event array', 'items': []}
    if type(report.get('event_count')) is not int or report['event_count'] != len(raw):
        return {'status': 'source_mismatch', 'reason': 'Report event count differs from source', 'items': []}
    # Cross-provider metadata is an additional required gate. An operator-provided
    # JSON binding is not provider authentication; expose only provisional evidence.
    identity_path = os.getenv('FOOTBALLIQ_MATCH_IDENTITY_JSON', '').strip()
    if not identity_path:
        return {'status': 'identity_unverified', 'reason': 'Cross-provider match identity binding not configured', 'items': []}
    try:
        binding_file = Path(identity_path)
        if not binding_file.is_file() or binding_file.stat().st_size > 100_000:
            raise ValueError('Invalid identity binding file')
        binding = json.loads(binding_file.read_text(encoding='utf-8'))
        if not isinstance(binding, dict):
            raise ValueError('Invalid identity binding')
        fd, sb, mapping = binding['football_data'], binding['statsbomb'], binding['team_mapping']
        if str(sb.get('match_id')) != str(report['match_id']) or str(sb.get('match_id')) != configured_match:
            return {'status': 'identity_mismatch', 'reason': 'Identity binding match ID differs from report or event binding', 'items': []}
        identity = verify_match_identity(fd, sb, mapping)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {'status': 'identity_unverified', 'reason': 'Cross-provider identity binding invalid or unreadable', 'items': []}
    if identity['status'] != 'metadata_consistent':
        return {'status': 'identity_mismatch', 'reasons': identity['reasons'], 'items': []}
    by_id = {}
    duplicate_ids = set()
    for e in raw:
        if not isinstance(e, dict) or not isinstance(e.get('id'), (str, int)):
            continue
        key = str(e['id'])
        if key in by_id:
            duplicate_ids.add(key)
        else:
            by_id[key] = e
    # Reject a source with ambiguous identifiers anywhere in the match, not only
    # in the selected transition. A source-wide collision makes provenance unsafe.
    if duplicate_ids:
        requested_ids = {str(i) for i in transition.get('evidence_event_ids', [])} if isinstance(transition.get('evidence_event_ids'), list) else set()
        if duplicate_ids & requested_ids:
            return {'status': 'ambiguous_evidence', 'reason': 'Duplicate evidence event IDs', 'items': []}
        return {'status': 'ambiguous_source', 'reason': 'Duplicate event IDs in source match', 'items': []}
    if any(not isinstance(e.get('id'), (str, int)) or isinstance(e.get('id'), bool) or not str(e['id']).strip() for e in raw):
        return {'status': 'invalid_source', 'reason': 'Missing or invalid source event IDs', 'items': []}
    # Evidence must be a valid nonempty ordered subset of the source event list.
    # The transition start event is the first evidence item by contract.
    evidence_ids = transition.get('evidence_event_ids')
    if not isinstance(evidence_ids, list) or not evidence_ids or any(not isinstance(i, (str, int)) or isinstance(i, bool) for i in evidence_ids):
        return {'status': 'invalid_evidence', 'reason': 'Invalid evidence event IDs', 'items': []}
    if str(evidence_ids[0]) != start_event_id:
        return {'status': 'invalid_evidence', 'reason': 'Transition start differs from first evidence event', 'items': []}
    requested = [str(i) for i in transition['evidence_event_ids']]
    if len(requested) != len(set(requested)) or any(i in duplicate_ids for i in requested):
        return {'status': 'ambiguous_evidence', 'reason': 'Duplicate evidence event IDs', 'items': []}
    missing = [i for i in requested if i not in by_id]
    if missing:
        return {'status': 'incomplete_evidence', 'missing_event_ids': missing, 'items': []}
    items = []
    for event_id in requested:
        e = by_id[event_id]
        team, player, kind = e.get('team'), e.get('player'), e.get('type')
        loc = e.get('location')
        safe_loc = loc[:2] if isinstance(loc, list) and len(loc) >= 2 and all(type(n) in (int, float) and 0 <= n <= bound for n, bound in zip(loc[:2], (120, 80))) else None
        items.append({'event_id': event_id, 'period': e.get('period'), 'minute': e.get('minute'), 'second': e.get('second'), 'type': kind.get('name') if isinstance(kind, dict) else None, 'team': team.get('name') if isinstance(team, dict) else None, 'player': player.get('name') if isinstance(player, dict) else None, 'location': safe_loc})
    return {'status': 'provisional', 'match_id': str(report['match_id']), 'start_event_id': start_event_id, 'verification_status': transition['verification_status'], 'source_sha256': actual_digest, 'identity_status': 'metadata_consistent', 'items': items, 'warning': 'Matched event IDs only; tactical classification has not been independently verified.'}
