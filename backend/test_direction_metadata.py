import hashlib, json
import pytest
from fastapi import HTTPException
from direction_metadata import load_verified_directions, DirectionMetadataError
from app import heatmap_api

@pytest.fixture
def source(tmp_path):
    events = tmp_path/'events.json'
    events.write_text(json.dumps([{'id':'a','team':{'id':1},'type':{'name':'Pass'},'period':1,'location':[10,20]}, {'id':'b','team':{'id':1},'type':{'name':'Pass'},'period':2,'location':[110,60]}]))
    metadata = tmp_path/'directions.json'
    data = {'verification_status':'manually_verified', 'evidence_note':'Reviewed independently against video', 'source_sha256':hashlib.sha256(events.read_bytes()).hexdigest(), 'teams':{'1':{'1':'left_to_right','2':'right_to_left'}}}
    metadata.write_text(json.dumps(data))
    return events,metadata,data

def test_verified_source_bound_directions(source):
    events, metadata, _ = source
    directions, provenance = load_verified_directions(metadata, events, 1)
    assert directions == {1:'left_to_right',2:'right_to_left'}
    assert provenance['verification_status'] == 'manually_verified'

def test_changed_source_rejected(source):
    events, metadata, _ = source
    events.write_text(events.read_text()+' ')
    with pytest.raises(DirectionMetadataError,match='checksum'):
        load_verified_directions(metadata,events,1)

def test_unverified_or_missing_team_rejected(source):
    events, metadata, data = source
    data['verification_status']='unverified'
    metadata.write_text(json.dumps(data))
    with pytest.raises(DirectionMetadataError,match='manually verified'):
        load_verified_directions(metadata,events,1)
    data['verification_status']='manually_verified'
    metadata.write_text(json.dumps(data))
    with pytest.raises(DirectionMetadataError,match='selected team'):
        load_verified_directions(metadata,events,2)

def test_normalized_api_requires_metadata(monkeypatch,source):
    events, metadata, _ = source
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(events))
    monkeypatch.delenv('FOOTBALLIQ_DIRECTION_METADATA',raising=False)
    with pytest.raises(HTTPException,match='Verified direction metadata not configured'):
        heatmap_api.events_heatmap(team_id=1, player_id=None, event_type=None, period=None, columns=12, rows=8, normalize=True)

def test_normalized_api_uses_metadata(monkeypatch,source):
    events, metadata, _ = source
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS',str(events))
    monkeypatch.setenv('FOOTBALLIQ_DIRECTION_METADATA',str(metadata))
    result = heatmap_api.events_heatmap(team_id=1, player_id=None, event_type=None, period=None, columns=12, rows=8, normalize=True)
    assert result['direction_normalized'] is True
    assert result['grid'][2][1] == 2
    assert result['direction_provenance']['source_sha256']
