import hashlib
import json
from fastapi.testclient import TestClient
from app.main import app
from app.tactical_batch_api import aggregate_reports


def fixture(tmp_path, team=7, report_id=990):
    report = {'match_id': report_id, 'event_count': 30, 'transitions': [
        {'match_id': report_id, 'verification_status': 'provisional', 'shot': True,
         'goal': False, 'evidence_event_ids': ['a']},
        {'match_id': report_id, 'verification_status': 'needs_review', 'shot': False,
         'goal': False, 'evidence_event_ids': ['b']} ]}
    raw = json.dumps(report).encode()
    (tmp_path / 'report.json').write_bytes(raw)
    entry = {'provider_match_id': 11, 'event_match_id': report_id, 'team_id': team,
             'relative_path': 'report.json', 'sha256': hashlib.sha256(raw).hexdigest()}
    (tmp_path / 'manifest.json').write_text(json.dumps({'reports': [entry]}))
    return entry, tmp_path / 'manifest.json'


def test_partial_coverage_and_denominator(tmp_path):
    _, manifest = fixture(tmp_path)
    result = aggregate_reports(7, [11, 12, 13], manifest)
    assert result['analyzedMatches'] == 1 and result['coverageRatio'] == 0.3333
    assert result['perAnalyzedMatch']['transitions'] == 2
    assert result['matches'][1]['status'] == 'missing'


def test_team_mismatch_rejected(tmp_path):
    _, manifest = fixture(tmp_path)
    assert aggregate_reports(8, [11], manifest)['analyzedMatches'] == 0


def test_checksum_tamper_rejected(tmp_path):
    _, manifest = fixture(tmp_path)
    (tmp_path / 'report.json').write_text('{}')
    assert aggregate_reports(7, [11], manifest)['matches'][0]['status'] == 'invalid'


def test_duplicate_mapping_rejected(tmp_path):
    entry, manifest = fixture(tmp_path)
    manifest.write_text(json.dumps({'reports': [entry, entry]}))
    assert aggregate_reports(7, [11], manifest)['analyzedMatches'] == 0


def test_no_configuration_and_bad_input(monkeypatch):
    monkeypatch.delenv('FOOTBALLIQ_TACTICAL_REPORT_MANIFEST', raising=False)
    client = TestClient(app)
    assert client.get('/api/v1/opponentiq/tactical-batch', params={'team_id': 7, 'match_ids': '11'}).json()['status'] == 'not_configured'
    assert client.get('/api/v1/opponentiq/tactical-batch', params={'team_id': 7, 'match_ids': '11,11'}).status_code == 422
