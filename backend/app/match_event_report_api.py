"""Descriptive event report from a configured local file, never a tactical inference."""
from collections import Counter
from fastapi import APIRouter
from .heatmap_api import load_events

router = APIRouter(prefix='/api/v1/opponentiq', tags=['historical-event-report'])


def summarize_events(events):
    teams = {}
    skipped = 0
    for e in events:
        if not isinstance(e, dict):
            skipped += 1
            continue
        t, kind = e.get('team'), e.get('type')
        if not isinstance(t, dict) or type(t.get('id')) is not int or not isinstance(kind, dict) or not isinstance(kind.get('name'), str):
            skipped += 1
            continue
        tid = t['id']
        row = teams.setdefault(tid, {'team_id':tid, 'team_name':t.get('name') or str(tid), 'event_count':0,
                                      'passes':0, 'completed_passes':0, 'shots':0, 'goals_from_shots':0,
                                      'located_events':0, 'event_types':Counter()})
        row['event_count'] += 1
        typ = kind['name']
        row['event_types'][typ] += 1
        loc = e.get('location')
        if isinstance(loc, list) and len(loc)>=2 and all(type(v) in (float,int) and 0<=v<=bound for v,bound in zip(loc[:2],(120,80))):
            row['located_events'] += 1
        if typ == 'Pass':
            row['passes'] += 1
            if not (isinstance(e.get('pass'),dict) and e['pass'].get('outcome')):
                row['completed_passes'] += 1
        elif typ == 'Shot':
            row['shots'] += 1
            if isinstance(e.get('shot'),dict) and isinstance(e['shot'].get('outcome'),dict) and e['shot']['outcome'].get('name')=='Goal':
                row['goals_from_shots'] += 1
    result=[]
    for row in sorted(teams.values(),key=lambda x:x['team_name']):
        row['event_types']=dict(sorted(row['event_types'].items()))
        row['pass_completion_pct']=round(row['completed_passes']/row['passes']*100,1) if row['passes'] else None
        result.append(row)
    return {'status':'event_summary' if result else 'insufficient_data','source':'configured_local_statsbomb_events',
            'provisional':True,'match_identity_verified':False,'skipped_events':skipped,'total_events':len(events),
            'teams':result,'limitations':['Event counts are not possession percentages or tracking metrics.',
            'Goals from Shot events may differ from official score (e.g. own goals).',
            'The configured file has not been independently matched to a fixture.']}

@router.get('/historical-event-report')
def historical_event_report():
    events=load_events()
    if events is None:
        return {'status':'not_configured','teams':[],'match_identity_verified':False,
                'reason':'Set FOOTBALLIQ_HISTORICAL_EVENTS to a local StatsBomb events JSON file.'}
    return summarize_events(events)
