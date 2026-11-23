"""Read-only, bounded exploration of the separately configured historical StatsBomb file."""
from fastapi import APIRouter, Query
from app.heatmap_api import load_events

router = APIRouter(prefix='/api/v1/event-explorer', tags=['historical-event-explorer'])

@router.get('/events')
def explore_events(team_id: int | None = Query(None, gt=0),
                   event_type: str | None = Query(None, max_length=80),
                   period: int | None = Query(None, ge=1, le=5),
                   cursor: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100)):
    raw = load_events()
    if raw is None:
        return {'status': 'insufficient_data', 'reason': 'Historical event JSON not configured', 'items': [], 'next_cursor': None}
    matches = []
    for idx, event in enumerate(raw):
        if idx < cursor or not isinstance(event, dict):
            continue
        team = event.get('team') or {}
        kind = event.get('type') or {}
        if not isinstance(team, dict) or not isinstance(kind, dict):
            continue
        if team_id is not None and team.get('id') != team_id:
            continue
        if event_type is not None and kind.get('name') != event_type:
            continue
        if period is not None and event.get('period') != period:
            continue
        location = event.get('location')
        safe_location = location[:2] if isinstance(location, list) and len(location) >= 2 and all(type(x) in (int, float) for x in location[:2]) else None
        player = event.get('player')
        matches.append({'event_id': event.get('id'), 'index': idx, 'minute': event.get('minute'), 'second': event.get('second'), 'period': event.get('period'), 'team': team.get('name'), 'team_id': team.get('id'), 'player': player.get('name') if isinstance(player, dict) else None, 'type': kind.get('name'), 'location': safe_location})
        if len(matches) > limit:
            break
    has_more = len(matches) > limit
    items = matches[:limit]
    return {'status': 'ready', 'source': 'local_historical_statsbomb_events', 'provisional': True, 'items': items, 'next_cursor': items[-1]['index'] + 1 if has_more else None, 'limit': limit, 'filters': {'team_id': team_id, 'event_type': event_type, 'period': period}}

@router.get('/shots')
def historical_shots():
    """Source-bound shot coordinates and outcomes; no inferred goals or xG."""
    raw = load_events()
    if raw is None:
        return {'status': 'insufficient_data', 'reason': 'Historical event JSON not configured', 'items': []}
    items = []
    for idx, event in enumerate(raw):
        if not isinstance(event, dict) or (event.get('type') or {}).get('name') != 'Shot':
            continue
        team = event.get('team') or {}
        player = event.get('player') or {}
        shot = event.get('shot') or {}
        outcome = shot.get('outcome') or {}
        loc = event.get('location')
        valid = isinstance(loc, list) and len(loc) >= 2 and all(type(v) in (int, float) and 0 <= v <= limit for v, limit in zip(loc[:2], (120, 80)))
        items.append({
            'event_id': event.get('id'), 'index': idx,
            'minute': event.get('minute'), 'second': event.get('second'),
            'period': event.get('period'),
            'team': team.get('name') if isinstance(team, dict) else None,
            'team_id': team.get('id') if isinstance(team, dict) else None,
            'player': player.get('name') if isinstance(player, dict) else None,
            'location': loc[:2] if valid else None,
            'outcome': outcome.get('name') if isinstance(outcome, dict) else None,
            'shot_type': (shot.get('type') or {}).get('name') if isinstance(shot.get('type'), dict) else None,
            'statsbomb_xg': shot.get('statsbomb_xg') if isinstance(shot.get('statsbomb_xg'), (float, int)) else None,
        })
    return {
        'status': 'ready', 'source': 'local_historical_statsbomb_events',
        'provisional': True, 'shot_count': len(items),
        'located_count': sum(item['location'] is not None for item in items),
        'items': items,
        'notes': 'Raw source shot outcomes; not independently reconciled with official score. Shot direction not verified.',
    }


@router.get('/shot-context')
def shot_context(event_id: str = Query(..., min_length=8, max_length=80),
                 limit: int = Query(12, ge=1, le=30)):
    """Bounded source event window; adjacency is not proof of a causal sequence."""
    raw = load_events()
    if raw is None:
        return {'status': 'insufficient_data', 'reason': 'Historical event JSON not configured', 'items': []}
    match = next((i for i, e in enumerate(raw) if isinstance(e, dict) and
                  e.get('id') == event_id and (e.get('type') or {}).get('name') == 'Shot'), None)
    if match is None:
        return {'status': 'not_found', 'reason': 'Shot event not found', 'items': []}
    target = raw[match]
    period = target.get('period')
    possession = target.get('possession')
    candidates = [(i, e) for i, e in enumerate(raw[:match]) if isinstance(e, dict) and
                  e.get('period') == period and possession is not None and
                  e.get('possession') == possession]
    chosen = candidates[-limit:] if possession is not None else []
    chosen.append((match, target))
    items = []
    for idx, event in chosen:
        team = event.get('team')
        player = event.get('player')
        kind = event.get('type')
        location = event.get('location')
        items.append({
            'event_id': event.get('id'), 'index': idx, 'minute': event.get('minute'),
            'second': event.get('second'), 'period': event.get('period'),
            'possession': event.get('possession'),
            'team': team.get('name') if isinstance(team, dict) else None,
            'player': player.get('name') if isinstance(player, dict) else None,
            'type': kind.get('name') if isinstance(kind, dict) else None,
            'location': location[:2] if isinstance(location, list) and len(location) >= 2
                        and all(type(v) in (int, float) for v in location[:2]) else None,
        })
    # Explicit source labels only. Do not infer a causal chain from adjacency.
    evidence = []
    for item in items:
        if item['type'] in ('Error', 'Dispossessed', 'Pressure', 'Duel', 'Ball Receipt*', 'Shot'):
            original = raw[item['index']]
            detail = original.get('shot') if item['type'] == 'Shot' else original.get(item['type'].lower().replace(' ', '_').replace('*', ''))
            if not isinstance(detail, dict):
                detail = {}
            outcome = detail.get('outcome')
            if not isinstance(outcome, dict):
                outcome = {}
            evidence.append({
                'event_id': item['event_id'], 'type': item['type'],
                'minute': item['minute'], 'second': item['second'],
                'team': item['team'], 'player': item['player'],
                'outcome': outcome.get('name'),
                'shot_xg': detail.get('statsbomb_xg') if item['type'] == 'Shot'
                           and type(detail.get('statsbomb_xg')) in (int, float) else None,
            })
    interpretation = {
        'status': 'source_observations',
        'evidence': evidence,
        'has_error_label': any(e['type'] == 'Error' for e in evidence),
        'has_pressure_label': any(e['type'] == 'Pressure' for e in evidence),
        'has_dispossessed_label': any(e['type'] == 'Dispossessed' for e in evidence),
        'note': 'Source event labels within the selected possession; not proof that pressure or error caused the goal.'
    }
    # V1.5: descriptive labels, never inferred causality or invented xG.
    shot_detail = target.get('shot') if isinstance(target.get('shot'), dict) else {}
    shot_outcome = shot_detail.get('outcome')
    is_goal = isinstance(shot_outcome, dict) and shot_outcome.get('name') == 'Goal'
    shot_team = target.get('team')
    shot_team_name = shot_team.get('name') if isinstance(shot_team, dict) else None
    before = evidence[:-1]
    def matching(kind, predicate=lambda e: True):
        return [e for e in before if e['type'] == kind and predicate(e) and e['event_id']]
    findings = []
    def add(code, label, matches, explanation):
        if matches:
            findings.append({'code': code, 'label': label, 'status': 'observed',
                             'evidence_event_ids': [e['event_id'] for e in matches],
                             'explanation': explanation})
    if is_goal:
        add('goal_with_prior_error', 'Gol öncesi hata kaydı',
            matching('Error'),
            'Aynı possession içinde golden önce Error etiketi var; nedensellik doğrulanmadı.')
        add('goal_with_prior_dispossessed', 'Gol öncesi top kaybı kaydı',
            matching('Dispossessed'),
            'Aynı possession içinde golden önce Dispossessed etiketi var; top kazanımıyla eşdeğer değildir.')
        add('goal_with_prior_won_duel', 'Gol öncesi kazanılmış mücadele',
            matching('Duel', lambda e: e['outcome'] == 'Won' and e['team'] == shot_team_name),
            'Golü atan takım için Won sonucuna sahip Duel kaydı var; top kazanma zinciri doğrulanmadı.')
    xg = shot_detail.get('statsbomb_xg')
    if type(xg) in (int, float) and 0 <= xg <= 1 and xg >= 0.5:
        add('high_xg_shot', 'Yüksek kaynak xG şutu',
            [e for e in evidence if e['event_id'] == event_id],
            'Kaynak xG >= 0.50; bu eşik analitik gösterim içindir, yeniden hesaplanan xG değildir.')
    classification = {
        'status': 'source_classification' if possession is not None else 'insufficient_data',
        'is_goal': is_goal,
        'findings': findings if possession is not None else [],
        'context_truncated': len(candidates) > limit,
        'coverage_note': ('Son %d önceki olay gösteriliyor; daha eski kanıtlar dışarıda kalmış olabilir.' % limit)
                         if len(candidates) > limit else 'Seçili possession içindeki önceki olaylar listelendi.',
        'limitations': 'Etiketler betimleyicidir; kesin neden-sonuç, otomatik top kazanımı veya taktik niyet kanıtı değildir.'
    }
    return {'status': 'ready', 'source': 'local_historical_statsbomb_events',
            'shot_event_id': event_id, 'possession': possession, 'period': period,
            'has_possession': possession is not None, 'items': items,
            'interpretation': interpretation, 'classification': classification,
            'truncated': len(candidates) > limit,
            'notes': 'Same-possession events preceding the shot in file order. '
                     'Not a validated causal chain, tracking reconstruction, or tactical attribution.'}


@router.get('/goal-origins')
def goal_origins(limit: int = Query(30, ge=1, le=30)):
    """Match-wide source-labeled goals with bounded possession evidence.

    Goal labels are source Shot outcomes, not independently validated score.
    """
    raw = load_events()
    if raw is None:
        return {'status': 'insufficient_data', 'reason': 'Historical event JSON not configured',
                'goals': [], 'teams': [], 'goal_count': 0}
    goal_events = []
    for idx, event in enumerate(raw):
        if not isinstance(event, dict):
            continue
        kind = event.get('type')
        shot = event.get('shot')
        if not (isinstance(kind, dict) and kind.get('name') == 'Shot'
                and isinstance(shot, dict)):
            continue
        outcome = shot.get('outcome')
        if isinstance(outcome, dict) and outcome.get('name') == 'Goal':
            goal_events.append((idx, event))
    goals = []
    for idx, event in goal_events:
        event_id = event.get('id')
        if not isinstance(event_id, str) or not event_id:
            continue
        context = shot_context(event_id=event_id, limit=limit)
        team = event.get('team')
        player = event.get('player')
        shot = event['shot']
        xg = shot.get('statsbomb_xg')
        valid_xg = type(xg) in (int, float) and 0 <= xg <= 1
        goals.append({
            'event_id': event_id, 'index': idx,
            'team': team.get('name') if isinstance(team, dict) else None,
            'player': player.get('name') if isinstance(player, dict) else None,
            'minute': event.get('minute'), 'second': event.get('second'),
            'period': event.get('period'),
            'statsbomb_xg': xg if valid_xg else None,
            'possession': context.get('possession'),
            'classification': context.get('classification'),
            'evidence': context.get('interpretation', {}).get('evidence', []),
            'truncated': context.get('truncated', False),
        })
    names = sorted({g['team'] for g in goals if g['team']})
    teams = []
    for name in names:
        subset = [g for g in goals if g['team'] == name]
        teams.append({
            'team': name, 'source_goal_count': len(subset),
            'xg_covered_goals': sum(g['statsbomb_xg'] is not None for g in subset),
            'goal_shot_xg_sum': sum(g['statsbomb_xg'] for g in subset if g['statsbomb_xg'] is not None),
            'finding_counts': {
                code: sum(any(f['code'] == code for f in
                         (g.get('classification') or {}).get('findings', [])) for g in subset)
                for code in ('goal_with_prior_error', 'goal_with_prior_dispossessed',
                             'goal_with_prior_won_duel', 'high_xg_shot')
            },
        })
    return {
        'status': 'ready', 'source': 'local_historical_statsbomb_events',
        'provisional': True, 'goal_count': len(goals), 'goals': goals, 'teams': teams,
        'notes': 'Source Shot/Goal labels only; not official-score reconciliation. '
                 'Findings are descriptive and may miss events outside the bounded context. '
                 'Goal-shot xG sum is not match total xG. No causal attribution.',
    }
