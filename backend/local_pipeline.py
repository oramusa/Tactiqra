"""One-command offline event JSON -> report -> review CSV; never downloads data."""
import argparse
import hashlib
import json
from pathlib import Path
from pilot_runner import analyze
from review_export import export_review


def run_pipeline(events_path: Path, output_dir: Path, match_id: str, window: int = 10):
    if window not in (5, 8, 10, 12):
        raise ValueError('Unsupported window')
    source = events_path.read_bytes()
    events = json.loads(source)
    if not isinstance(events, list) or not events:
        raise ValueError('Events must be a nonempty JSON array')
    sha256 = hashlib.sha256(source).hexdigest()
    report = analyze(events, match_id, 'sha256:' + sha256, window)
    # Analyze before writing: invalid source should not leave a misleading report.
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / 'pilot_report.json'
    review_path = output_dir / 'manual_review.csv'
    manifest_path = output_dir / 'source_manifest.json'
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    count = export_review(report_path, review_path, limit=10)
    manifest_path.write_text(json.dumps({
        'match_id': str(match_id), 'source_sha256': sha256,
        'source_bytes': len(source), 'source_event_count': len(events),
        'review_rows_exported': count, 'manual_review_completed': False,
        'tactical_accuracy_measured': False,
    }, indent=2) + '\n', encoding='utf-8')
    return {'report': str(report_path), 'review_csv': str(review_path),
            'manifest': str(manifest_path), 'review_rows': count}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--events', type=Path, required=True)
    p.add_argument('--match-id', required=True)
    p.add_argument('--output-dir', type=Path, default=Path('results'))
    p.add_argument('--window', type=int, choices=[5, 8, 10, 12], default=10)
    args = p.parse_args()
    print(json.dumps(run_pipeline(args.events, args.output_dir, args.match_id, args.window), indent=2))
