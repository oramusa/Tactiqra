import hashlib
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.event_coverage_api import audit_manifest

def test_verified_and_missing(tmp_path):
    payload = b'[{"id":"abc"}]'
    (tmp_path/'events.json').write_bytes(payload)
    (tmp_path/'manifest.json').write_text(json.dumps({'matches':[{'provider_match_id':11,'event_source':'StatsBomb open data','relative_path':'events.json','sha256':hashlib.sha256(payload).hexdigest()}]}))
    result = audit_manifest([11,12], tmp_path/'manifest.json')
    assert result['verifiedFiles']==1 and result['missingOrInvalid']==1
    assert result['matches'][1]['status']=='missing'

def test_reject_traversal(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({'matches':[{'provider_match_id':1,'event_source':'test','relative_path':'../secret','sha256':'0'*64}]}))
    assert audit_manifest([1],tmp_path/'manifest.json')['matches'][0]['status']=='invalid'

def test_reject_checksum(tmp_path):
    (tmp_path/'events.json').write_text('[]')
    (tmp_path/'manifest.json').write_text(json.dumps({'matches':[{'provider_match_id':1,'event_source':'test','relative_path':'events.json','sha256':'0'*64}]}))
    assert audit_manifest([1],tmp_path/'manifest.json')['verifiedFiles']==0

def test_missing_configuration(monkeypatch):
    monkeypatch.delenv('FOOTBALLIQ_EVENT_MANIFEST',raising=False)
    response=TestClient(app).get('/api/v1/opponentiq/event-coverage',params={'match_ids':'1,2'})
    assert response.status_code==200 and response.json()['status']=='not_configured'

def test_bad_ids():
    assert TestClient(app).get('/api/v1/opponentiq/event-coverage',params={'match_ids':'1,no'}).status_code==422
