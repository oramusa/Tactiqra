import json
import pytest
from local_pipeline import run_pipeline
from verify_artifacts import verify
from test_local_pipeline import sample_event

def test_verify_and_source_tampering(tmp_path):
    raw=tmp_path/'events.json'
    events=[sample_event(1,1,1,'Half Start'),sample_event(2,1,1),sample_event(3,2,2,'Interception'),sample_event(4,2,2,'Shot')]
    raw.write_text(json.dumps(events))
    out=tmp_path/'out'
    run_pipeline(raw,out,'m1')
    assert verify(raw,out)['status']=='verified_bundle_integrity_only'
    raw.write_text(json.dumps(events+[sample_event(5,2,2,'Carry')]))
    with pytest.raises(ValueError,match='Source checksum'):
        verify(raw,out)

def test_csv_tampering(tmp_path):
    raw=tmp_path/'events.json'
    raw.write_text(json.dumps([sample_event(1,1,1,'Half Start'),sample_event(2,2,2,'Interception')]))
    out=tmp_path/'out'
    run_pipeline(raw,out,'m2')
    f=out/'manual_review.csv'
    f.write_text(f.read_text()+'tampered,line\n')
    with pytest.raises(ValueError,match='Review CSV'):
        verify(raw,out)

def test_wrong_report_match(tmp_path):
    raw=tmp_path/'events.json'
    raw.write_text(json.dumps([sample_event(1,1,1,'Half Start')]))
    out=tmp_path/'out'
    run_pipeline(raw,out,'m3')
    f=out/'pilot_report.json'
    data=json.loads(f.read_text());data['match_id']='other';f.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='Report match ID'):
        verify(raw,out)


def test_reject_unknown_evidence_reference(tmp_path):
    raw=tmp_path/'events.json'
    raw.write_text(json.dumps([sample_event(1,1,1,'Half Start'),sample_event(2,2,2,'Interception')]))
    out=tmp_path/'out'; run_pipeline(raw,out,'m4')
    report_path=out/'pilot_report.json'
    report=json.loads(report_path.read_text())
    report['transitions']=[{'start_event_id':'statsbomb:m4:event-1','evidence_event_ids':['statsbomb:m4:event-1','not-in-source']}]
    report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='unknown source event'):
        verify(raw,out)

def test_reject_missing_start_evidence(tmp_path):
    raw=tmp_path/'events.json'
    raw.write_text(json.dumps([sample_event(1,1,1,'Half Start'),sample_event(2,2,2,'Interception')]))
    out=tmp_path/'out'; run_pipeline(raw,out,'m5')
    report_path=out/'pilot_report.json'
    report=json.loads(report_path.read_text())
    report['transitions']=[{'start_event_id':'statsbomb:m5:event-1','evidence_event_ids':['statsbomb:m5:event-2']}]
    report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='start not included'):
        verify(raw,out)
