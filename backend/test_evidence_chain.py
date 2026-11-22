from app import evidence_chain_api as api
from fastapi import HTTPException
import hashlib
import json
import pytest

REPORT = {'match_id': 77, 'event_count': 2, 'transitions': [{'start_event_id':'a','evidence_event_ids':['a','b'], 'verification_status':'provisional'}]}
EVENTS = [{'id':i,'type':{'name':'Pass'},'team':{'name':'Team'},'location':[10,20]} for i in ('a','b')]

def setup(monkeypatch, tmp_path):
    path = tmp_path / 'events.json'
    path.write_text(json.dumps(EVENTS))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS', str(path))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS_SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
    identity = {'football_data': {'id': 100, 'homeTeam': {'id': 1}, 'awayTeam': {'id': 2}, 'utcDate': '2020-10-31T20:00:00Z', 'score': {'fullTime': {'home': 1, 'away': 0}}}, 'statsbomb': {'match_id': 77, 'home_team': {'home_team_id': 11}, 'away_team': {'away_team_id': 22}, 'kickoff_utc': '2020-10-31T20:00:00Z', 'home_score': 1, 'away_score': 0}, 'team_mapping': {'1': 11, '2': 22}}
    binding_path = tmp_path / 'identity.json'
    binding_path.write_text(json.dumps(identity))
    monkeypatch.setenv('FOOTBALLIQ_MATCH_IDENTITY_JSON', str(binding_path))
    monkeypatch.setattr(api,'load_report',lambda:REPORT)

def test_requires_explicit_match_binding(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.delenv('FOOTBALLIQ_HISTORICAL_MATCH_ID',raising=False)
    assert api.evidence_chain('a')['status']=='match_unverified'

def test_resolves_ordered_evidence(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID','77')
    result=api.evidence_chain('a')
    assert result['status']=='provisional'
    assert [x['event_id'] for x in result['items']]==['a','b']

def test_missing_event_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID','77')
    monkeypatch.setattr(api,'load_report',lambda:{**REPORT, 'event_count': 1})
    path = tmp_path / 'events.json'
    path.write_text(json.dumps(EVENTS[:1]))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS_SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
    assert api.evidence_chain('a')['status']=='incomplete_evidence'

def test_duplicate_event_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID','77')
    monkeypatch.setattr(api,'load_report',lambda:{**REPORT, 'event_count': 3})
    path = tmp_path / 'events.json'
    path.write_text(json.dumps(EVENTS + [EVENTS[0]]))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS_SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
    assert api.evidence_chain('a')['status']=='ambiguous_evidence'

def test_unknown_transition_404(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    with pytest.raises(HTTPException) as exc:
        api.evidence_chain('missing')
    assert exc.value.status_code==404

def test_wrong_source_hash_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS_SHA256', '0' * 64)
    assert api.evidence_chain('a')['status'] == 'source_mismatch'

def test_missing_hash_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    monkeypatch.delenv('FOOTBALLIQ_HISTORICAL_EVENTS_SHA256')
    assert api.evidence_chain('a')['status'] == 'source_unverified'

def test_wrong_event_count_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    monkeypatch.setattr(api, 'load_report', lambda: {**REPORT, 'event_count': 99})
    assert api.evidence_chain('a')['status'] == 'source_mismatch'


def test_missing_cross_provider_binding_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    monkeypatch.delenv('FOOTBALLIQ_MATCH_IDENTITY_JSON')
    assert api.evidence_chain('a')['status'] == 'identity_unverified'


def test_wrong_cross_provider_match_id_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    path = tmp_path / 'identity.json'
    data = json.loads(path.read_text())
    data['statsbomb']['match_id'] = 88
    path.write_text(json.dumps(data))
    assert api.evidence_chain('a')['status'] == 'identity_mismatch'


def test_cross_provider_score_conflict_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    path = tmp_path / 'identity.json'
    data = json.loads(path.read_text())
    data['statsbomb']['away_score'] = 2
    path.write_text(json.dumps(data))
    result = api.evidence_chain('a')
    assert result['status'] == 'identity_mismatch'
    assert 'score_mismatch' in result['reasons']


def test_source_bytes_not_separate_loader(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    # The endpoint must use the verified source file even if another loader is patched.
    monkeypatch.setattr(api, 'load_events', lambda: [{'id': 'forged'}], raising=False)
    result = api.evidence_chain('a')
    assert result['status'] == 'provisional'
    assert [item['event_id'] for item in result['items']] == ['a', 'b']

def test_verified_file_malformed_json_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    path = tmp_path / 'events.json'
    path.write_text('{not-json')
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS_SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
    assert api.evidence_chain('a')['status'] == 'source_unverified'

def test_verified_file_wrong_shape_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    path = tmp_path / 'events.json'
    path.write_text(json.dumps({'events': EVENTS}))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS_SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
    assert api.evidence_chain('a')['status'] == 'source_unverified'


def test_duplicate_unrelated_source_event_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    source_events = EVENTS + [{'id':'z'}, {'id':'z'}]
    path = tmp_path / 'events.json'
    path.write_text(json.dumps(source_events))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS_SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
    monkeypatch.setattr(api, 'load_report', lambda: {**REPORT, 'event_count': len(source_events)})
    assert api.evidence_chain('a')['status'] == 'ambiguous_source'


def test_missing_source_event_id_fails_closed(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    source_events = EVENTS + [{'type': {'name':'Pass'}}]
    path = tmp_path / 'events.json'
    path.write_text(json.dumps(source_events))
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS_SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
    monkeypatch.setattr(api, 'load_report', lambda: {**REPORT, 'event_count': len(source_events)})
    assert api.evidence_chain('a')['status'] == 'invalid_source'


def test_transition_start_must_be_first_evidence(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_MATCH_ID', '77')
    monkeypatch.setattr(api, 'load_report', lambda: {**REPORT, 'transitions': [{'start_event_id':'a','evidence_event_ids':['b','a'],'verification_status':'provisional'}]})
    assert api.evidence_chain('a')['status'] == 'invalid_evidence'
