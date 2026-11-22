import pytest
from heatmap_engine import heatmap
from heatmap_compare import compare_heatmaps

EVENTS = [
    {'id': 'a', 'team': {'id': 1}, 'type': {'name': 'Pass'}, 'period': 1, 'location': [10, 20]},
    {'id': 'b', 'team': {'id': 1}, 'type': {'name': 'Pass'}, 'period': 2, 'location': [110, 60]},
    {'id': 'c', 'team': {'id': 2}, 'type': {'name': 'Pass'}, 'period': 1, 'location': [110, 60]},
]

def test_explicit_direction_normalization_aligns_periods():
    raw = heatmap(EVENTS, team_id=1)
    result = heatmap(EVENTS, team_id=1, attacking_directions={1: 'left_to_right', 2: 'right_to_left'})
    assert result['direction_normalized'] is True
    assert result['grid'][2][1] == 2
    assert raw['grid'][2][1] == 1
    assert result['plotted_events'] == 2
    assert result['evidence'][0]['event_ids'] == ['a', 'b']

def test_missing_direction_rejected_not_guessed():
    with pytest.raises(ValueError, match='Missing verified direction'):
        heatmap(EVENTS, team_id=1, attacking_directions={1: 'left_to_right'})

def test_bad_mapping_and_no_team_rejected():
    with pytest.raises(ValueError, match='Invalid verified'):
        heatmap(EVENTS, team_id=1, attacking_directions={1: 'unknown'})
    with pytest.raises(ValueError, match='requires a team'):
        heatmap(EVENTS, player_id=12, attacking_directions={1: 'left_to_right'})

def test_compare_both_teams_normalized():
    result = compare_heatmaps(EVENTS, team_a=1, team_b=2, directions_a={1:'left_to_right', 2:'right_to_left'}, directions_b={1:'right_to_left'})
    assert result['direction_normalized'] is True
    assert result['team_a']['grid'][2][1] == 2
    assert result['team_b']['grid'][2][1] == 1
    assert result['delta_grid'][2][1] == 1

def test_compare_without_mapping_is_explicitly_raw():
    result = compare_heatmaps(EVENTS, team_a=1, team_b=2)
    assert result['direction_normalized'] is False
