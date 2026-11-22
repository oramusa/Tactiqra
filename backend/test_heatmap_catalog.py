import json
from fastapi.testclient import TestClient
from app.main import app

def test_catalog_without_source(monkeypatch):
    monkeypatch.delenv('FOOTBALLIQ_HISTORICAL_EVENTS', raising=False)
    with TestClient(app) as c:
        data=c.get('/api/v1/heatmap/catalog').json()
    assert data['status']=='insufficient_data' and data['teams']==[]

def test_catalog_team_player_event_types(monkeypatch,tmp_path):
    raw=[{'id':'1','team':{'id':2,'name':'Away'},'player':{'id':20,'name':'B'},'type':{'name':'Pass'}},
         {'id':'2','team':{'id':1,'name':'Home'},'player':{'id':10,'name':'A'},'type':{'name':'Shot'}},
         {'id':'3','team':{'id':1,'name':'Home'},'player':{'id':11,'name':'C'},'type':{'name':'Pass'}}]
    path=tmp_path/'events.json';path.write_text(json.dumps(raw));monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(path))
    with TestClient(app) as c:
        response=c.get('/api/v1/heatmap/catalog')
    assert response.status_code==200
    data=response.json()
    assert [t['name'] for t in data['teams']]==['Away','Home']
    assert [p['name'] for p in data['teams'][1]['players']]==['A','C']
    assert data['event_types']==['Pass','Shot']

def test_catalog_ignores_malformed_team(monkeypatch,tmp_path):
    path=tmp_path/'events.json';path.write_text(json.dumps([{'team':{'id':'wrong'},'type':{'name':'Pass'}},None]))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(path))
    with TestClient(app) as c:
        data=c.get('/api/v1/heatmap/catalog').json()
    assert data['teams']==[] and data['status']=='insufficient_data'
