import json
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def test_not_configured(monkeypatch):
    monkeypatch.delenv('FOOTBALLIQ_HISTORICAL_EVENTS',raising=False)
    data=client.get('/api/v1/data-quality/historical-events').json()
    assert data['status']=='not_configured' and data['match_identity_verified'] is False

def test_valid_local_file_does_not_claim_identity(monkeypatch,tmp_path):
    f=tmp_path/'events.json'
    f.write_text(json.dumps([{'id':str(uuid4()),'team':{'id':217,'name':'Barcelona'},'type':{'name':'Pass'},'location':[30,40]}]))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(f))
    data=client.get('/api/v1/data-quality/historical-events').json()
    assert data['status']=='structurally_valid' and data['events']==1 and not data['match_identity_verified']
    assert len(data['sha256'])==64

def test_invalid_file_rejected(monkeypatch,tmp_path):
    f=tmp_path/'events.json';f.write_text('{bad')
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(f))
    data=client.get('/api/v1/data-quality/historical-events').json()
    assert data['status']=='rejected' and not data['match_identity_verified']
