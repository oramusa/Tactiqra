"""Fetch a public historical match and run integrity checks; no tactical accuracy claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from local_pipeline import run_pipeline
from verify_artifacts import verify

BASE = 'https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/'
MAX_BYTES = 30_000_000

def download_match(match_id: str, destination: Path, opener=urlopen):
    if not match_id.isascii() or not match_id.isdecimal() or len(match_id) > 12:
        raise ValueError('Match ID must contain digits only')
    req = Request(BASE + match_id + '.json', headers={'User-Agent': 'FootballIQ-Historical-Research/0.1'})
    with opener(req, timeout=45) as response:
        length = response.headers.get('Content-Length')
        if length and int(length) > MAX_BYTES:
            raise ValueError('Source file exceeds 30 MB limit')
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Source file exceeds 30 MB limit')
    events = json.loads(data)
    if not isinstance(events, list) or not events:
        raise ValueError('Downloaded data must be a nonempty event array')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix('.tmp')
    try:
        temp.write_bytes(data)
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)
    return {'source': str(destination), 'sha256': hashlib.sha256(data).hexdigest(), 'events': len(events)}

def execute(match_id: str, directory: Path, opener=urlopen):
    raw = directory / 'source' / (match_id + '.json')
    downloaded = download_match(match_id, raw, opener=opener)
    result_dir = directory / 'results'
    produced = run_pipeline(raw, result_dir, match_id)
    checked = verify(raw, result_dir)
    return {'download': downloaded, 'outputs': produced, 'integrity': checked,
            'manual_review_complete': False, 'tactical_accuracy_measured': False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--match-id', default='3773386')
    parser.add_argument('--output-dir', type=Path, default=Path('historical_pilot'))
    args = parser.parse_args()
    print(json.dumps(execute(args.match_id, args.output_dir), indent=2))
