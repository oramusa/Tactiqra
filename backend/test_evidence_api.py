import json
from fastapi.testclient import TestClient
from app.main import app

def test_no_report(monkeypatch):
    monkeypatch.delenv("FOOTBALLIQ_PILOT_REPORT",raising=False)
    with TestClient(app) as c:
        assert c.get("/api/v1/evidence/summary").json()["status"]=="insufficient_data"
        assert c.get("/api/v1/evidence/transitions").json()["items"]==[]

def test_report(monkeypatch,tmp_path):
    p=tmp_path/"report.json"
    p.write_text(json.dumps({"match_id":"historical","event_count":12,"transitions":[{"start_event_id":"evt1","evidence_event_ids":["evt1"],"verification_status":"provisional_verified"}]}))
    monkeypatch.setenv("FOOTBALLIQ_PILOT_REPORT",str(p))
    with TestClient(app) as c:
        assert c.get("/api/v1/evidence/summary").json()["transition_count"]==1
        assert c.get("/api/v1/evidence/transitions").json()["items"][0]["evidence_event_ids"]==["evt1"]
        assert c.get("/api/v1/evidence/transitions?limit=101").status_code==422

def test_invalid_report(monkeypatch,tmp_path):
    p=tmp_path/"report.json";p.write_text("{")
    monkeypatch.setenv("FOOTBALLIQ_PILOT_REPORT",str(p))
    with TestClient(app) as c:
        assert c.get("/api/v1/evidence/summary").status_code==503

def test_reject_invalid_evidence_ids(monkeypatch,tmp_path):
    p=tmp_path/"bad.json"
    p.write_text(json.dumps({"transitions":[{"evidence_event_ids":"not a list"}]}))
    monkeypatch.setenv("FOOTBALLIQ_PILOT_REPORT",str(p))
    with TestClient(app) as c:
        assert c.get("/api/v1/evidence/transitions").status_code == 503

def test_reject_report_without_transition_array(monkeypatch,tmp_path):
    p=tmp_path/"bad.json"
    p.write_text(json.dumps({"transitions":{}}))
    monkeypatch.setenv("FOOTBALLIQ_PILOT_REPORT",str(p))
    with TestClient(app) as c:
        assert c.get("/api/v1/evidence/summary").status_code == 503


def test_cross_match_rejected(monkeypatch,tmp_path):
    p=tmp_path/"cross.json"
    p.write_text(json.dumps({"match_id":"a","event_count":10,"transitions":[{"match_id":"b","verification_status":"needs_review","evidence_event_ids":["e1"]}]}))
    monkeypatch.setenv("FOOTBALLIQ_PILOT_REPORT",str(p))
    with TestClient(app) as c:
        assert c.get("/api/v1/evidence/summary").status_code==503

def test_missing_provenance_rejected(monkeypatch,tmp_path):
    p=tmp_path/"missing.json"
    p.write_text(json.dumps({"event_count":10,"transitions":[]}))
    monkeypatch.setenv("FOOTBALLIQ_PILOT_REPORT",str(p))
    with TestClient(app) as c:
        assert c.get("/api/v1/evidence/summary").status_code==503


def test_actual_engine_provisional_status_is_accepted(monkeypatch,tmp_path):
    p=tmp_path/"report.json"
    p.write_text(json.dumps({"match_id":"3773386","event_count":120,
        "transitions":[{"match_id":"3773386","start_event_id":"e1",
                        "verification_status":"provisional","evidence_event_ids":["e1","e2"]}]}))
    monkeypatch.setenv("FOOTBALLIQ_PILOT_REPORT",str(p))
    with TestClient(app) as c:
        assert c.get("/api/v1/evidence/summary").status_code==200
        r=c.get("/api/v1/evidence/review-export")
        assert r.status_code==200
        assert "e1|e2" in r.text
        assert "reviewer_verdict" in r.text

def test_review_export_without_report(monkeypatch):
    monkeypatch.delenv("FOOTBALLIQ_PILOT_REPORT",raising=False)
    with TestClient(app) as c:
        assert c.get("/api/v1/evidence/review-export").status_code==404

def test_cross_match_rejected(monkeypatch,tmp_path):
    p=tmp_path/"report.json"
    p.write_text(json.dumps({"match_id":"A","event_count":1,
        "transitions":[{"match_id":"B","verification_status":"provisional",
                        "evidence_event_ids":["e1"]}]}))
    monkeypatch.setenv("FOOTBALLIQ_PILOT_REPORT",str(p))
    with TestClient(app) as c:
        assert c.get("/api/v1/evidence/summary").status_code==503
