from fastapi.testclient import TestClient
from app.main import app
from app.possession_sequence_api import summarize_possessions
import json

client = TestClient(app)

def event(i, possession, team, kind, goal=False):
    return {'id': str(i), 'possession': possession, 'possession_team': {'id': team, 'name': str(team)},
            'team': {'id': team}, 'type': {'name': kind}, 'shot': {'outcome': {'name': 'Goal' if goal else 'Saved'}} if kind == 'Shot' else {}}

def test_counts_unique_possessions_and_shots():
    rows = [event(1,1,2,'Pass'), event(2,1,2,'Shot'), event(3,1,2,'Shot',True), event(4,2,2,'Pass'), event(5,3,1,'Shot')]
    r = summarize_possessions(rows)
    a = next(x for x in r['teams'] if x['team_id'] == 2)
    assert (a['possessions'],a['possessions_with_shot'],a['possessions_with_goal_shot']) == (2,1,1)
    assert a['examples'][0]['shot_event_ids'] == ['2','3']
    assert r['match_identity_verified'] is False

def test_missing_possession_does_not_guess():
    r = summarize_possessions([{'type':{'name':'Shot'}}, None])
    assert r['status'] == 'insufficient_data' and r['ignored_events'] == 2

def test_missing_source(monkeypatch):
    monkeypatch.delenv('FOOTBALLIQ_HISTORICAL_EVENTS', raising=False)
    assert client.get('/api/v1/opponentiq/possession-sequences').json()['status'] == 'not_configured'

def test_local_fixture(monkeypatch,tmp_path):
    f=tmp_path/'events.json'; f.write_text(json.dumps([event(1,1,3,'Shot')]))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(f))
    r=client.get('/api/v1/opponentiq/possession-sequences').json()
    assert r['teams'][0]['possessions_with_shot'] == 1
    assert r['status'] == 'provisional'

def test_limits_examples():
    r=summarize_possessions([event(1,1,2,'Shot'),event(2,2,2,'Shot')],max_examples=1)
    assert len(r['teams'][0]['examples'])==1
