import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from heatmap_compare import compare_heatmaps
from test_heatmap import event

def test_delta_and_evidence():
    events=[event('a',1,11,0,0),event('b',1,11,0,0),event('c',2,22,120,80)]
    r=compare_heatmaps(events,team_a=1,team_b=2)
    assert r['delta_total']==1
    assert r['delta_grid'][0][0]==2 and r['delta_grid'][-1][-1]==-1
    assert r['team_a']['evidence'][0]['event_ids']==['a','b']
    assert sum(map(sum,r['delta_grid']))==1

def test_no_fabricated_comparison():
    r=compare_heatmaps([event('a',1,11,0,0)],team_a=1,team_b=2)
    assert r['status']=='insufficient_data'
    assert r['team_b']['plotted_events']==0

def test_same_team_rejected():
    with pytest.raises(ValueError,match='distinct'):
        compare_heatmaps([],team_a=1,team_b=1)

def test_api_compare_and_invalid(monkeypatch,tmp_path):
    source=tmp_path/'events.json'
    source.write_text(json.dumps([event('a',1,11,0,0),event('b',2,22,120,80)]))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(source))
    with TestClient(app) as c:
        r=c.get('/api/v1/heatmap/compare?team_a=1&team_b=2')
        assert r.status_code==200 and r.json()['delta_total']==0
        assert c.get('/api/v1/heatmap/compare?team_a=1&team_b=1').status_code==422
        assert c.get('/api/v1/heatmap/compare?team_a=1&team_b=2&period=7').status_code==422

def test_period_applies_to_both():
    a=event('a',1,11,0,0);a['period']=1
    b=event('b',2,22,120,80);b['period']=2
    r=compare_heatmaps([a,b],team_a=1,team_b=2,period=1)
    assert r['team_a']['plotted_events']==1
    assert r['team_b']['plotted_events']==0
