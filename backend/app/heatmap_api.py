"""Read-only local pilot heatmap API; not associated with selected live team."""
import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from heatmap_engine import heatmap
from heatmap_compare import compare_heatmaps
from direction_metadata import load_verified_directions, DirectionMetadataError

router = APIRouter(prefix='/api/v1/heatmap', tags=['historical-heatmap'])

def load_events():
    configured = os.getenv('FOOTBALLIQ_HISTORICAL_EVENTS')
    if not configured:
        return None
    path = Path(configured)
    if not path.is_file() or path.stat().st_size > 30_000_000:
        raise HTTPException(503, 'Event source unavailable')
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError):
        raise HTTPException(503, 'Invalid event source')
    if not isinstance(raw, list) or len(raw) > 200_000:
        raise HTTPException(503, 'Invalid event source structure')
    return raw

@router.get('/catalog')
def catalog():
    raw = load_events()
    if raw is None:
        return {'status': 'insufficient_data', 'reason': 'Historical event JSON not configured', 'teams': [], 'event_types': []}
    teams = {}
    event_types = set()
    for event in raw:
        if not isinstance(event, dict):
            continue
        team = event.get('team')
        player = event.get('player')
        kind = event.get('type')
        if isinstance(kind, dict) and isinstance(kind.get('name'), str):
            event_types.add(kind['name'])
        if not isinstance(team, dict) or type(team.get('id')) is not int:
            continue
        tid = team['id']
        entry = teams.setdefault(tid, {'id': tid, 'name': team.get('name') or str(tid), 'players': {}})
        if isinstance(player, dict) and type(player.get('id')) is int:
            entry['players'][player['id']] = {'id': player['id'], 'name': player.get('name') or str(player['id'])}
    result = []
    for entry in sorted(teams.values(), key=lambda t: (t['name'], t['id'])):
        result.append({'id': entry['id'], 'name': entry['name'], 'players': sorted(entry['players'].values(), key=lambda x: (x['name'], x['id']))})
    return {'status': 'ready' if result else 'insufficient_data', 'source': 'local_historical_statsbomb_events', 'teams': result, 'event_types': sorted(event_types)}

def get_directions(team_id):
    configured = os.getenv('FOOTBALLIQ_HISTORICAL_EVENTS')
    metadata = os.getenv('FOOTBALLIQ_DIRECTION_METADATA')
    if not configured or not metadata:
        raise HTTPException(422, 'Verified direction metadata not configured')
    try:
        return load_verified_directions(Path(metadata), Path(configured), team_id)
    except (DirectionMetadataError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc

@router.get('/events')
def events_heatmap(team_id: int | None = None, player_id: int | None = None,
                   event_type: str | None = Query(None, max_length=80),
                   period: int | None = Query(None, ge=1, le=5),
                   columns: int = Query(12, ge=1, le=60), rows: int = Query(8, ge=1, le=40),
                   normalize: bool = False):
    if team_id is None and player_id is None:
        raise HTTPException(422, 'team_id or player_id required')
    raw = load_events()
    if raw is None:
        return {'status': 'insufficient_data', 'reason': 'Historical event JSON not configured'}
    directions, provenance = get_directions(team_id) if normalize else (None, None)
    result = heatmap(raw, team_id=team_id, player_id=player_id,
                     event_type=event_type, period=period, columns=columns, rows=rows, attacking_directions=directions)
    if provenance is not None:
        result['direction_provenance'] = provenance
    result['source'] = 'local_historical_statsbomb_events'
    result['provisional'] = True
    return result

@router.get('/compare')
def compare(team_a: int, team_b: int, event_type: str | None = Query(None, max_length=80),
            period: int | None = Query(None, ge=1, le=5),
            columns: int = Query(12, ge=1, le=60), rows: int = Query(8, ge=1, le=40),
            normalize: bool = False):
    if team_a == team_b:
        raise HTTPException(422, 'Select two distinct teams')
    raw = load_events()
    if raw is None:
        return {'status': 'insufficient_data', 'reason': 'Historical event JSON not configured'}
    directions_a, provenance_a = get_directions(team_a) if normalize else (None, None)
    directions_b, provenance_b = get_directions(team_b) if normalize else (None, None)
    result = compare_heatmaps(raw, team_a=team_a, team_b=team_b,
                              event_type=event_type, period=period, columns=columns, rows=rows,
                              directions_a=directions_a, directions_b=directions_b)
    if normalize:
        result['direction_provenance'] = {'team_a': provenance_a, 'team_b': provenance_b}
    result['source'] = 'local_historical_statsbomb_events'
    result['provisional'] = True
    return result


@router.get('/direction-status')
def direction_status(team_id: int, opponent_id: int | None = None):
    """Report verified metadata availability without exposing source details."""
    if opponent_id is not None and opponent_id == team_id:
        raise HTTPException(422, 'Select two distinct teams')
    if load_events() is None:
        return {'available': False, 'reason': 'Historical event JSON not configured'}
    try:
        _, first = get_directions(team_id)
        if opponent_id is not None:
            get_directions(opponent_id)
    except HTTPException as exc:
        return {'available': False, 'reason': str(exc.detail)}
    return {'available': True, 'verification_status': first['verification_status'], 'evidence_note': first['evidence_note']}
