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
