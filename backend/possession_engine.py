"""Conservative StatsBomb possession segmentation; not a verified turnover detector.

StatsBomb possession_team is an annotation of the possession, not proof of
individual control at the instant of every event. Boundaries are candidates.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any

STOP_TYPES = {'half_end', 'out', 'foul_committed'}

def segment_possessions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group normalized events by match, period and contiguous possession ID.

    Preserve original source ordering; reject inconsistent possession annotations.
    Never infer a turnover from a segment boundary alone.
    """
    ordered = sorted(events, key=lambda e: (str(e['match_id']), int(e['period']), int(e['timestamp_ms']), int(e['provider_index'])))
    seen = set()
    segments: list[dict[str, Any]] = []
    for e in ordered:
        key = (e['match_id'], e['provider_event_id'])
        if key in seen:
            raise ValueError(f'duplicate event: {key}')
        seen.add(key)
        for field in ('match_id','period','timestamp_ms','provider_index','possession_id','possession_team_id','event_id'):
            if e.get(field) is None:
                raise ValueError(f'missing field {field}')
        group = (e['match_id'],e['period'],e['possession_id'])
        prev = segments[-1] if segments else None
        if prev and prev['_group'] == group:
            if prev['possession_team_id'] != e['possession_team_id']:
                raise ValueError('conflicting possession team for same possession')
            prev['event_ids'].append(e['event_id'])
            prev['end_timestamp_ms'] = e['timestamp_ms']
            prev['last_event_type'] = e['event_type']
        else:
            segments.append({
                '_group': group, 'match_id': e['match_id'], 'period': e['period'],
                'possession_id': e['possession_id'], 'possession_team_id': e['possession_team_id'],
                'start_timestamp_ms': e['timestamp_ms'], 'end_timestamp_ms': e['timestamp_ms'],
                'event_ids': [e['event_id']], 'first_event_type': e['event_type'],
                'last_event_type': e['event_type'], 'verification_status': 'annotation_only',
            })
    for s in segments:
        del s['_group']
    return segments


def transition_candidates(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find possession-team changes within a period; mark as needs_review.

    A candidate is NOT a verified live-ball turnover. A second pass must inspect
    boundary events, stoppages, play pattern, and actual control evidence.
    """
    candidates = []
    for before, after in zip(segments, segments[1:]):
        if before['match_id'] != after['match_id'] or before['period'] != after['period']:
            continue
        if before['possession_team_id'] == after['possession_team_id']:
            continue
        if after['start_timestamp_ms'] < before['end_timestamp_ms']:
            continue
        candidates.append({
            'match_id': after['match_id'], 'period': after['period'],
            'previous_possession_id': before['possession_id'],
            'next_possession_id': after['possession_id'],
            'losing_team_id': before['possession_team_id'],
            'gaining_team_id': after['possession_team_id'],
            'boundary_timestamp_ms': after['start_timestamp_ms'],
            'boundary_event_id': after['event_ids'][0],
            'verification_status': 'needs_review',
            'reason': 'possession annotation change alone does not prove live-ball control change',
            'possible_stoppage': before['last_event_type'] in STOP_TYPES or after['first_event_type'] in STOP_TYPES,
        })
    return candidates
