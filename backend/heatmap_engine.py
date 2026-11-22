"""Deterministic StatsBomb event-location heatmap, not player tracking."""
from collections import defaultdict
import math

WIDTH, HEIGHT = 120.0, 80.0

def heatmap(events, *, team_id=None, player_id=None, event_type=None, period=None, columns=12, rows=8, attacking_directions=None):
    if not isinstance(events, list):
        raise ValueError('Events must be a list')
    if not (1 <= columns <= 60 and 1 <= rows <= 40):
        raise ValueError('Invalid grid dimensions')
    if team_id is None and player_id is None:
        raise ValueError('Select a team or player to avoid mixing unrelated teams')
    if period is not None and (type(period) is not int or period not in (1, 2, 3, 4, 5)):
        raise ValueError('Invalid match period')
    # No inferred direction: only explicitly verified team/period mappings may be used.
    if attacking_directions is not None:
        if team_id is None:
            raise ValueError('Direction normalization requires a team')
        if not isinstance(attacking_directions, dict):
            raise ValueError('Directions must be a period-to-direction mapping')
        for key, value in attacking_directions.items():
            if type(key) is not int or key not in (1, 2, 3, 4, 5) or value not in ('left_to_right', 'right_to_left'):
                raise ValueError('Invalid verified attacking direction')
    cells = [[0 for _ in range(columns)] for _ in range(rows)]
    evidence = defaultdict(list)
    eligible = missing_location = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        team = event.get('team') or {}
        player = event.get('player') or {}
        typ = event.get('type') or {}
        if not isinstance(team, dict) or not isinstance(player, dict) or not isinstance(typ, dict):
            continue
        if team_id is not None and str(team.get('id')) != str(team_id):
            continue
        if player_id is not None and str(player.get('id')) != str(player_id):
            continue
        if event_type is not None and typ.get('name') != event_type:
            continue
        if period is not None and event.get('period') != period:
            continue
        eligible += 1
        loc = event.get('location')
        if (not isinstance(loc, list) or len(loc) < 2 or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in loc[:2]) or
            not (0 <= loc[0] <= WIDTH and 0 <= loc[1] <= HEIGHT)):
            missing_location += 1
            continue
        x, y = loc[:2]
        if attacking_directions is not None:
            direction = attacking_directions.get(event.get('period'))
            if direction is None:
                raise ValueError('Missing verified direction for eligible event period')
            if direction == 'right_to_left':
                x, y = WIDTH - x, HEIGHT - y
        col = min(int(x / WIDTH * columns), columns - 1)
        row = min(int(y / HEIGHT * rows), rows - 1)
        cells[row][col] += 1
        if event.get('id') is not None:
            evidence[(row, col)].append(str(event['id']))
    plotted = sum(map(sum, cells))
    return {
        'status': 'event_density' if plotted else 'insufficient_data',
        'map_type': 'event_heatmap_not_tracking', 'coordinate_system': 'statsbomb_120x80',
        'direction_normalized': attacking_directions is not None, 'team_id': team_id, 'player_id': player_id,
        'event_type': event_type, 'period': period, 'columns': columns, 'rows': rows,
        'eligible_events': eligible, 'plotted_events': plotted,
        'missing_location_events': missing_location, 'grid': cells,
        'evidence': [{'row': r, 'column': c, 'event_ids': ids} for (r, c), ids in sorted(evidence.items())],
        'warning': ('Verified per-period attacking direction applied; event positions only, not tracking.' if attacking_directions is not None else 'Raw event positions only; attacking direction not normalized. Not a tracking heatmap.')
    }
