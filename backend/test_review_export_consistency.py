import csv
import io
import json
from fastapi.testclient import TestClient
from app.main import app
from review_export import select_review_cases


def test_review_export_prioritizes_shots_and_is_stable(monkeypatch, tmp_path):
    rows = [
        {"match_id": "m", "start_event_id": f"e{i}", "period": 1,
         "verification_status": "provisional", "evidence_event_ids": [f"e{i}"],
         "shot": i == 9} for i in range(10)
    ]
    report={"match_id":"m", "event_count":100, "transitions":rows}
    p=tmp_path/'report.json';p.write_text(json.dumps(report))
    monkeypatch.setenv('FOOTBALLIQ_PILOT_REPORT',str(p))
    with TestClient(app) as c:
        result=c.get('/api/v1/evidence/review-export?limit=3')
        assert result.status_code==200
        actual=list(csv.DictReader(io.StringIO(result.text)))
        expected=select_review_cases(report,3)
        assert actual==[{k:str(v) for k,v in row.items()} for row in expected]
        assert actual[0]['start_event_id']=='e9'
        assert all(x['reviewer_verdict']=='' for x in actual)
        assert c.get('/api/v1/evidence/review-export?limit=101').status_code==422
