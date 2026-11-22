import json
from fastapi.testclient import TestClient
from app.main import app
from heatmap_engine import heatmap


def event(i, team, player, x=None, y=None, kind='Pass'):
    return {'id': str(i), 'team': {'id': team}, 'player': {'id': player},
            'type': {'name': kind}, 'location': [x, y] if x is not None else None}


def test_team_and_player_separation():
    raw = [event(1, 1, 10, 0, 0), event(2, 1, 11, 120, 80), event(3, 2, 20, 50, 40)]
    team = heatmap(raw, team_id=1)
    player = heatmap(raw, team_id=1, player_id=10)
    assert team['plotted_events'] == 2
    assert player['plotted_events'] == 1
    assert team['grid'][0][0] == 1 and team['grid'][-1][-1] == 1
    assert sum(map(sum, team['grid'])) == 2


def test_missing_location_and_filter():
    raw = [event(1, 1, 10), event(2, 1, 10, 20, 20, 'Shot')]
    result = heatmap(raw, team_id=1, event_type='Pass')
    assert result['status'] == 'insufficient_data'
    assert result['eligible_events'] == 1 and result['missing_location_events'] == 1


def test_invalid_coordinates_do_not_pollute():
    raw = [event(1, 1, 10, -1, 0), event(2, 1, 10, float('nan'), 3)]
    result = heatmap(raw, team_id=1)
    assert result['plotted_events'] == 0 and result['missing_location_events'] == 2


def test_api_no_file(monkeypatch):
    monkeypatch.delenv('FOOTBALLIQ_HISTORICAL_EVENTS', raising=False)
    with TestClient(app) as client:
        assert client.get('/api/v1/heatmap/events?team_id=1').json()['status'] == 'insufficient_data'
        assert client.get('/api/v1/heatmap/events').status_code == 422


def test_api_local_historical_file(monkeypatch, tmp_path):
    source = tmp_path / 'events.json'
    source.write_text(json.dumps([event(1, 1, 10, 60, 40), event(2, 2, 20, 60, 40)]))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS', str(source))
    with TestClient(app) as client:
        data = client.get('/api/v1/heatmap/events?team_id=1').json()
        assert data['plotted_events'] == 1 and data['provisional'] is True
        assert data['direction_normalized'] is False
        assert data['evidence'][0]['event_ids'] == ['1']


def test_period_filter_excludes_other_halves():
    raw = [event(1,1,10,30,20), event(2,1,10,90,60)]
    raw[0]['period']=1
    raw[1]['period']=2
    one = heatmap(raw,team_id=1,period=1)
    two = heatmap(raw,team_id=1,period=2)
    assert one['plotted_events']==1 and two['plotted_events']==1
    assert one['grid'] != two['grid']
    assert one['period']==1

def test_api_period_filter(monkeypatch,tmp_path):
    source=tmp_path/'events.json'
    raw=[event(1,1,10,30,20),event(2,1,10,90,60)]
    raw[0]['period']=1; raw[1]['period']=2
    source.write_text(json.dumps(raw))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(source))
    with TestClient(app) as c:
        assert c.get('/api/v1/heatmap/events?team_id=1&period=2').json()['plotted_events']==1
        assert c.get('/api/v1/heatmap/events?team_id=1&period=7').status_code==422
