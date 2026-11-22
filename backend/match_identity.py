"""Conservative cross-provider match identity verification; no fuzzy matching."""
from datetime import datetime, timezone


def _date(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc).date()
    except ValueError:
        return None


def verify_match_identity(football_data, statsbomb, team_mapping):
    """Compare independently supplied match metadata with explicit provider team-ID mapping.

    This does NOT authenticate the origin of either metadata record. Reject unknown
    or ambiguous mappings, incomplete teams, and conflicting dates/scores.
    """
    failures = []
    if not isinstance(football_data, dict) or not isinstance(statsbomb, dict) or not isinstance(team_mapping, dict):
        return {'status': 'unverified', 'reasons': ['invalid_input']}
    fd_home = (football_data.get('homeTeam') or {}).get('id')
    fd_away = (football_data.get('awayTeam') or {}).get('id')
    sb_home = (statsbomb.get('home_team') or {}).get('home_team_id')
    sb_away = (statsbomb.get('away_team') or {}).get('away_team_id')
    if any(type(x) is not int or x <= 0 for x in (fd_home, fd_away, sb_home, sb_away)) or fd_home == fd_away or sb_home == sb_away:
        failures.append('invalid_team_ids')
    elif team_mapping.get(str(fd_home)) != sb_home or team_mapping.get(str(fd_away)) != sb_away or sb_home == sb_away:
        failures.append('team_mapping_mismatch')
    # Date-only StatsBomb kickoff can be missing; never silently assume timezone.
    fd_day = _date(football_data.get('utcDate'))
    sb_day = _date(statsbomb.get('kickoff_utc'))
    if fd_day is None or sb_day is None:
        failures.append('missing_utc_kickoff')
    elif fd_day != sb_day:
        failures.append('date_mismatch')
    fd_score = football_data.get('score', {}).get('fullTime') or {}
    sb_score = (statsbomb.get('home_score'), statsbomb.get('away_score'))
    if any(type(x) is not int or x < 0 for x in (fd_score.get('home'), fd_score.get('away'), *sb_score)):
        failures.append('missing_or_invalid_score')
    elif (fd_score['home'], fd_score['away']) != sb_score:
        failures.append('score_mismatch')
    if not football_data.get('id') or not statsbomb.get('match_id'):
        failures.append('missing_match_id')
    return {'status': 'metadata_consistent' if not failures else 'unverified',
            'reasons': failures, 'football_data_match_id': football_data.get('id'),
            'statsbomb_match_id': statsbomb.get('match_id'),
            'warning': 'Metadata consistency does not authenticate providers or verify event provenance.'}
