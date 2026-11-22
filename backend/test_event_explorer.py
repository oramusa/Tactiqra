from app import event_explorer_api as api

def test_unconfigured(monkeypatch):
    monkeypatch.setattr(api, 'load_events', lambda: None)
    assert api.explore_events(team_id=None, event_type=None, period=None, cursor=0, limit=25)['status'] == 'insufficient_data'

def test_pagination_and_filter(monkeypatch):
    events = [{'id': str(i), 'team': {'id': 1 if i % 2 else 2, 'name': 'T'}, 'type': {'name': 'Pass'}, 'period': 1, 'minute': i, 'location': [10, 20]} for i in range(9)]
    monkeypatch.setattr(api, 'load_events', lambda: events)
    first = api.explore_events(team_id=1, event_type='Pass', period=1, cursor=0, limit=2)
    assert [x['event_id'] for x in first['items']] == ['1', '3']
    second = api.explore_events(team_id=1, event_type='Pass', period=1, cursor=first['next_cursor'], limit=2)
    assert [x['event_id'] for x in second['items']] == ['5', '7']
    assert second['next_cursor'] is None

def test_safe_location(monkeypatch):
    monkeypatch.setattr(api, 'load_events', lambda: [{'id':'x','team':{'id':1},'type':{'name':'Shot'},'location':['bad', 1]}])
    result = api.explore_events(team_id=None, event_type=None, period=None, cursor=0, limit=10)
    assert result['items'][0]['location'] is None
