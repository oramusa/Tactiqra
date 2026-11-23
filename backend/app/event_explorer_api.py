"""Read-only, bounded exploration of the separately configured historical StatsBomb file."""
from fastapi import APIRouter, Query
from app.heatmap_api import load_events

router = APIRouter(prefix='/api/v1/event-explorer', tags=['historical-event-explorer'])

@router.get('/events')
def explore_events(team_id: int | None = Query(None, gt=0),
                   event_type: str | None = Query(None, max_length=80),
                   period: int | None = Query(None, ge=1, le=5),
                   cursor: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100)):
    raw = load_events()
    if raw is None:
        return {'status': 'insufficient_data', 'reason': 'Historical event JSON not configured', 'items': [], 'next_cursor': None}
    matches = []
    for idx, event in enumerate(raw):
        if idx < cursor or not isinstance(event, dict):
            continue
        team = event.get('team') or {}
        kind = event.get('type') or {}
        if not isinstance(team, dict) or not isinstance(kind, dict):
            continue
        if team_id is not None and team.get('id') != team_id:
            continue
        if event_type is not None and kind.get('name') != event_type:
            continue
        if period is not None and event.get('period') != period:
            continue
        location = event.get('location')
        safe_location = location[:2] if isinstance(location, list) and len(location) >= 2 and all(type(x) in (int, float) for x in location[:2]) else None
        player = event.get('player')
        matches.append({'event_id': event.get('id'), 'index': idx, 'minute': event.get('minute'), 'second': event.get('second'), 'period': event.get('period'), 'team': team.get('name'), 'team_id': team.get('id'), 'player': player.get('name') if isinstance(player, dict) else None, 'type': kind.get('name'), 'location': safe_location})
        if len(matches) > limit:
            break
    has_more = len(matches) > limit
    items = matches[:limit]
    return {'status': 'ready', 'source': 'local_historical_statsbomb_events', 'provisional': True, 'items': items, 'next_cursor': items[-1]['index'] + 1 if has_more else None, 'limit': limit, 'filters': {'team_id': team_id, 'event_type': event_type, 'period': period}}

@router.get('/shots')
def historical_shots():
    """Source-bound shot coordinates and outcomes; no inferred goals or xG."""
    raw = load_events()
    if raw is None:
        return {'status': 'insufficient_data', 'reason': 'Historical event JSON not configured', 'items': []}
    items = []
    for idx, event in enumerate(raw):
        if not isinstance(event, dict) or (event.get('type') or {}).get('name') != 'Shot':
            continue
        team = event.get('team') or {}
        player = event.get('player') or {}
        shot = event.get('shot') or {}
        outcome = shot.get('outcome') or {}
        loc = event.get('location')
        valid = isinstance(loc, list) and len(loc) >= 2 and all(type(v) in (int, float) and 0 <= v <= limit for v, limit in zip(loc[:2], (120, 80)))
        items.append({
            'event_id': event.get('id'), 'index': idx,
            'minute': event.get('minute'), 'second': event.get('second'),
            'period': event.get('period'),
            'team': team.get('name') if isinstance(team, dict) else None,
            'team_id': team.get('id') if isinstance(team, dict) else None,
            'player': player.get('name') if isinstance(player, dict) else None,
            'location': loc[:2] if valid else None,
            'outcome': outcome.get('name') if isinstance(outcome, dict) else None,
            'shot_type': (shot.get('type') or {}).get('name') if isinstance(shot.get('type'), dict) else None,
            'statsbomb_xg': shot.get('statsbomb_xg') if isinstance(shot.get('statsbomb_xg'), (float, int)) else None,
        })
    return {
        'status': 'ready', 'source': 'local_historical_statsbomb_events',
        'provisional': True, 'shot_count': len(items),
        'located_count': sum(item['location'] is not None for item in items),
        'items': items,
        'notes': 'Raw source shot outcomes; not independently reconciled with official score. Shot direction not verified.',
    }


@router.get('/shot-context')
def shot_context(event_id: str = Query(..., min_length=8, max_length=80),
                 limit: int = Query(12, ge=1, le=30)):
    """Bounded source event window; adjacency is not proof of a causal sequence."""
    raw = load_events()
    if raw is None:
        return {'status': 'insufficient_data', 'reason': 'Historical event JSON not configured', 'items': []}
    match = next((i for i, e in enumerate(raw) if isinstance(e, dict) and
                  e.get('id') == event_id and (e.get('type') or {}).get('name') == 'Shot'), None)
    if match is None:
        return {'status': 'not_found', 'reason': 'Shot event not found', 'items': []}
    target = raw[match]
    period = target.get('period')
    possession = target.get('possession')
    candidates = [(i, e) for i, e in enumerate(raw[:match]) if isinstance(e, dict) and
                  e.get('period') == period and possession is not None and
                  e.get('possession') == possession]
    chosen = candidates[-limit:] if possession is not None else []
    chosen.append((match, target))
    items = []
    for idx, event in chosen:
        team = event.get('team')
        player = event.get('player')
        kind = event.get('type')
        location = event.get('location')
        items.append({
            'event_id': event.get('id'), 'index': idx, 'minute': event.get('minute'),
            'second': event.get('second'), 'period': event.get('period'),
            'possession': event.get('possession'),
            'team': team.get('name') if isinstance(team, dict) else None,
            'player': player.get('name') if isinstance(player, dict) else None,
            'type': kind.get('name') if isinstance(kind, dict) else None,
            'location': location[:2] if isinstance(location, list) and len(location) >= 2
                        and all(type(v) in (int, float) for v in location[:2]) else None,
        })
    # Explicit source labels only. Do not infer a causal chain from adjacency.
    evidence = []
    for item in items:
        if item['type'] in ('Error', 'Dispossessed', 'Pressure', 'Duel', 'Ball Receipt*', 'Shot'):
            original = raw[item['index']]
            detail = original.get('shot') if item['type'] == 'Shot' else original.get(item['type'].lower().replace(' ', '_').replace('*', ''))
            if not isinstance(detail, dict):
                detail = {}
            outcome = detail.get('outcome')
            if not isinstance(outcome, dict):
                outcome = {}
            evidence.append({
                'event_id': item['event_id'], 'type': item['type'],
                'minute': item['minute'], 'second': item['second'],
                'team': item['team'], 'player': item['player'],
                'outcome': outcome.get('name'),
                'shot_xg': detail.get('statsbomb_xg') if item['type'] == 'Shot'
                           and type(detail.get('statsbomb_xg')) in (int, float) else None,
            })
    interpretation = {
        'status': 'source_observations',
        'evidence': evidence,
        'has_error_label': any(e['type'] == 'Error' for e in evidence),
        'has_pressure_label': any(e['type'] == 'Pressure' for e in evidence),
        'has_dispossessed_label': any(e['type'] == 'Dispossessed' for e in evidence),
        'note': 'Source event labels within the selected possession; not proof that pressure or error caused the goal.'
    }
    return {'status': 'ready', 'source': 'local_historical_statsbomb_events',
            'shot_event_id': event_id, 'possession': possession, 'period': period,
            'has_possession': possession is not None, 'items': items,
            'interpretation': interpretation,
            'truncated': len(candidates) > limit,
            'notes': 'Same-possession events preceding the shot in file order. '
                     'Not a validated causal chain, tracking reconstruction, or tactical attribution.'}
