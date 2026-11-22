import csv
import json
import pytest
from review_gate import evaluate

def fixture(tmp_path, decisions):
    report = tmp_path / 'report.json'
    report.write_text(json.dumps({'match_id':'m1','transitions':[{'start_event_id':'e1'},{'start_event_id':'e2'}]}))
    review = tmp_path / 'review.csv'
    with review.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['match_id','start_event_id','review_decision','review_notes'])
        w.writeheader()
        for i,d in enumerate(decisions,1):
            w.writerow({'match_id':'m1','start_event_id':f'e{i}','review_decision':d,'review_notes':'Compared to original event sequence'})
    return report,review

def test_no_review_is_not_accuracy(tmp_path):
    r,c=fixture(tmp_path,[])
    out=evaluate(r,c)
    assert out['sample_precision'] is None and out['recall_measured'] is False
    assert out['status']=='review_incomplete'

def test_sample_precision_is_not_recall(tmp_path):
    r,c=fixture(tmp_path,['correct','false_positive'])
    out=evaluate(r,c,min_reviews=2)
    assert out['sample_precision']==0.5
    assert out['review_target_met'] is True
    assert out['independent_full_match_accuracy_measured'] is False

def test_invalid_decision_rejected(tmp_path):
    r,c=fixture(tmp_path,['verified'])
    with pytest.raises(ValueError): evaluate(r,c)

def test_duplicate_rejected(tmp_path):
    r,c=fixture(tmp_path,['correct'])
    with c.open('a') as f: f.write('m1,e1,correct,again\n')
    with pytest.raises(ValueError): evaluate(r,c)
