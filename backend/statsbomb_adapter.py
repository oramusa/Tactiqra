"""FootballIQ StatsBomb Open Data event normalizer (prototype; no commercial rights implied)."""
from __future__ import annotations
from datetime import timedelta
from typing import Any

EVENT_TYPES = {
    'Pass': 'pass', 'Ball Recovery': 'ball_recovery', 'Dispossessed': 'dispossessed',
    'Interception': 'interception', 'Shot': 'shot', 'Carry': 'carry',
    'Dribble': 'dribble', 'Duel': 'duel', 'Miscontrol': 'miscontrol',
    'Ball Receipt*': 'ball_receipt', 'Foul Committed': 'foul_committed',
    'Half End': 'half_end', 'Half Start': 'half_start', 'Out': 'out',
    'Offside': 'offside', 'Injury Stoppage': 'injury_stoppage', 'Referee Ball-Drop': 'referee_ball_drop',
}


def timestamp_ms(value: str) -> int:
    parts = value.split(':')
    if len(parts) != 3:
        raise ValueError('timestamp must be HH:MM:SS.mmm')
    h, m = int(parts[0]), int(parts[1])
    sec, dot, ms = parts[2].partition('.')
    if not (0 <= m < 60 and 0 <= int(sec) < 60 and 0 <= h <= 23):
        raise ValueError('invalid timestamp')
    fraction = int((ms + '000')[:3]) if dot else 0
    return ((h * 3600 + m * 60 + int(sec)) * 1000 + fraction)


def normalize_event(event: dict[str, Any], match_id: str, source_record_id: str) -> dict[str, Any]:
    required = ('id', 'index', 'period', 'timestamp', 'type', 'team', 'possession', 'possession_team')
    missing = [k for k in required if event.get(k) is None]
    if missing:
        raise ValueError(f'missing StatsBomb fields: {missing}')
    typ = event['type']['name']
    location = event.get('location')
    if location is not None and (not isinstance(location, list) or len(location) < 2):
        raise ValueError('invalid location')
    detail = event.get(typ.lower().replace(' ', '_')) or {}
    if typ == 'Ball Receipt*':
        detail = event.get('ball_receipt') or {}
    outcome = detail.get('outcome') if isinstance(detail, dict) else None
    return {
        'event_id': f'statsbomb:{match_id}:{event["id"]}',
        'match_id': str(match_id), 'provider': 'statsbomb',
        'provider_event_id': str(event['id']), 'provider_index': int(event['index']),
        'period': int(event['period']), 'timestamp_ms': timestamp_ms(event['timestamp']),
        'team_id': str(event['team']['id']),
        'player_id': str(event['player']['id']) if event.get('player') else None,
        'event_type': EVENT_TYPES.get(typ, 'other'), 'provider_event_type': typ,
        'outcome': outcome.get('name') if isinstance(outcome, dict) else None,
        'possession_id': f'{match_id}:{event["possession"]}',
        'possession_team_id': str(event['possession_team']['id']),
        'play_pattern': (event.get('play_pattern') or {}).get('name'),
        'location': {'x': float(location[0]), 'y': float(location[1])} if location else None,
        'raw_location': location, 'coordinate_system': 'statsbomb_120x80',
        'related_event_ids': event.get('related_events', []),
        'source_record_id': source_record_id,
        'validation_status': 'normalized_unverified',
    }


def normalize_match(events: list[dict[str, Any]], match_id: str, source_record_id: str) -> list[dict[str, Any]]:
    normalized = [normalize_event(e, match_id, source_record_id) for e in events]
    keys = [(e['provider_event_id']) for e in normalized]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate provider event IDs')
    return sorted(normalized, key=lambda e: (e['period'], e['timestamp_ms'], e['provider_index']))
