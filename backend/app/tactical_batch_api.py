"""Conservative multi-match aggregation of locally reviewed provenance-bearing reports.

A file checksum is NOT a tactical accuracy certificate. Never backfill missing matches.
"""
import hashlib
import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix='/api/v1/opponentiq', tags=['tactical-batch'])


def aggregate_reports(team_id: int, match_ids: list[int], manifest_path: Path):
    if not match_ids or len(match_ids) > 100 or any(type(mid) is not int or mid <= 0 for mid in match_ids):
        raise HTTPException(422, 'Provide 1–100 positive match IDs')
    if len(set(match_ids)) != len(match_ids):
        raise HTTPException(422, 'Duplicate match IDs are not permitted')
    try:
        if not manifest_path.is_file() or manifest_path.stat().st_size > 2_000_000:
            raise ValueError('manifest missing or too large')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if not isinstance(manifest, dict) or not isinstance(manifest.get('reports'), list):
            raise ValueError('invalid manifest')
    except (OSError, ValueError, UnicodeError) as exc:
        raise HTTPException(503, 'Tactical report manifest unavailable or invalid') from exc
    base = manifest_path.resolve().parent
    entries = {}
    for entry in manifest['reports']:
        if isinstance(entry, dict) and type(entry.get('provider_match_id')) is int:
            entries.setdefault(entry['provider_match_id'], []).append(entry)
    results = []
    total_transitions = total_shots = total_goals = 0
    for mid in match_ids:
        matches = entries.get(mid, [])
        row = {'matchId': mid, 'status': 'missing', 'reason': 'No explicit report mapping', 'transitionCount': None}
        if len(matches) > 1:
            row.update(status='invalid', reason='Ambiguous duplicate report mappings')
        elif matches:
            entry = matches[0]
            rel, digest = entry.get('relative_path'), entry.get('sha256')
            if (type(entry.get('team_id')) is not int or entry['team_id'] != team_id
                    or not isinstance(rel, str) or not isinstance(digest, str)
                    or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)):
                row.update(status='invalid', reason='Team or provenance mismatch')
            else:
                path = (base / rel).resolve()
                if not path.is_relative_to(base) or not path.is_file() or path.stat().st_size > 8_000_000:
                    row.update(status='invalid', reason='Missing, unsafe or oversized report')
                else:
                    try:
                        raw = path.read_bytes()
                        if hashlib.sha256(raw).hexdigest() != digest:
                            raise ValueError('Checksum mismatch')
                        report = json.loads(raw)
                        transitions = report['transitions']
                        if (not isinstance(report, dict) or str(report.get('match_id')) != str(entry.get('event_match_id'))
                                or not isinstance(transitions, list) or len(transitions) > 100_000
                                or type(report.get('event_count')) is not int or report['event_count'] < 0):
                            raise ValueError('Invalid report structure or event match ID')
                        if any(not isinstance(t, dict) or str(t.get('match_id', report['match_id'])) != str(report['match_id'])
                               or t.get('verification_status') not in ('provisional', 'provisional_verified', 'needs_review')
                               or type(t.get('shot')) is not bool or type(t.get('goal')) is not bool
                               or (t['goal'] and not t['shot'])
                               or not isinstance(t.get('evidence_event_ids'), list)
                               for t in transitions):
                            raise ValueError('Invalid transition evidence')
                        shots = sum(t['shot'] for t in transitions)
                        goals = sum(t['goal'] for t in transitions)
                        total_transitions += len(transitions)
                        total_shots += shots
                        total_goals += goals
                        row.update(status='provisional', reason='Checksum verified; tactical accuracy not independently validated',
                                   transitionCount=len(transitions), shotCount=shots, goalCount=goals,
                                   eventMatchId=str(report['match_id']))
                    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
                        row.update(status='invalid', reason='Report checksum, format or evidence invalid')
        results.append(row)
    valid = sum(r['status'] == 'provisional' for r in results)
    return {'status': 'provisional_unreviewed' if valid else 'insufficient_data',
            'teamId': team_id, 'requestedMatches': len(match_ids), 'analyzedMatches': valid,
            'coverageRatio': round(valid / len(match_ids), 4),
            'perAnalyzedMatch': ({'transitions': round(total_transitions / valid, 3),
                                  'shotsAfterTransition': round(total_shots / valid, 3),
                                  'goalsAfterTransition': round(total_goals / valid, 3)} if valid else None),
            'totals': {'transitions': total_transitions, 'shotsAfterTransition': total_shots,
                       'goalsAfterTransition': total_goals}, 'matches': results,
            'warning': 'Provisional candidate events only. File integrity does not prove team identity, tactical accuracy, recall, or complete match coverage. Per-90 metrics require verified playing time.'}


@router.get('/tactical-batch')
def tactical_batch(team_id: int = Query(..., gt=0), match_ids: str = Query(..., min_length=1, max_length=1000)):
    try:
        ids = [int(x) for x in match_ids.split(',')]
    except ValueError as exc:
        raise HTTPException(422, 'Invalid comma-separated match IDs') from exc
    if not 1 <= len(ids) <= 100 or any(x <= 0 for x in ids) or len(set(ids)) != len(ids):
        raise HTTPException(422, 'Provide 1–100 unique positive match IDs')
    configured = os.getenv('FOOTBALLIQ_TACTICAL_REPORT_MANIFEST')
    if not configured:
        return {'status': 'not_configured', 'teamId': team_id, 'requestedMatches': len(ids),
                'analyzedMatches': 0, 'perAnalyzedMatch': None,
                'warning': 'No verified tactical report manifest configured; tactical metrics unavailable.'}
    return aggregate_reports(team_id, ids, Path(configured))
