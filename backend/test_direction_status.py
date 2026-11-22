import hashlib, json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_direction_status_missing_source(monkeypatch):
    monkeypatch.delenv('FOOTBALLIQ_HISTORICAL_EVENTS', raising=False)
    assert client.get('/api/v1/heatmap/direction-status?team_id=1').json()['available'] is False

def test_direction_status_missing_metadata(tmp_path, monkeypatch):
    events = tmp_path / 'events.json'
    events.write_text('[]')
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS', str(events))
    monkeypatch.delenv('FOOTBALLIQ_DIRECTION_METADATA', raising=False)
    result = client.get('/api/v1/heatmap/direction-status?team_id=1')
    assert result.status_code == 200 and result.json()['available'] is False

def test_direction_status_verified_pair(tmp_path, monkeypatch):
    events = tmp_path / 'events.json'
    events.write_text('[]')
    meta = tmp_path / 'directions.json'
    meta.write_text(json.dumps({'verification_status':'manually_verified','source_sha256':hashlib.sha256(events.read_bytes()).hexdigest(),'evidence_note':'Reviewed manually for test','teams':{'1':{'1':'left_to_right'},'2':{'1':'right_to_left'}}}))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(events))
    monkeypatch.setenv('FOOTBALLIQ_DIRECTION_METADATA',str(meta))
    assert client.get('/api/v1/heatmap/direction-status?team_id=1&opponent_id=2').json()['available'] is True
    assert client.get('/api/v1/heatmap/direction-status?team_id=1&opponent_id=3').json()['available'] is False

def test_direction_status_same_team_rejected():
    assert client.get('/api/v1/heatmap/direction-status?team_id=1&opponent_id=1').status_code == 422
