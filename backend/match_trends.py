"""Scoreline-only trends; not event-derived tactical metrics."""

def summarize(window):
    team_id = window['teamId']
    records = []
    for match in reversed(window['matches']):
        if not all(k in match for k in ('homeTeam','awayTeam','homeGoals','awayGoals')):
            continue
        home = match['homeTeam']['id'] == team_id
        away = match['awayTeam']['id'] == team_id
        if home == away or match['homeGoals'] is None or match['awayGoals'] is None:
            continue
        gf = match['homeGoals'] if home else match['awayGoals']
        ga = match['awayGoals'] if home else match['homeGoals']
        result = 'W' if gf > ga else 'D' if gf == ga else 'L'
        records.append({'matchId':match['id'],'date':match['utcDate'],
                        'goalsFor':gf,'goalsAgainst':ga,'result':result,
                        'points':3 if result=='W' else 1 if result=='D' else 0})
    count = len(records)
    wins = sum(x['result']=='W' for x in records)
    draws = sum(x['result']=='D' for x in records)
    losses = count-wins-draws
    gf = sum(x['goalsFor'] for x in records)
    ga = sum(x['goalsAgainst'] for x in records)
    return {'metricType':'scoreline_only','requestedCount':window['requestedCount'],
            'selectedCount':window['selectedCount'],'scoredCount':count,
            'wins':wins,'draws':draws,'losses':losses,
            'goalsFor':gf,'goalsAgainst':ga,
            'goalsForPerMatch':round(gf/count,3) if count else None,
            'goalsAgainstPerMatch':round(ga/count,3) if count else None,
            'pointsPerMatch':round(sum(x['points'] for x in records)/count,3) if count else None,
            'chronologicalMatches':records,
            'warning': 'Some selected matches lack usable scorelines' if count<window['selectedCount'] else None}
