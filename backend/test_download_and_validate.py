import json
import pytest
from download_and_validate import download_match, execute
from test_local_pipeline import sample_event

class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.headers = {'Content-Length': str(len(data))}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size): return self.data[:size]

def opener(data):
    def f(request, timeout): return FakeResponse(data)
    return f

def test_invalid_match_id(tmp_path):
    with pytest.raises(ValueError, match='digits only'):
        download_match('../secret', tmp_path/'x', opener(b'[]'))

def test_invalid_json_does_not_write_file(tmp_path):
    target=tmp_path/'x.json'
    with pytest.raises(json.JSONDecodeError):
        download_match('3773386',target,opener(b'broken'))
    assert not target.exists()

def test_full_pipeline_with_mock_source(tmp_path):
    data=json.dumps([sample_event(1,1,1,'Half Start'),sample_event(2,1,1),
                     sample_event(3,2,2,'Interception'),sample_event(4,2,2,'Shot')]).encode()
    result=execute('3773386',tmp_path,opener(data))
    assert result['integrity']['status']=='verified_bundle_integrity_only'
    assert result['manual_review_complete'] is False
    assert (tmp_path/'results'/'manual_review.csv').exists()

def test_oversized_source_is_rejected(tmp_path):
    class TooLarge(FakeResponse):
        def __init__(self):
            self.headers={'Content-Length':'30000001'}
    with pytest.raises(ValueError,match='30 MB'):
        download_match('3773386',tmp_path/'x',lambda req,timeout: TooLarge())
