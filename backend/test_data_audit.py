import json
from data_audit import audit_events


def test_clean_structure_does_not_claim_identity(tmp_path):
    p = tmp_path / '3773386.json'
    p.write_text(json.dumps([{'id': 'e1', 'type': {'name': 'Pass'}, 'location': [120, 80]},
                             {'id': 'e2', 'type': {'name': 'Shot'}}]))
    result = audit_events(p, 3773386)
    assert result['status'] == 'structure_only_pass'
    assert result['identityVerified'] is False
    assert result['eventTypes'] == {'Pass': 1, 'Shot': 1}


def test_duplicates_missing_ids_and_bad_locations(tmp_path):
    p = tmp_path / 'a.json'
    p.write_text(json.dumps([{'id': 'x', 'location': [121, 3]},
                             {'id': 'x', 'location': [2, 3]},
                             {'type': {'name': 'Pass'}}]))
    r = audit_events(p)
    assert r['duplicateEventIds'] == 1
    assert r['missingEventIds'] == 1
    assert r['invalidLocations'] == 1
    assert r['status'] == 'needs_review'


def test_mismatched_filename_not_verified(tmp_path):
    p = tmp_path / 'other.json'
    p.write_text('[]')
    r = audit_events(p, 3773386)
    assert 'filename_match_id_mismatch_unverified_identity' in r['issues']
    assert 'empty_event_file' in r['issues']
