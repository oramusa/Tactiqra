from match_identity import verify_match_identity

FD = {'id': 12, 'utcDate': '2020-10-31T20:00:00Z', 'homeTeam': {'id': 1}, 'awayTeam': {'id': 2}, 'score': {'fullTime': {'home': 1, 'away': 1}}}
SB = {'match_id': 3773386, 'kickoff_utc': '2020-10-31T20:00:00+00:00', 'home_team': {'home_team_id': 101}, 'away_team': {'away_team_id': 202}, 'home_score': 1, 'away_score': 1}
M = {'1': 101, '2': 202}

def test_consistent_metadata():
    assert verify_match_identity(FD, SB, M)['status'] == 'metadata_consistent'

def test_reversed_teams_rejected():
    assert 'team_mapping_mismatch' in verify_match_identity(FD, SB, {'1':202, '2':101})['reasons']

def test_wrong_date_rejected():
    assert 'date_mismatch' in verify_match_identity(FD, {**SB, 'kickoff_utc':'2020-11-01T20:00:00Z'}, M)['reasons']

def test_wrong_score_rejected():
    assert 'score_mismatch' in verify_match_identity(FD, {**SB, 'away_score':2}, M)['reasons']

def test_no_timezone_rejected():
    assert 'missing_utc_kickoff' in verify_match_identity(FD, {**SB, 'kickoff_utc':'2020-10-31T20:00:00'}, M)['reasons']

def test_no_team_mapping_rejected():
    assert 'team_mapping_mismatch' in verify_match_identity(FD, SB, {})['reasons']

def test_missing_score_rejected():
    assert 'missing_or_invalid_score' in verify_match_identity({**FD, 'score': {}}, SB, M)['reasons']
