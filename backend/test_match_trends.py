from match_trends import summarize

def match(i,home,away,hg,ag):
    return {'id':i,'utcDate':f'2026-01-{i:02d}T00:00:00Z',
            'homeTeam':{'id':home},'awayTeam':{'id':away},
            'homeGoals':hg,'awayGoals':ag}

def test_home_away_results_and_chronological_trend():
    window={'teamId':1,'requestedCount':13,'selectedCount':3,
            'matches':[match(3,2,1,0,2),match(2,1,2,1,1),match(1,1,2,0,2)]}
    result=summarize(window)
    assert (result['wins'],result['draws'],result['losses'])==(1,1,1)
    assert result['goalsForPerMatch']==1.0
    assert result['goalsAgainstPerMatch']==1.0
    assert result['pointsPerMatch']==1.333
    assert [x['matchId'] for x in result['chronologicalMatches']]==[1,2,3]
    assert result['requestedCount']==13

def test_missing_scoreline_is_not_imputed():
    result=summarize({'teamId':1,'requestedCount':47,'selectedCount':2,
                      'matches':[match(2,1,2,None,None),match(1,2,1,0,1)]})
    assert result['scoredCount']==1
    assert result['warning']
    assert result['goalsForPerMatch']==1

def test_no_matches_does_not_divide_by_zero():
    result=summarize({'teamId':1,'requestedCount':13,'selectedCount':0,'matches':[]})
    assert result['pointsPerMatch'] is None
    assert result['chronologicalMatches']==[]
