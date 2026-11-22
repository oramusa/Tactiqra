import csv
import io
import json
import hashlib
import pytest
from local_pipeline import run_pipeline
from fastapi.testclient import TestClient
from app.main import app


def sample_event(i, team=1, possession=1, typ='Pass'):
    return {'id':f'event-{i}', 'index':i, 'period':1,
            'timestamp':f'00:00:{i:02d}.000', 'type':{'name':typ},
            'team':{'id':team}, 'possession':possession,
            'possession_team':{'id':team}}


def test_end_to_end_offline_pipeline(tmp_path, monkeypatch):
    events=[sample_event(1, 1, 1, 'Half Start'),sample_event(2,1,1),
            sample_event(3,2,2,'Interception'),sample_event(4,2,2,'Carry'),
            sample_event(5,2,2,'Shot')]
    raw=tmp_path/'events.json'
    raw.write_text(json.dumps(events),encoding='utf-8')
    out=tmp_path/'results'
    result=run_pipeline(raw,out,'test-match')
    manifest=json.loads((out/'source_manifest.json').read_text())
    assert manifest['source_sha256']==hashlib.sha256(raw.read_bytes()).hexdigest()
    assert manifest['manual_review_completed'] is False
    report=json.loads((out/'pilot_report.json').read_text())
    assert report['event_count']==5
    with (out/'manual_review.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==result['review_rows']
    monkeypatch.setenv('FOOTBALLIQ_PILOT_REPORT',str(out/'pilot_report.json'))
    with TestClient(app) as client:
        assert client.get('/api/v1/evidence/summary').status_code==200
        assert client.get('/api/v1/evidence/transitions').status_code==200
        response=client.get('/api/v1/evidence/review-export')
        assert response.status_code==200
        online=list(csv.DictReader(io.StringIO(response.text)))
        assert online==rows  # Offline and API review sheets must select identical candidates



def test_invalid_input_writes_no_report(tmp_path):
    raw=tmp_path/'events.json';raw.write_text('[]')
    with pytest.raises(ValueError):
        run_pipeline(raw,tmp_path/'out','x')
    assert not (tmp_path/'out'/'pilot_report.json').exists()
