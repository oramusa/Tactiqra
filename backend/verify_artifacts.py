"""Check source integrity and review CSV consistency; does not certify tactics."""
import argparse
import csv
import hashlib
import json
import tempfile
from pathlib import Path
from review_export import export_review

def verify(events_path: Path, results_dir: Path):
    manifest=json.loads((results_dir/'source_manifest.json').read_text())
    source=events_path.read_bytes()
    digest=hashlib.sha256(source).hexdigest()
    if manifest.get('source_sha256')!=digest or manifest.get('source_bytes')!=len(source):
        raise ValueError('Source checksum/size mismatch')
    events=json.loads(source)
    if not isinstance(events,list) or len(events)!=manifest.get('source_event_count'):
        raise ValueError('Source event count mismatch')
    report_path=results_dir/'pilot_report.json'
    report=json.loads(report_path.read_text())
    if str(report.get('match_id'))!=str(manifest.get('match_id')):
        raise ValueError('Report match ID mismatch')
    if report.get('event_count')!=len(events):
        raise ValueError('Report event count mismatch')
    # Every claimed evidence event must exist in the original provider file.
    # This is an identity check, not an assertion of tactical correctness.
    source_ids = {str(e['id']) for e in events if isinstance(e, dict) and e.get('id') is not None}
    if len(source_ids) != len(events):
        raise ValueError('Source event IDs missing or duplicated')
    prefix = f"statsbomb:{manifest['match_id']}:"
    for transition in report.get('transitions', []):
        if not isinstance(transition, dict):
            raise ValueError('Invalid transition record')
        start = str(transition.get('start_event_id', '')).removeprefix(prefix)
        evidence = transition.get('evidence_event_ids')
        if start not in source_ids or not isinstance(evidence, list) or not evidence:
            raise ValueError('Transition start/evidence missing from source')
        if start not in {str(v).removeprefix(prefix) for v in evidence}:
            raise ValueError('Transition start not included in evidence')
        if any(str(v).removeprefix(prefix) not in source_ids for v in evidence):
            raise ValueError('Evidence references unknown source event')
    with tempfile.TemporaryDirectory() as temp:
        expected=Path(temp)/'review.csv'
        count=export_review(report_path,expected,limit=10)
        with expected.open(newline='') as f:
            expected_rows=list(csv.DictReader(f))
        with (results_dir/'manual_review.csv').open(newline='') as f:
            actual_rows=list(csv.DictReader(f))
        if expected_rows!=actual_rows or count!=manifest.get('review_rows_exported'):
            raise ValueError('Review CSV does not match report')
    return {'status':'verified_bundle_integrity_only','match_id':str(manifest['match_id']),
            'source_sha256':digest,'review_rows':count,'tactical_accuracy_measured':False}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--events',type=Path,required=True)
    p.add_argument('--results-dir',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(verify(args.events,args.results_dir),indent=2))
