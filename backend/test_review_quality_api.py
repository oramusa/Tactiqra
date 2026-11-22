import json
from fastapi.testclient import TestClient
from app.main import app

def setup(monkeypatch,tmp_path,quality):
    report=tmp_path/'pilot.json'
    report.write_text(json.dumps({'match_id':'m1','event_count':100,'transitions':[
        {'start_event_id':str(i),'verification_status':'provisional','evidence_event_ids':[str(i)]} for i in range(10)]}))
    monkeypatch.setenv('FOOTBALLIQ_PILOT_REPORT',str(report))
    if quality is None:
        monkeypatch.delenv('FOOTBALLIQ_REVIEW_QUALITY',raising=False)
    else:
        p=tmp_path/'quality.json';p.write_text(json.dumps(quality))
        monkeypatch.setenv('FOOTBALLIQ_REVIEW_QUALITY',str(p))

def test_missing_review_never_claims_precision(monkeypatch,tmp_path):
    setup(monkeypatch,tmp_path,None)
    with TestClient(app) as c:
        x=c.get('/api/v1/evidence/review-quality').json()
        assert x['status']=='review_not_submitted' and x['sample_precision'] is None

def test_reviewed_sample(monkeypatch,tmp_path):
    setup(monkeypatch,tmp_path,{'match_id':'m1','reviewed_count':10,'correct_count':8,
        'false_positive_count':2,'uncertain_count':0,'sample_precision_denominator':10,
        'sample_precision':0.8,'recall_measured':False,'independent_full_match_accuracy_measured':False})
    with TestClient(app) as c:
        x=c.get('/api/v1/evidence/review-quality').json()
        assert x['sample_precision']==0.8 and x['status']=='sample_review_complete'
        assert x['recall_measured'] is False

def test_wrong_match_is_rejected(monkeypatch,tmp_path):
    setup(monkeypatch,tmp_path,{'match_id':'different'})
    with TestClient(app) as c:
        assert c.get('/api/v1/evidence/review-quality').status_code==503

def test_inconsistent_counts_are_rejected(monkeypatch,tmp_path):
    setup(monkeypatch,tmp_path,{'match_id':'m1','reviewed_count':10,'correct_count':9,
        'false_positive_count':2,'uncertain_count':0,'sample_precision_denominator':10,
        'sample_precision':0.9,'recall_measured':False,'independent_full_match_accuracy_measured':False})
    with TestClient(app) as c:
        assert c.get('/api/v1/evidence/review-quality').status_code==503
