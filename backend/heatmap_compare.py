"""Compare two event heatmaps without confusing counts with tracking or possession."""
from heatmap_engine import heatmap

def compare_heatmaps(events, *, team_a, team_b, player_a=None, player_b=None,
                     event_type=None, period=None, columns=12, rows=8, directions_a=None, directions_b=None):
    if team_a == team_b:
        raise ValueError('Select two distinct teams')
    a = heatmap(events, team_id=team_a, player_id=player_a, event_type=event_type,
                period=period, columns=columns, rows=rows, attacking_directions=directions_a)
    b = heatmap(events, team_id=team_b, player_id=player_b, event_type=event_type,
                period=period, columns=columns, rows=rows, attacking_directions=directions_b)
    delta = [[av-bv for av,bv in zip(ar,br)] for ar,br in zip(a['grid'],b['grid'])]
    return {
        'status': 'event_density_comparison' if a['plotted_events'] and b['plotted_events'] else 'insufficient_data',
        'map_type': 'event_heatmap_not_tracking',
        'direction_normalized': directions_a is not None and directions_b is not None,
        'team_a': a, 'team_b': b,
        'delta_grid': delta,
        'delta_total': a['plotted_events'] - b['plotted_events'],
        'warning': 'Event counts, not tracking. Compare equal event types and time windows; directions normalized only when explicitly verified for both teams.'
    }
