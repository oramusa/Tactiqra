from fastapi.testclient import TestClient
from app.main import app
from app.match_event_report_api import summarize_events
import json

client=TestClient(app)

def test_no_source(monkeypatch):
    monkeypatch.delenv('FOOTBALLIQ_HISTORICAL_EVENTS',raising=False)
    assert client.get('/api/v1/opponentiq/historical-event-report').json()['status']=='not_configured'

def test_report_from_local_file(monkeypatch,tmp_path):
    sample=[{'id':'1','team':{'id':1,'name':'Barcelona'},'type':{'name':'Pass'},'location':[40,30],'pass':{}},
            {'id':'2','team':{'id':1,'name':'Barcelona'},'type':{'name':'Pass'},'pass':{'outcome':{'name':'Incomplete'}}},
            {'id':'3','team':{'id':2,'name':'Alavés'},'type':{'name':'Shot'},'shot':{'outcome':{'name':'Goal'}}}]
    f=tmp_path/'events.json';f.write_text(json.dumps(sample))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(f))
    result=client.get('/api/v1/opponentiq/historical-event-report')
    assert result.status_code==200
    data=result.json()
    assert data['match_identity_verified'] is False
    barca=next(t for t in data['teams'] if t['team_id']==1)
    assert barca['passes']==2 and barca['completed_passes']==1 and barca['pass_completion_pct']==50.0
    assert next(t for t in data['teams'] if t['team_id']==2)['goals_from_shots']==1

def test_empty_events_are_not_ready():
    assert summarize_events([])['status']=='insufficient_data'

def test_malformed_rows_are_skipped():
    data=summarize_events([None,{'team':{'id':1},'type':None}])
    assert data['skipped_events']==2 and not data['teams']
