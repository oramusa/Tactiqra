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

def validate_event_identity(events):
    """Reject ambiguous event identities before aggregating a match."""
    seen = set()
    for event in events:
        if not isinstance(event, dict):
            raise ValueError('Invalid event record')
        eid = event.get('id')
        if not isinstance(eid, str) or not eid.strip() or eid in seen:
            raise ValueError('Missing or duplicate event identity')
        seen.add(eid)
        if not isinstance(event.get('type'), dict) or not isinstance(event['type'].get('name'), str):
            raise ValueError('Invalid event type')
        for key in ('team','player','position','shot','pass','ball_recovery','play_pattern','possession_team'):
            if event.get(key) is not None and not isinstance(event[key], dict):
                raise ValueError('Invalid event field: '+key)

def playing_style(events, team_id, opponent_id):
    """Descriptive source-tag counts; no possession-time or tracking inference."""
    result = {}
    for side, tid in (('own', team_id), ('opponent', opponent_id)):
        passes = completed = located = forward = long_passes = length_known = pressures = 0
        lanes = {'left': 0, 'center': 0, 'right': 0}
        evidence = {'forward': [], 'long': [], 'pressure': []}
        def valid(p):
            return isinstance(p, list) and len(p) >= 2 and all(type(v) in (int,float) and isfinite(v) and 0 <= v <= b for v,b in zip(p[:2],(120,80)))
        for e in events:
            if (e.get('team') or {}).get('id') != tid:
                continue
            kind = e['type']['name']
            if kind == 'Pressure':
                pressures += 1
                evidence['pressure'].append(e['id'])
            if kind != 'Pass':
                continue
            passes += 1
            p = e.get('pass') or {}
            completed += int(p.get('outcome') is None)
            length = p.get('length')
            if type(length) in (int,float) and isfinite(length) and length >= 0:
                length_known += 1
                if length >= 30:
                    long_passes += 1
                    evidence['long'].append(e['id'])
            a,b = e.get('location'),p.get('end_location')
            if valid(a) and valid(b):
                located += 1
                lanes['left' if b[1]<80/3 else 'right' if b[1]>=160/3 else 'center'] += 1
                if b[0]-a[0] >= 5:
                    forward += 1
                    evidence['forward'].append(e['id'])
        result[side] = dict(passes=passes,completed=completed,located=located,forward=forward,
                            length_known=length_known,long_passes=long_passes,pressures=pressures,
                            lanes=lanes,evidence=evidence)
    return result

def attacking_patterns(events, team_id, opponent_id):
    """Raw-coordinate completed pass entries and same-possession pre-shot chains."""
    result = {}
    def valid(p):
        return isinstance(p,list) and len(p)>=2 and all(type(v) in (int,float) and isfinite(v) and 0<=v<=b for v,b in zip(p[:2],(120,80)))
    def box(p):
        return p[0]>=102 and 18<=p[1]<=62
    for side,tid in (('own',team_id),('opponent',opponent_id)):
        row={'completed':0,'located':0,'third_entries':[],'box_entries':[],'shots':0,'covered_shots':0,'chains':[]}
        chains={}
        for e in events:
            if (e.get('team') or {}).get('id')!=tid:
                continue
            kind=e['type']['name']
            period,pos=e.get('period'),e.get('possession')
            key=(period,pos) if type(period) is int and type(pos) is int and (e.get('possession_team') or {}).get('id')==tid else None
            if kind=='Pass' and (e.get('pass') or {}).get('outcome') is None:
                row['completed']+=1
                a,b=e.get('location'),(e.get('pass') or {}).get('end_location')
                if key is not None:
                    chain=chains.setdefault(key,[])
                    chain.append(e)
                if not valid(a) or not valid(b):
                    continue
                row['located']+=1
                entry={'event_id':e['id'],'minute':e.get('minute'),'start':a[:2],'end':b[:2],'lane':'left' if b[1]<80/3 else 'right' if b[1]>=160/3 else 'center'}
                if a[0]<80<=b[0]:
                    row['third_entries'].append(entry)
                if not box(a) and box(b):
                    row['box_entries'].append(entry)
            if kind=='Shot':
                row['shots']+=1
                if key is None:
                    continue
                row['covered_shots']+=1
                prior=chains.pop(key,[])
                first=prior[0].get('location') if prior else None
                row['chains'].append({'shot_id':e['id'],'minute':e.get('minute'),'goal':((e.get('shot') or {}).get('outcome') or {}).get('name')=='Goal','pass_count':len(prior),'start_zone':('defensive' if first[0]<40 else 'middle' if first[0]<80 else 'attacking') if valid(first) else None,'pass_ids':[p['id'] for p in prior[-10:]]})
        result[side]=row
    return result

def defensive_weakness(events, team_id, opponent_id, attack, losses, fullbacks, set_pieces):
    """Observed conceded events, not inferred off-ball defensive gaps."""
    result={}
    for side,tid,other in (('own',team_id,'opponent'),('opponent',opponent_id,'own')):
        conceded=attack[other]
        shots=[e for e in events if e['type']['name']=='Shot' and (e.get('team') or {}).get('id')!=tid and (e.get('team') or {}).get('id') in (team_id,opponent_id)]
        located=[]
        for e in shots:
            p=e.get('location')
            if isinstance(p,list) and len(p)>=2 and all(type(v) in (int,float) and isfinite(v) and 0<=v<=b for v,b in zip(p[:2],(120,80))):
                located.append({'id':e['id'],'x':p[0],'y':p[1],'goal':((e.get('shot') or {}).get('outcome') or {}).get('name')=='Goal'})
        result[side]={'shots':len(shots),'located_shots':located,'third_entries':conceded['third_entries'],'box_entries':conceded['box_entries'],'loss_covered':losses[other]['covered'],'loss_candidates':losses[other]['candidates'],'fullback_candidates':fullbacks[other]['candidates'],'set_piece_classified':set_pieces[other]['classified'],'set_piece_shots':set_pieces[other]['categories']}
    return result

def transition_intelligence(events, recoveries, losses):
    """Reuse existing 15-second candidate windows; nested thresholds, not causal rates."""
    by_id={e['id']:e for e in events}
    result={}
    for side in ('own','opponent'):
        result[side]={}
        for kind,windows,id_key in (('recovery',recoveries,'recovery_event_id'),('loss',losses,'loss_event_id')):
            w=windows[side]
            candidates=[]
            for c in w['candidates']:
                p=by_id[c[id_key]].get('location')
                valid=isinstance(p,list) and len(p)>=2 and all(type(v) in (int,float) and isfinite(v) and 0<=v<=b for v,b in zip(p[:2],(120,80)))
                candidates.append({**c,'origin':p[:2] if valid else None,'zone':('defensive' if p[0]<40 else 'middle' if p[0]<80 else 'attacking') if valid else None})
            result[side][kind]={'covered':w['covered'],'shots':w['shots'],'candidates':candidates,'thresholds':{str(t):{'shots':sum(c['seconds']<=t for c in candidates),'goals':sum(c['seconds']<=t and c['goal'] for c in candidates)} for t in (5,10,15)}}
    return result

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
            value = int(h)*3600 + int(m)*60 + float(s)
            return value if isfinite(value) and value >= 0 and 0 <= int(m) < 60 and 0 <= float(s) < 60 and int(h) >= 0 else None
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

def loss_to_shot(events, team_id, opponent_id):
    """Nearest explicit loss tag before a shot, within 15 seconds and one period.
    Temporal association only; no inferred possession change or causation."""
    def clock(e):
        try:
            h,m,s = e['timestamp'].split(':')
            t = int(h)*3600 + int(m)*60 + float(s)
            return t if isfinite(t) and t >= 0 else None
        except (KeyError, ValueError, TypeError, AttributeError):
            return None
    result = {'own': {'shots':0,'covered':0,'candidates':[]},
              'opponent': {'shots':0,'covered':0,'candidates':[]}}
    for i,e in enumerate(events):
        if not isinstance(e,dict) or (e.get('type') or {}).get('name') != 'Shot':
            continue
        tid = (e.get('team') or {}).get('id')
        if tid not in (team_id,opponent_id):
            continue
        row = result['own' if tid==team_id else 'opponent']
        row['shots'] += 1
        t,period = clock(e),e.get('period')
        if t is None or type(period) is not int:
            continue
        candidate = None
        complete = True
        for j in range(i-1,-1,-1):
            p = events[j]
            if not isinstance(p,dict):
                complete = False
                break
            if p.get('period') != period:
                break
            pt = clock(p)
            if pt is None or pt > t:
                complete = False
                break
            if t-pt > 15:
                break
            kind = (p.get('type') or {}).get('name')
            other = (p.get('team') or {}).get('id')
            if candidate is None and other == (opponent_id if tid==team_id else team_id) and kind in ('Dispossessed','Miscontrol','Error') and isinstance(p.get('id'),str):
                candidate = {'loss_event_id':p['id'],'shot_event_id':e['id'],
                             'loss_type':kind,'seconds':round(t-pt,3),
                             'loss_player':(p.get('player') or {}).get('name'),
                             'shot_player':(e.get('player') or {}).get('name'),
                             'minute':e.get('minute'),'goal':((e.get('shot') or {}).get('outcome') or {}).get('name')=='Goal'}
        if complete:
            row['covered'] += 1
            if candidate is not None:
                row['candidates'].append(candidate)
    return result

def recovery_to_shot(events, team_id, opponent_id):
    """Explicit successful recovery followed by a same-possession shot within 15s."""
    def clock(e):
        try:
            h,m,s=e['timestamp'].split(':')
            t=int(h)*3600+int(m)*60+float(s)
            return t if isfinite(t) and t>=0 else None
        except (KeyError,ValueError,TypeError,AttributeError):
            return None
    result={side:{'shots':0,'covered':0,'candidates':[]} for side in ('own','opponent')}
    for i,e in enumerate(events):
        if not isinstance(e,dict) or (e.get('type') or {}).get('name')!='Shot':
            continue
        tid=(e.get('team') or {}).get('id')
        if tid not in (team_id,opponent_id):
            continue
        row=result['own' if tid==team_id else 'opponent']
        row['shots']+=1
        t,period,pos=clock(e),e.get('period'),e.get('possession')
        if t is None or type(period) is not int or type(pos) is not int or (e.get('possession_team') or {}).get('id')!=tid:
            continue
        candidate=None
        complete=True
        for j in range(i-1,-1,-1):
            p=events[j]
            if not isinstance(p,dict):
                complete=False
                break
            if p.get('period')!=period or p.get('possession')!=pos:
                break
            pt=clock(p)
            if pt is None or pt>t:
                complete=False
                break
            if t-pt>15:
                break
            if candidate is None and (p.get('type') or {}).get('name')=='Ball Recovery' and (p.get('team') or {}).get('id')==tid and not (p.get('ball_recovery') or {}).get('recovery_failure') and isinstance(p.get('id'),str):
                candidate={'recovery_event_id':p['id'],'shot_event_id':e['id'],'seconds':round(t-pt,3),'recovery_player':(p.get('player') or {}).get('name'),'shot_player':(e.get('player') or {}).get('name'),'minute':e.get('minute'),'goal':((e.get('shot') or {}).get('outcome') or {}).get('name')=='Goal'}
        if complete:
            row['covered']+=1
            if candidate is not None:
                row['candidates'].append(candidate)
    return result

def set_piece_summary(events, team_id, opponent_id):
    """Shot play-pattern tags, not counts of set-piece opportunities."""
    patterns={'From Corner':'corner','From Free Kick':'free_kick','From Throw In':'throw_in'}
    result={side:{'shots':0,'classified':0,'categories':{k:[] for k in patterns.values()}} for side in ('own','opponent')}
    for e in events:
        if not isinstance(e,dict) or (e.get('type') or {}).get('name')!='Shot':
            continue
        tid=(e.get('team') or {}).get('id')
        if tid not in (team_id,opponent_id):
            continue
        row=result['own' if tid==team_id else 'opponent']
        row['shots']+=1
        pattern=(e.get('play_pattern') or {}).get('name')
        if not isinstance(pattern,str) or not pattern:
            continue
        row['classified']+=1
        if pattern not in patterns:
            continue
        shot=e.get('shot') or {}
        xg=shot.get('statsbomb_xg')
        row['categories'][patterns[pattern]].append({'event_id':e['id'],'minute':e.get('minute'),'player':(e.get('player') or {}).get('name'),'goal':(shot.get('outcome') or {}).get('name')=='Goal','xg':xg if type(xg) in (int,float) and isfinite(xg) and 0<=xg<=1 else None})
    return result

def flank_entries(events, team_id, opponent_id):
    """Completed passes crossing into raw attacking third, by destination lane."""
    result={side:{'completed':0,'located':0,'entries':[]} for side in ('own','opponent')}
    def valid(p):
        return isinstance(p,list) and len(p)>=2 and all(type(v) in (int,float) and isfinite(v) and 0<=v<=b for v,b in zip(p[:2],(120,80)))
    for e in events:
        if not isinstance(e,dict) or (e.get('type') or {}).get('name')!='Pass':
            continue
        tid=(e.get('team') or {}).get('id')
        p=e.get('pass') or {}
        if tid not in (team_id,opponent_id) or p.get('outcome') is not None:
            continue
        row=result['own' if tid==team_id else 'opponent']
        row['completed']+=1
        a,b=e.get('location'),p.get('end_location')
        if not valid(a) or not valid(b) or not isinstance(e.get('id'),str):
            continue
        row['located']+=1
        if a[0]<80<=b[0]:
            lane='left' if b[1]<80/3 else 'right' if b[1]>=160/3 else 'center'
            row['entries'].append({'event_id':e['id'],'lane':lane,'start':a[:2],'end':b[:2],'minute':e.get('minute'),'player':(e.get('player') or {}).get('name')})
    return result

def fullback_loss_candidates(events, team_id, opponent_id, *, loss_windows=None):
    """Explicit fullback-position loss tags preceding opposing shots; not tracking."""
    positions={'Left Back','Right Back','Left Wing Back','Right Wing Back'}
    by_id={e.get('id'):e for e in events if isinstance(e,dict) and isinstance(e.get('id'),str)}
    windows=loss_windows if loss_windows is not None else loss_to_shot(events,team_id,opponent_id)
    result={}
    for side,window in windows.items():
        candidates=[]
        known=0
        for c in window['candidates']:
            event=by_id.get(c['loss_event_id'],{})
            position=(event.get('position') or {}).get('name')
            if isinstance(position,str) and position:
                known+=1
            if position not in positions:
                continue
            loc=event.get('location')
            valid=isinstance(loc,list) and len(loc)>=2 and all(type(v) in (int,float) and isfinite(v) and 0<=v<=b for v,b in zip(loc[:2],(120,80)))
            candidates.append({**c,'position':position,'loss_location':loc[:2] if valid else None,
                               'advanced_raw':loc[0]>=60 if valid else None})
        result[side]={'matched_shots':len(window['candidates']),'position_known':known,'candidates':candidates}
    return result

@router.get('/historical-teams')
def historical_teams():
    if os.getenv('FOOTBALLIQ_STATSBOMB_PILOT') != '3773386':
        return {'status':'not_configured','teams':[]}
    try:
        teams = {}
        for m in read_source('matches/11/90.json'):
            if not isinstance(m,dict) or m.get('match_status')!='available' or type(m.get('match_id')) is not int:
                continue
            for side in ('home','away'):
                t=m.get(side+'_team') or {}
                tid,name=t.get(side+'_team_id'),t.get(side+'_team_name')
                if type(tid) is not int or not isinstance(name,str) or not name.strip():
                    continue
                row=teams.setdefault(tid,{'team_id':tid,'name':name,'ids':set()})
                row['ids'].add(m['match_id'])
        return {'status':'ready','competition_id':11,'season_id':90,
                'teams':sorted([{'team_id':r['team_id'],'name':r['name'],'catalog_matches':len(r['ids'])} for r in teams.values()],key=lambda r:r['name']),
                'limitations':['Available catalog entries only; event files not yet validated. Historical coverage is not full-season or current-form coverage.']}
    except (OSError,ValueError,TypeError,AttributeError,KeyError) as exc:
        raise HTTPException(503,'Historical team catalog unavailable') from exc

@router.get('/historical-multi-match')
def historical_multi_match(limit: int = Query(3, ge=1, le=5), team_id: int = Query(217, ge=1)):
    if os.getenv('FOOTBALLIQ_STATSBOMB_PILOT') != '3773386':
        return {'status':'not_configured', 'matches':[]}
    try:
        catalog = read_source('matches/11/90.json')
        eligible = [m for m in catalog if isinstance(m, dict)
                    and team_id in ((m.get('home_team') or {}).get('home_team_id'),
                                (m.get('away_team') or {}).get('away_team_id'))
                    and m.get('match_status') == 'available'
                    and type(m.get('match_id')) is int]
        eligible.sort(key=lambda m: (m.get('match_date',''),m['match_id']), reverse=True)
        if len({m['match_id'] for m in eligible}) != len(eligible):
            raise ValueError('Duplicate catalog match identity')
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(503, 'Historical match catalog unavailable') from exc
    if not eligible:
        return {'status':'insufficient_data','team_id':team_id,'requested_matches':limit,'analyzed_matches':0,'coverage_ratio':0,'matches':[], 'limitations':['No available historical catalog matches for this team.']}
    results = []
    for m in eligible[:limit]:
        mid = m['match_id']
        home, away = m['home_team'], m['away_team']
        opp = away['away_team_id'] if home['home_team_id'] == team_id else home['home_team_id']
        row = {'match_id':mid, 'date':m.get('match_date'),
               'home':home.get('home_team_name'), 'away':away.get('away_team_name'),
               'source':BASE + f'events/{mid}.json'}
        try:
            events = read_source(f'events/{mid}.json')
            validate_event_identity(events)
            teams = {(e.get('team') or {}).get('id') for e in events if isinstance(e,dict)}
            if not {team_id,opp}.issubset(teams):
                raise ValueError('Team mismatch')
            row['own'], row['opponent'] = shot_summary(events,team_id,opp)
            row['playing_style'] = playing_style(events,team_id,opp)
            row['attacking_patterns'] = attacking_patterns(events,team_id,opp)
            row['goal_origins'] = goal_origins(events,team_id)
            row['loss_to_shot'] = loss_to_shot(events,team_id,opp)
            row['recovery_to_shot'] = recovery_to_shot(events,team_id,opp)
            row['set_pieces'] = set_piece_summary(events,team_id,opp)
            row['flank_entries'] = flank_entries(events,team_id,opp)
            row['fullback_loss_candidates'] = fullback_loss_candidates(events,team_id,opp,loss_windows=row['loss_to_shot'])
            row['transition_intelligence'] = transition_intelligence(events,row['recovery_to_shot'],row['loss_to_shot'])
            row['defensive_weakness'] = defensive_weakness(events,team_id,opp,row['attacking_patterns'],row['loss_to_shot'],row['fullback_loss_candidates'],row['set_pieces'])
            row['status'] = 'provisional'
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            row = {k:v for k,v in row.items() if k in ('match_id','date','home','away','source')}
            row['status'] = 'unavailable'
            row['reason'] = 'source_or_validation_failure'
        results.append(row)
    valid = [r for r in results if r['status']=='provisional']
    return {'status':'provisional' if valid else 'insufficient_data',
            'team_id':team_id,'competition_id':11,'season_id':90,
            'requested_matches':limit,'analyzed_matches':len(valid),
            'coverage_ratio':len(valid)/limit,'matches':results,
            'limitations':['Historical available matches only; not current form.',
            'Shot goals may exclude own goals. xG sums cover only shots with source xG.',
            'Box locations use raw StatsBomb shot coordinates; direction not independently verified.',
            'Goal origins use a 15-second same-possession window; absence of a tag does not establish absence of an error.',
            'Loss-to-shot candidates use nearest opposing explicit loss tag within 15 seconds in the same period, including across possessions; not proof of turnover causation.',
            'Recovery-to-shot uses explicit successful Ball Recovery tags within the same possession and 15 seconds; not all turnovers or counterattacks.',
            'Set-piece shots use source play-pattern tags; penalties and own goals are not separately analyzed, and opportunity conversion rates are unavailable.',
            'Flank entries count completed passes crossing raw x=80, grouped by destination y thirds; direction is not independently verified. Carries are excluded.',
            'Descriptive evidence, not causal tactical conclusions.']}

@router.get('/historical-match-catalog')
def historical_match_catalog():
    if os.getenv('FOOTBALLIQ_STATSBOMB_PILOT') != '3773386':
        return {'status':'not_configured','matches':[]}
    try:
        rows = read_source('matches/11/90.json')
        matches = [{'match_id':m['match_id'],'date':m['match_date'],
                    'home':m['home_team']['home_team_name'],'away':m['away_team']['away_team_name']}
                   for m in rows if m.get('match_status')=='available' and type(m.get('match_id')) is int]
        if len({m['match_id'] for m in matches}) != len(matches):
            raise ValueError('Duplicate catalog match identity')
        return {'status':'ready','matches':sorted(matches,key=lambda m:(m['date'],m['match_id']),reverse=True)}
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        raise HTTPException(503,'Historical catalog unavailable') from exc

@router.get('/historical-match/{match_id}')
def historical_match(match_id: int):
    catalog = historical_match_catalog()
    if catalog['status'] != 'ready':
        raise HTTPException(503,'Historical pilot not configured')
    match = next((m for m in catalog['matches'] if m['match_id']==match_id),None)
    if match is None:
        raise HTTPException(404,'Match not in available catalog')
    try:
        meta = next(m for m in read_source('matches/11/90.json') if m['match_id']==match_id)
        home,away = meta['home_team']['home_team_id'],meta['away_team']['away_team_id']
        events = read_source(f'events/{match_id}.json')
        validate_event_identity(events)
        teams = {(e.get('team') or {}).get('id') for e in events if isinstance(e,dict)}
        if not {home,away}.issubset(teams):
            raise ValueError('Team mismatch')
        a,b = shot_summary(events,home,away)
        shots = []
        for e in events:
            if not isinstance(e,dict) or (e.get('type') or {}).get('name') != 'Shot':
                continue
            shot = e.get('shot') or {}
            loc = e.get('location')
            valid = isinstance(loc,list) and len(loc)>=2 and all(type(v) in (int,float) and isfinite(v) and 0<=v<=b for v,b in zip(loc[:2],(120,80)))
            xg = shot.get('statsbomb_xg')
            shots.append({'event_id':e['id'],'side':'home' if (e.get('team') or {}).get('id')==home else 'away',
                          'location':loc[:2] if valid else None,'xg':xg if type(xg) in (int,float) and isfinite(xg) and 0<=xg<=1 else None,
                          'player':(e.get('player') or {}).get('name'),'minute':e.get('minute'),
                          'outcome':(shot.get('outcome') or {}).get('name')})
        heatmap = {'home':{},'away':{}}
        for e in events:
            if not isinstance(e,dict):
                continue
            tid = (e.get('team') or {}).get('id')
            if tid not in (home,away):
                continue
            side = 'home' if tid==home else 'away'
            player = e.get('player') or {}
            pid = player.get('id')
            key = str(pid) if type(pid) is int else 'unknown'
            row = heatmap[side].setdefault(key,{'player_id':pid if type(pid) is int else None,'player':player.get('name') or 'Unknown','events':0,'located':0,'cells':[0]*96})
            row['events'] += 1
            loc = e.get('location')
            if isinstance(loc,list) and len(loc)>=2 and all(type(v) in (int,float) and isfinite(v) and 0<=v<=b for v,b in zip(loc[:2],(120,80))):
                row['located'] += 1
                col = min(11,int(loc[0]//10))
                line = min(7,int(loc[1]//10))
                row['cells'][line*12+col] += 1
        networks = {}
        for tid,side in ((home,'home'),(away,'away')):
            nodes,links = {},{}
            attempts,completed,mapped = 0,0,0
            for e in events:
                if not isinstance(e,dict) or (e.get('team') or {}).get('id')!=tid or (e.get('type') or {}).get('name')!='Pass':
                    continue
                attempts += 1
                p = e.get('pass') or {}
                if p.get('outcome') is not None:
                    continue
                completed += 1
                sender,receiver = e.get('player') or {},p.get('recipient') or {}
                sid,rid = sender.get('id'),receiver.get('id')
                if type(sid) is not int or type(rid) is not int or sid==rid:
                    continue
                mapped += 1
                link = links.setdefault((sid,rid),{'from':sid,'to':rid,'count':0,'event_ids':[]})
                link['count'] += 1
                link['event_ids'].append(e['id'])
                for player in (sender,receiver):
                    nodes.setdefault(player['id'],{'id':player['id'],'name':player.get('name'),'x':0.0,'y':0.0,'located':0})
                loc=e.get('location')
                if isinstance(loc,list) and len(loc)>=2 and all(type(v) in (int,float) and isfinite(v) and 0<=v<=bound for v,bound in zip(loc[:2],(120,80))):
                    n=nodes[sid]
                    n['x']+=loc[0]
                    n['y']+=loc[1]
                    n['located']+=1
            for n in nodes.values():
                n['x']=round(n['x']/n['located'],3) if n['located'] else None
                n['y']=round(n['y']/n['located'],3) if n['located'] else None
            networks[side]={'attempts':attempts,'completed':completed,'mapped':mapped,'nodes':list(nodes.values()),'links':sorted(links.values(),key=lambda l:-l['count'])}
        players = {'home':{},'away':{}}
        for e in events:
            if not isinstance(e,dict):
                continue
            tid = (e.get('team') or {}).get('id')
            p = e.get('player') or {}
            pid = p.get('id')
            if tid not in (home,away) or type(pid) is not int:
                continue
            side = 'home' if tid==home else 'away'
            row = players[side].setdefault(pid,{'id':pid,'name':p.get('name'),'passes':0,'completed':0,'shots':0,'goals':0,'xg':0.0,'xg_count':0,'recoveries':0,'pressures':0,'loss_tags':0})
            kind = (e.get('type') or {}).get('name')
            if kind=='Pass':
                row['passes']+=1
                row['completed']+=int((e.get('pass') or {}).get('outcome') is None)
            elif kind=='Shot':
                shot=e.get('shot') or {}
                row['shots']+=1
                row['goals']+=int((shot.get('outcome') or {}).get('name')=='Goal')
                xg=shot.get('statsbomb_xg')
                if type(xg) in (int,float) and isfinite(xg) and 0<=xg<=1:
                    row['xg']+=xg
                    row['xg_count']+=1
            elif kind=='Ball Recovery':
                row['recoveries']+=int(not (e.get('ball_recovery') or {}).get('recovery_failure'))
            elif kind=='Pressure':
                row['pressures']+=1
            elif kind in ('Dispossessed','Miscontrol'):
                row['loss_tags']+=1
        timeline = []
        for e in events:
            if not isinstance(e,dict):
                continue
            tid = (e.get('team') or {}).get('id')
            if tid not in (home,away) or not isinstance(e.get('id'),str):
                continue
            kind = (e.get('type') or {}).get('name')
            detail = None
            replacement = None
            if kind == 'Shot':
                detail = ((e.get('shot') or {}).get('outcome') or {}).get('name')
                kind = 'Goal' if detail == 'Goal' else 'Shot'
            elif kind in ('Foul Committed','Bad Behaviour'):
                detail = ((e.get('foul_committed' if kind=='Foul Committed' else 'bad_behaviour') or {}).get('card') or {}).get('name')
                if not detail:
                    continue
                kind = 'Card'
            elif kind == 'Substitution':
                sub = e.get('substitution') or {}
                replacement = (sub.get('replacement') or {}).get('name')
                detail = (sub.get('outcome') or {}).get('name')
            elif kind not in ('Own Goal For','Own Goal Against'):
                continue
            timeline.append({'event_id':e['id'],'side':'home' if tid==home else 'away',
                             'kind':kind,'detail':detail,'replacement':replacement,
                             'player':(e.get('player') or {}).get('name'),
                             'minute':e.get('minute'),'second':e.get('second'),'period':e.get('period')})
        return {**match,'status':'provisional','home_stats':a,'away_stats':b,'shots':shots,'timeline':timeline,
                'pass_networks':networks,'players':{side:list(rows.values()) for side,rows in players.items()},
                'heatmap':{side:list(rows.values()) for side,rows in heatmap.items()},
                'source':BASE+f'events/{match_id}.json',
                'limitations':['Historical event data; shot goals may exclude own goals.']}
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        raise HTTPException(503,'Historical match data unavailable') from exc
