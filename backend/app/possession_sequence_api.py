"""Evidence-backed possession sequences; NOT a counterattack classifier."""
from collections import defaultdict
from fastapi import APIRouter, Query
from .heatmap_api import load_events

router = APIRouter(prefix='/api/v1/opponentiq', tags=['possession-sequences'])


def summarize_possessions(events, max_examples=10):
    groups = defaultdict(list)
    ignored = 0
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            ignored += 1
            continue
        possession = event.get('possession')
        team = event.get('possession_team')
        if type(possession) is not int or possession < 1 or not isinstance(team, dict) or type(team.get('id')) is not int:
            ignored += 1
            continue
        groups[(possession, team['id'])].append((index, event))
    results = defaultdict(lambda: {'possessions': 0, 'possessions_with_shot': 0, 'possessions_with_goal_shot': 0, 'examples': []})
    for (possession, team_id), indexed in sorted(groups.items()):
        first = indexed[0][1]
        name = (first.get('possession_team') or {}).get('name') or str(team_id)
        key = (team_id, name)
        row = results[key]
        row['possessions'] += 1
        shots = [e for _, e in indexed if isinstance(e.get('type'), dict) and e['type'].get('name') == 'Shot' and isinstance(e.get('team'), dict) and e['team'].get('id') == team_id]
        if shots:
            row['possessions_with_shot'] += 1
        goals = [e for e in shots if isinstance(e.get('shot'), dict) and isinstance(e['shot'].get('outcome'), dict) and e['shot']['outcome'].get('name') == 'Goal']
        if goals:
            row['possessions_with_goal_shot'] += 1
        if shots and len(row['examples']) < max_examples:
            row['examples'].append({'possession': possession, 'first_event_id': first.get('id'), 'shot_event_ids': [e.get('id') for e in shots][:10], 'event_count': len(indexed)})
    return {'status': 'provisional' if results else 'insufficient_data', 'source': 'configured_local_statsbomb_events', 'match_identity_verified': False,
            'ignored_events': ignored, 'teams': [{'team_id': k[0], 'team_name': k[1], **v} for k, v in sorted(results.items())],
            'limitations': ['A possession with a shot is NOT necessarily a counterattack or defensive transition.',
                            'Possession boundaries use StatsBomb possession IDs; sequence timing and tactical classification are not inferred.',
                            'Event-file match identity has not been independently verified.']}


@router.get('/possession-sequences')
def possession_sequences(max_examples: int = Query(10, ge=0, le=30)):
    events = load_events()
    if events is None:
        return {'status': 'not_configured', 'teams': [], 'match_identity_verified': False}
    return summarize_possessions(events, max_examples)
