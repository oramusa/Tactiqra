"""Historical StatsBomb multi-match pilot; separate from current provider windows."""
import json
import os
from functools import lru_cache
from urllib.request import urlopen
from fastapi import APIRouter, HTTPException, Query
from math import isfinite

router = APIRouter(prefix='/api/v1/opponentiq', tags=['historical-multi-match'])
BASE = 'https://raw.githubusercontent.com/statsbomb/open-data/master/data/'
MAX_BYTES = 30_000_000

@lru_cache(maxsize=12)
def read_source(path):
    with urlopen(BASE + path, timeout=5) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Oversized source')
    rows = json.loads(data)
    if not isinstance(rows, list) or not rows or len(rows) > 200_000:
        raise ValueError('Invalid source')
    return rows

def shot_summary(events, team_id, opponent_id):
    sides = {tid: {'shots': 0, 'goals_from_shots': 0, 'xg_sum': 0.0,
                   'xg_count': 0, 'box_shots': 0, 'located_shots': 0,
                   'goal_event_ids': []} for tid in (team_id, opponent_id)}
    seen = set()
    for e in events:
        if not isinstance(e, dict) or (e.get('type') or {}).get('name') != 'Shot':
            continue
        tid = (e.get('team') or {}).get('id')
        eid = e.get('id')
        if tid not in sides or not isinstance(eid, str) or eid in seen:
            raise ValueError('Invalid or duplicate shot identity')
        seen.add(eid)
        row = sides[tid]
        shot = e.get('shot') or {}
        row['shots'] += 1
        xg = shot.get('statsbomb_xg')
        if type(xg) in (int, float) and isfinite(xg) and 0 <= xg <= 1:
            row['xg_count'] += 1
            row['xg_sum'] += xg
        loc = e.get('location')
        if isinstance(loc, list) and len(loc) >= 2 and all(type(v) in (int,float) and 0 <= v <= b for v,b in zip(loc[:2],(120,80))):
            row['located_shots'] += 1
            row['box_shots'] += int(loc[0] >= 102 and 18 <= loc[1] <= 62)
        if (shot.get('outcome') or {}).get('name') == 'Goal':
            row['goals_from_shots'] += 1
            row['goal_event_ids'].append(eid)
    for row in sides.values():
        row['xg_sum'] = round(row['xg_sum'], 6) if row['xg_count'] else None
    return sides[team_id], sides[opponent_id]

def goal_origins(events, team_id):
    """Same-possession temporal associations, not causal attribution."""
    def seconds(e):
        try:
            h,m,s = e['timestamp'].split(':')
            return int(h)*3600 + int(m)*60 + float(s)
        except (KeyError, ValueError, TypeError, AttributeError):
            return None
    goals = []
    for i,e in enumerate(events):
        if not isinstance(e,dict) or (e.get('type') or {}).get('name') != 'Shot' or ((e.get('shot') or {}).get('outcome') or {}).get('name') != 'Goal':
            continue
        scoring = (e.get('team') or {}).get('id')
        t = seconds(e)
        possession = e.get('possession')
        period = e.get('period')
        evidence = []
        covered = t is not None and type(possession) is int and type(period) is int
        if covered:
            for p in reversed(events[:i]):
                if not isinstance(p,dict) or p.get('period') != period or p.get('possession') != possession:
                    break
                pt = seconds(p)
                if pt is None or pt > t:
                    covered = False
                    break
                if t-pt > 15:
                    break
                kind = (p.get('type') or {}).get('name')
                other = (p.get('team') or {}).get('id')
                if kind in ('Error','Dispossessed','Miscontrol') and type(other) is int and other != scoring and isinstance(p.get('id'),str):
                    evidence.append({'type':kind,'event_id':p['id'],'player':(p.get('player') or {}).get('name'),'seconds_before_goal':round(t-pt,3),'location':p.get('location')})
        goals.append({'goal_event_id':e.get('id'),'side':'own' if scoring==team_id else 'opponent','minute':e.get('minute'),'player':(e.get('player') or {}).get('name'),'play_pattern':(e.get('play_pattern') or {}).get('name'),'window_status':'available' if covered else 'incomplete','preceding_events':list(reversed(evidence)) if covered else []})
    return goals

@router.get('/historical-multi-match')
def historical_multi_match(limit: int = Query(3, ge=1, le=5)):
    if os.getenv('FOOTBALLIQ_STATSBOMB_PILOT') != '3773386':
        return {'status':'not_configured', 'matches':[]}
    try:
        catalog = read_source('matches/11/90.json')
        eligible = [m for m in catalog if isinstance(m, dict)
                    and 217 in ((m.get('home_team') or {}).get('home_team_id'),
                                (m.get('away_team') or {}).get('away_team_id'))
                    and m.get('match_status') == 'available'
                    and type(m.get('match_id')) is int]
        eligible.sort(key=lambda m: (m.get('match_date',''),m['match_id']), reverse=True)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(503, 'Historical match catalog unavailable') from exc
    results = []
    for m in eligible[:limit]:
        mid = m['match_id']
        home, away = m['home_team'], m['away_team']
        opp = away['away_team_id'] if home['home_team_id'] == 217 else home['home_team_id']
        row = {'match_id':mid, 'date':m.get('match_date'),
               'home':home.get('home_team_name'), 'away':away.get('away_team_name'),
               'source':BASE + f'events/{mid}.json'}
        try:
            events = read_source(f'events/{mid}.json')
            teams = {(e.get('team') or {}).get('id') for e in events if isinstance(e,dict)}
            if not {217,opp}.issubset(teams):
                raise ValueError('Team mismatch')
            row['own'], row['opponent'] = shot_summary(events,217,opp)
            row['goal_origins'] = goal_origins(events,217)
            row['status'] = 'provisional'
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            row['status'] = 'unavailable'
        results.append(row)
    valid = [r for r in results if r['status']=='provisional']
    return {'status':'provisional' if valid else 'insufficient_data',
            'team_id':217,'competition_id':11,'season_id':90,
            'requested_matches':limit,'analyzed_matches':len(valid),
            'coverage_ratio':len(valid)/limit,'matches':results,
            'limitations':['Historical available matches only; not current form.',
            'Shot goals may exclude own goals. xG sums cover only shots with source xG.',
            'Box locations use raw StatsBomb shot coordinates; direction not independently verified.',
            'Goal origins use a 15-second same-possession window; absence of a tag does not establish absence of an error.',
            'Descriptive evidence, not causal tactical conclusions.']}
