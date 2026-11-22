import json
from uuid import uuid4
from real_match_preflight import inspect_file

def event(team='Barcelona', eid=None, loc=None):
    return {'id': str(eid or uuid4()), 'team': {'id': 217, 'name': team}, 'type': {'name': 'Pass'}, 'location': loc or [60, 40]}

def test_valid_file(tmp_path):
    p = tmp_path / 'events.json'
    p.write_text(json.dumps([event(), event('Deportivo Alavés')]))
    result = inspect_file(p)
    assert result['status'] == 'structurally_valid'
    assert result['identity_status'].startswith('unverified')
    assert result['events'] == 2

def test_duplicate_rejected(tmp_path):
    p = tmp_path / 'events.json'
    id_ = uuid4()
    p.write_text(json.dumps([event(eid=id_), event(eid=id_)]))
    assert inspect_file(p)['failures']['duplicate_id'] == 1

def test_invalid_coordinate_rejected(tmp_path):
    p = tmp_path / 'events.json'
    p.write_text(json.dumps([event(loc=[121, 30])]))
    assert inspect_file(p)['status'] == 'rejected'

def test_wrong_team_rejected(tmp_path):
    p = tmp_path / 'events.json'
    p.write_text(json.dumps([event('Unexpected')]))
    assert inspect_file(p, expected_teams=['Barcelona', 'Deportivo Alavés'])['status'] == 'rejected'
