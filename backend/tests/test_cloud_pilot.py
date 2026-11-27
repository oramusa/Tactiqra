"""Cloud pilot loader regression tests; no live network required."""
import io
import json
import pytest
from fastapi import HTTPException
from app import heatmap_api as api

@pytest.fixture(autouse=True)
def clear_cache():
    api.load_remote_pilot.cache_clear()
    yield
    api.load_remote_pilot.cache_clear()

def test_opt_in_and_cache(monkeypatch):
    monkeypatch.delenv('FOOTBALLIQ_HISTORICAL_EVENTS', raising=False)
    monkeypatch.delenv('FOOTBALLIQ_STATSBOMB_PILOT', raising=False)
    assert api.load_events() is None
    calls = []
    data = [{'id': 'example', 'shot': {'statsbomb_xg': 0.9761923}}]
    def fetch(url, timeout):
        calls.append(url)
        return io.BytesIO(json.dumps(data).encode())
    monkeypatch.setattr(api, 'urlopen', fetch)
    monkeypatch.setenv('FOOTBALLIQ_STATSBOMB_PILOT', '3773386')
    assert api.load_events() == data
    assert api.load_events() == data
    assert calls == [api.PILOT_URL]

def test_local_source_takes_precedence(monkeypatch, tmp_path):
    source = tmp_path / 'events.json'
    source.write_text('[{"id":"local"}]')
    monkeypatch.setenv('FOOTBALLIQ_HISTORICAL_EVENTS', str(source))
    monkeypatch.setenv('FOOTBALLIQ_STATSBOMB_PILOT', '3773386')
    assert api.load_events() == [{'id': 'local'}]

@pytest.mark.parametrize('payload', [b'not json', b'{}', b'[]'])
def test_invalid_source(monkeypatch, payload):
    monkeypatch.setattr(api, 'urlopen', lambda *a, **kw: io.BytesIO(payload))
    with pytest.raises(HTTPException) as error:
        api.load_remote_pilot()
    assert error.value.status_code == 503
