"""Conservative event-based transition candidates, never definitive counterattacks."""
from collections import defaultdict
from fastapi import APIRouter, Query
from .heatmap_api import load_events

router = APIRouter(prefix='/api/v1/opponentiq', tags=['transition-candidates'])
RECOVERY = {'Ball Recovery', 'Interception'}

def second(event):
    try:
        stamp = event['timestamp']
        h, m, s = stamp.split(':')
        value = int(h)*3600 + int(m)*60 + float(s)
        if not (0 <= int(m) < 60 and 0 <= float(s) < 60 and value >= 0):
            return None
        return value
    except (KeyError, AttributeError, TypeError, ValueError):
        return None

def transition_candidates(events, max_examples=20, max_seconds=15):
    groups = defaultdict(list)
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        p, team = event.get('possession'), event.get('possession_team')
        if type(p) is int and p > 0 and isinstance(team, dict) and type(team.get('id')) is int:
            groups[(p, team['id'])].append((index, event))
    totals = defaultdict(lambda: {'examined_possessions': 0, 'candidates': 0, 'excluded_missing_evidence': 0, 'examples': []})
    for (p, team_id), indexed in sorted(groups.items()):
        evs = [e for _, e in indexed]
        name = next((e.get('possession_team', {}).get('name') for e in evs if isinstance(e.get('possession_team'), dict) and e['possession_team'].get('name')), str(team_id))
        row = totals[(team_id, name)]
        row['examined_possessions'] += 1
        periods = {e.get('period') for e in evs}
        if len(periods) != 1 or any(second(e) is None for e in evs):
            row['excluded_missing_evidence'] += 1
            continue
        # Require explicit successful recovery event belonging to the possessing team.
        recovery = next((e for e in evs[:4] if isinstance(e.get('team'), dict) and e['team'].get('id') == team_id
                         and isinstance(e.get('type'), dict) and e['type'].get('name') in RECOVERY
                         and not (isinstance(e.get('ball_recovery'), dict) and e['ball_recovery'].get('recovery_failure'))
                         and not (isinstance(e.get('interception'), dict) and isinstance(e['interception'].get('outcome'), dict) and e['interception']['outcome'].get('name') in {'Lost', 'Lost In Play', 'Lost Out'})), None)
        if recovery is None:
            continue
        start = second(recovery)
        shots = [e for e in evs if isinstance(e.get('team'), dict) and e['team'].get('id') == team_id
                 and isinstance(e.get('type'), dict) and e['type'].get('name') == 'Shot'
                 and 0 <= second(e)-start <= max_seconds]
        if not shots:
            continue
        shot = min(shots, key=second)
        row['candidates'] += 1
        if len(row['examples']) < max_examples:
            row['examples'].append({'possession': p, 'period': recovery['period'],
                                    'duration_seconds': round(second(shot)-start, 3),
                                    'recovery_event_id': recovery.get('id'), 'shot_event_id': shot.get('id'),
                                    'recovery_type': recovery['type']['name'],
                                    'shot_outcome': (shot.get('shot') or {}).get('outcome', {}).get('name'),
                                    'event_ids': [e.get('id') for e in evs if start <= second(e) <= second(shot)][:100]})
    return {'status': 'provisional' if totals else 'insufficient_data',
            'match_identity_verified': False, 'classification': 'rapid_recovery_to_shot_candidate_not_confirmed_counterattack',
            'max_seconds': max_seconds,
            'teams': [{'team_id': k[0], 'team_name': k[1], **v} for k, v in sorted(totals.items())],
            'limitations': ['Recovery and shot events do not prove a tactical counterattack.',
                            'Missing or inconsistent timestamps exclude a possession.',
                            'No direction or off-ball tracking inferred.',
                            'Match identity and source authenticity not independently verified.']}

@router.get('/transition-candidates')
def get_transition_candidates(max_examples: int = Query(20, ge=0, le=50), max_seconds: int = Query(15, ge=1, le=60)):
    events = load_events()
    if events is None:
        return {'status': 'not_configured', 'teams': [], 'match_identity_verified': False}
    return transition_candidates(events, max_examples, max_seconds)
