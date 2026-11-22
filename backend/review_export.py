"""Generate reproducible human-review worksheets from a provisional pilot report."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

FIELDS = ['review_id','match_id','period','start_event_id','losing_team_id','gaining_team_id','window_seconds','shot_predicted','goal_predicted','end_reason','evidence_event_ids','reviewer_verdict','actual_open_play_turnover','actual_shot_within_window','notes']

def select_review_cases(report, limit=10):
    if limit < 1:
        raise ValueError('limit must be positive')
    transitions = report.get('transitions', [])
    if not isinstance(transitions, list):
        raise ValueError('transitions must be a list')
    # Deterministic, diverse: shots first, then other cases; stable hash prevents input-order bias.
    def order(t):
        identifier = f"{t.get('match_id')}|{t.get('period')}|{t.get('start_event_id')}"
        return (not bool(t.get('shot')), hashlib.sha256(identifier.encode()).hexdigest())
    chosen = sorted(transitions, key=order)[:limit]
    rows = []
    for t in chosen:
        rows.append({
            'review_id': f"R{len(rows)+1:03d}", 'match_id': t.get('match_id',''),
            'period': t.get('period',''), 'start_event_id': t.get('start_event_id',''),
            'losing_team_id': t.get('losing_team_id',''), 'gaining_team_id': t.get('gaining_team_id',''),
            'window_seconds': t.get('window_seconds',''), 'shot_predicted': t.get('shot',False),
            'goal_predicted': t.get('goal',False), 'end_reason': t.get('end_reason',''),
            'evidence_event_ids': '|'.join(map(str,t.get('evidence_event_ids',[]))),
            'reviewer_verdict':'', 'actual_open_play_turnover':'', 'actual_shot_within_window':'', 'notes':''
        })
    return rows

def spreadsheet_safe(value):
    # Treat untrusted provider strings as data when opened in Excel/Sheets.
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value

def export_review(report_path, output_path, limit=10):
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    rows = select_review_cases(report, limit)
    with Path(output_path).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows([{k: spreadsheet_safe(v) for k, v in row.items()} for row in rows])
    return len(rows)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--limit', type=int, default=10)
    a = p.parse_args()
    n = export_review(a.report,a.output,a.limit)
    print(f'Exported {n} provisional cases. Review manually; no accuracy claim is implied.')
