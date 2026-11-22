"""Conservative live-ball turnover verification and defensive transition detection.

Only explicit positive control evidence qualifies; all other boundaries remain review.
This is a fixture-tested prototype, not a certified StatsBomb possession model.
"""
from __future__ import annotations
from typing import Any

STOP = {'out', 'half_end', 'foul_committed', 'offside', 'injury_stoppage', 'referee_ball_drop'}
CONTROL = {'ball_recovery', 'interception', 'ball_receipt', 'carry', 'pass', 'dribble'}
RESTART = {'From Corner', 'From Free Kick', 'From Throw In', 'From Goal Kick', 'From Kick Off', 'From Penalty'}


def verify_turnovers(events: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strict rule: explicit gain event + continuous open play + no prior stoppage.

    Provider possession annotations alone never count. Certain events may be
    ambiguous in real data; expert validation is required before production.
    """
    by_id = {e['event_id']: e for e in events}
    ordered = sorted(events, key=lambda e: (e['match_id'], e['period'], e['timestamp_ms'], e['provider_index']))
    positions = {e['event_id']: i for i, e in enumerate(ordered)}
    out = []
    for candidate in candidates:
        c = dict(candidate)
        c['verification_status'] = 'needs_review'
        start = by_id.get(c['boundary_event_id'])
        idx = positions.get(c['boundary_event_id'])
        if start is None or idx is None or idx == 0:
            c['reason'] = 'missing boundary context'
        else:
            prior = ordered[idx-1]
            same_context = prior['match_id'] == start['match_id'] and prior['period'] == start['period']
            if not same_context or c.get('possible_stoppage') or prior['event_type'] in STOP or start['event_type'] in STOP:
                c['reason'] = 'stoppage or period boundary'
            elif start.get('play_pattern') in RESTART:
                c['reason'] = 'restart possession, not open-play turnover'
            elif start['event_type'] not in CONTROL or start.get('team_id') != c['gaining_team_id']:
                c['reason'] = 'no explicit gain-team control evidence'
            elif start.get('outcome') in {'Incomplete', 'Lost', 'Unsuccessful'}:
                c['reason'] = 'gain event outcome does not establish control'
            else:
                c['verification_status'] = 'provisional_verified'
                c['reason'] = 'explicit gain-team control event in contiguous open play; requires match-level review'
        out.append(c)
    return out


def detect_transitions(events: list[dict[str, Any]], turnovers: list[dict[str, Any]], window_seconds: int = 10) -> list[dict[str, Any]]:
    if window_seconds not in (5, 8, 10, 12):
        raise ValueError('window_seconds must be one of 5,8,10,12')
    ordered = sorted(events, key=lambda e: (e['match_id'], e['period'], e['timestamp_ms'], e['provider_index']))
    by_id = {e['event_id']: i for i, e in enumerate(ordered)}
    results = []
    seen = set()
    for t in turnovers:
        if t['verification_status'] != 'provisional_verified':
            continue
        key = (t['match_id'], t['period'], t['boundary_event_id'], window_seconds)
        if key in seen:
            continue
        seen.add(key)
        idx = by_id.get(t['boundary_event_id'])
        if idx is None:
            continue
        start = ordered[idx]
        evidence = []
        shot = goal = False
        end_reason = 'window_expired'
        for e in ordered[idx:]:
            if e['match_id'] != start['match_id'] or e['period'] != start['period']:
                end_reason = 'match_or_period_boundary'; break
            dt = e['timestamp_ms'] - start['timestamp_ms']
            if dt > window_seconds * 1000:
                break
            if e['event_type'] in STOP or (e is not start and e.get('play_pattern') in RESTART):
                end_reason = 'stoppage_or_restart'; break
            if e['possession_team_id'] != t['gaining_team_id']:
                end_reason = 'possession_changed'; break
            evidence.append(e['event_id'])
            if e['event_type'] == 'shot' and e.get('team_id') == t['gaining_team_id']:
                shot = True
                if e.get('outcome') == 'Goal':
                    goal = True
        results.append({'match_id': t['match_id'], 'period': t['period'],
                        'start_event_id': t['boundary_event_id'], 'losing_team_id': t['losing_team_id'],
                        'gaining_team_id': t['gaining_team_id'], 'window_seconds': window_seconds,
                        'shot': shot, 'goal': goal, 'evidence_event_ids': evidence,
                        'end_reason': end_reason, 'verification_status': 'provisional',
                        'algorithm_version': 'transition-prototype-1.0'})
    return results
