import json
from fastapi.testclient import TestClient
from app.main import app
from app.transition_candidate_api import transition_candidates

client = TestClient(app)

def ev(i,p,kind,t,team=1,period=1):
    return {'id':str(i),'possession':p,'possession_team':{'id':team,'name':'Team'},
            'team':{'id':team},'type':{'name':kind},'timestamp':f'00:00:{t:02d}.000','period':period}

def test_fast_recovery_shot_candidate():
    r=transition_candidates([ev(1,1,'Ball Recovery',2),ev(2,1,'Pass',5),ev(3,1,'Shot',12)])
    assert r['teams'][0]['candidates']==1
    assert r['teams'][0]['examples'][0]['duration_seconds']==10
    assert r['match_identity_verified'] is False

def test_shot_without_recovery_is_not_counterattack():
    r=transition_candidates([ev(1,1,'Pass',1),ev(2,1,'Shot',5)])
    assert r['teams'][0]['candidates']==0

def test_slow_recovery_excluded():
    r=transition_candidates([ev(1,1,'Interception',1),ev(2,1,'Shot',40)])
    assert r['teams'][0]['candidates']==0

def test_missing_timestamps_excluded():
    a=ev(1,1,'Ball Recovery',1); b=ev(2,1,'Shot',5); b.pop('timestamp')
    r=transition_candidates([a,b])
    assert r['teams'][0]['excluded_missing_evidence']==1

def test_cross_period_not_combined():
    r=transition_candidates([ev(1,1,'Ball Recovery',1),ev(2,1,'Shot',5,period=2)])
    assert r['teams'][0]['candidates']==0

def test_api_unconfigured(monkeypatch):
    monkeypatch.delenv('FOOTBALLIQ_HISTORICAL_EVENTS',raising=False)
    assert client.get('/api/v1/opponentiq/transition-candidates').json()['status']=='not_configured'

def test_api_local_fixture(monkeypatch,tmp_path):
    f=tmp_path/'match.json'; f.write_text(json.dumps([ev(1,1,'Ball Recovery',1),ev(2,1,'Shot',7)]))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(f))
    data=client.get('/api/v1/opponentiq/transition-candidates').json()
    assert data['teams'][0]['candidates']==1
