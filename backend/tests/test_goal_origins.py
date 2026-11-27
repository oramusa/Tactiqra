"""Regression tests for the read-only OpponentIQ V1.6 goal origins endpoint."""
from app import event_explorer_api as api


def event(kind, event_id, team, player, possession=7, minute=30, second=0, **detail):
    result = {
        'id': event_id, 'type': {'name': kind},
        'team': {'name': team}, 'player': {'name': player},
        'period': 1, 'possession': possession,
        'minute': minute, 'second': second,
    }
    result.update(detail)
    return result


def sample_events():
    return [
        event('Pressure', 'pressure-001', 'Away', 'Attacker', second=1),
        event('Dispossessed', 'dispossessed-001', 'Home', 'Keeper', second=2),
        event('Duel', 'duel-001', 'Away', 'Attacker', second=3,
              duel={'outcome': {'name': 'Won'}}),
        event('Error', 'error-001', 'Home', 'Keeper', second=4),
        event('Shot', 'shot-goal-001', 'Away', 'Attacker', second=5,
              shot={'outcome': {'name': 'Goal'}, 'statsbomb_xg': 0.976}),
        event('Shot', 'shot-miss-001', 'Home', 'Forward', possession=8, second=7,
              shot={'outcome': {'name': 'Off T'}, 'statsbomb_xg': 0.2}),
        event('Shot', 'shot-goal-002', 'Home', 'Forward', possession=9, minute=62,
              shot={'outcome': {'name': 'Goal'}, 'statsbomb_xg': 0.291}),
    ]


def test_goal_origins_counts_source_goals_not_all_shots(monkeypatch):
    monkeypatch.setattr(api, 'load_events', sample_events)
    report = api.goal_origins(limit=30)
    assert report['status'] == 'ready'
    assert report['goal_count'] == 2
    assert {g['event_id'] for g in report['goals']} == {'shot-goal-001', 'shot-goal-002'}
    away = next(t for t in report['teams'] if t['team'] == 'Away')
    assert away['source_goal_count'] == 1
    assert away['goal_shot_xg_sum'] == 0.976
    assert away['xg_covered_goals'] == 1
    assert away['finding_counts']['goal_with_prior_error'] == 1
    assert away['finding_counts']['goal_with_prior_dispossessed'] == 1
    assert away['finding_counts']['goal_with_prior_won_duel'] == 1
    assert away['finding_counts']['high_xg_shot'] == 1
    home = next(t for t in report['teams'] if t['team'] == 'Home')
    assert home['goal_shot_xg_sum'] == 0.291
    assert all(count == 0 for count in home['finding_counts'].values())


def test_goal_origins_preserves_evidence_ids_and_no_causality(monkeypatch):
    monkeypatch.setattr(api, 'load_events', sample_events)
    goal = api.goal_origins(limit=30)['goals'][0]
    findings = {f['code']: f for f in goal['classification']['findings']}
    assert findings['goal_with_prior_error']['evidence_event_ids'] == ['error-001']
    assert findings['goal_with_prior_dispossessed']['evidence_event_ids'] == ['dispossessed-001']
    assert findings['goal_with_prior_won_duel']['evidence_event_ids'] == ['duel-001']
    assert findings['high_xg_shot']['evidence_event_ids'] == ['shot-goal-001']
    assert 'nedensellik' in findings['goal_with_prior_error']['explanation']


def test_goal_origins_truncation_is_disclosed(monkeypatch):
    monkeypatch.setattr(api, 'load_events', sample_events)
    goal = api.goal_origins(limit=1)['goals'][0]
    assert goal['truncated'] is True
    assert goal['classification']['context_truncated'] is True
    assert not any(f['code'] == 'goal_with_prior_error'
                   for f in goal['classification']['findings'])


def test_goal_origins_missing_source(monkeypatch):
    monkeypatch.setattr(api, 'load_events', lambda: None)
    report = api.goal_origins(limit=30)
    assert report['status'] == 'insufficient_data'
    assert report['goals'] == []


def test_goal_origins_missing_xg_is_not_fabricated(monkeypatch):
    data = [event('Shot', 'shot-goal-003', 'Away', 'Attacker',
                  shot={'outcome': {'name': 'Goal'}})]
    monkeypatch.setattr(api, 'load_events', lambda: data)
    report = api.goal_origins(limit=30)
    assert report['goals'][0]['statsbomb_xg'] is None
    assert report['teams'][0]['xg_covered_goals'] == 0
    assert report['teams'][0]['goal_shot_xg_sum'] == 0
