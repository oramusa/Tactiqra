"""Offline historical match pilot; NO data download or commercial-use grant."""
import argparse
import json
from pathlib import Path
from statsbomb_adapter import normalize_match
from possession_engine import segment_possessions, transition_candidates
from transition_engine import verify_turnovers, detect_transitions


def analyze(events, match_id, source_id, window=10):
    if not isinstance(events, list) or not events:
        raise ValueError('Expected a nonempty StatsBomb events JSON array')
    normalized = normalize_match(events, str(match_id), source_id)
    segments = segment_possessions(normalized)
    candidates = transition_candidates(segments)
    verified = verify_turnovers(normalized, candidates)
    transitions = detect_transitions(normalized, verified, window)
    statuses = {'provisional_verified': 0, 'needs_review': 0}
    for v in verified:
        statuses[v['verification_status']] = statuses.get(v['verification_status'], 0) + 1
    return {
        'match_id': str(match_id), 'source_record_id': source_id,
        'data_status': 'historical_pilot_unreviewed',
        'event_count': len(normalized), 'possession_segment_count': len(segments),
        'candidate_turnover_count': len(candidates), 'turnover_status_counts': statuses,
        'provisional_transition_count': len(transitions),
        'provisional_shot_count': sum(bool(t['shot']) for t in transitions),
        'provisional_goal_count': sum(bool(t['goal']) for t in transitions),
        'transitions': transitions,
        'warnings': [
            'These results are provisional; StatsBomb possession annotations do not certify live-ball turnovers.',
            'Manual expert review and provider licensing verification required before customer-facing use.',
            'No independent coverage or ground-truth accuracy measurement has been performed.'
        ]
    }


def main():
    p = argparse.ArgumentParser(description='Analyze a locally supplied StatsBomb events JSON file')
    p.add_argument('--events', required=True, type=Path)
    p.add_argument('--match-id', required=True)
    p.add_argument('--source-id', default='local-historical-fixture')
    p.add_argument('--window', type=int, choices=[5, 8, 10, 12], default=10)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    report = analyze(json.loads(args.events.read_text(encoding='utf-8')), args.match_id, args.source_id, args.window)
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(serialized + '\n', encoding='utf-8')
        print(f'Wrote {args.output}')
    else:
        print(serialized)

if __name__ == '__main__':
    main()
