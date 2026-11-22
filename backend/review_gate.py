"""Independent human review gate. Never turns candidate count into measured accuracy."""
import argparse
import csv
import json
from pathlib import Path

DECISIONS = {'correct', 'false_positive', 'uncertain'}

def evaluate(report_path: Path, reviewed_csv: Path, min_reviews: int = 10):
    report = json.loads(report_path.read_text(encoding='utf-8'))
    candidates = report.get('transitions', [])
    if not isinstance(candidates, list):
        raise ValueError('Invalid transition report')
    allowed = {str(x.get('start_event_id')) for x in candidates if isinstance(x, dict)}
    seen = set()
    decisions = []
    with reviewed_csv.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            decision = (row.get('review_decision') or '').strip().lower()
            if not decision:
                continue
            event_id = (row.get('start_event_id') or '').strip()
            if event_id not in allowed or event_id in seen:
                raise ValueError('Unknown or duplicate reviewed candidate: ' + event_id)
            if str(row.get('match_id')) != str(report.get('match_id')):
                raise ValueError('Reviewed row belongs to a different match')
            if decision not in DECISIONS:
                raise ValueError('Unsupported review decision: ' + decision)
            if not (row.get('review_notes') or '').strip():
                raise ValueError('Reviewed row requires explanatory notes')
            seen.add(event_id)
            decisions.append(decision)
    correct = decisions.count('correct')
    false_positive = decisions.count('false_positive')
    uncertain = decisions.count('uncertain')
    conclusive = correct + false_positive
    return {
        'match_id': str(report.get('match_id')),
        'reviewed_count': len(decisions),
        'correct_count': correct,
        'false_positive_count': false_positive,
        'uncertain_count': uncertain,
        'review_target': min_reviews,
        'review_target_met': len(decisions) >= min_reviews,
        'sample_precision': round(correct / conclusive, 4) if conclusive else None,
        'sample_precision_denominator': conclusive,
        'recall_measured': False,
        'independent_full_match_accuracy_measured': False,
        'status': 'sample_review_complete' if len(decisions) >= min_reviews and conclusive else 'review_incomplete',
        'warning': 'Sample precision only covers manually reviewed candidate transitions. Recall and full-match accuracy are unknown.'
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--reviewed-csv', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('review_quality.json'))
    args = parser.parse_args()
    result = evaluate(args.report, args.reviewed_csv)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
