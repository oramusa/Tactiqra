"""Explicit, source-bound direction metadata; never infer directions from events."""
import hashlib
import json
from pathlib import Path

class DirectionMetadataError(ValueError):
    pass

def load_verified_directions(metadata_path: Path, events_path: Path, team_id: int):
    """Require a reviewed mapping tied to exact event bytes and selected team."""
    try:
        obj = json.loads(metadata_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise DirectionMetadataError('Direction metadata unavailable or invalid') from exc
    if not isinstance(obj, dict) or obj.get('verification_status') != 'manually_verified':
        raise DirectionMetadataError('Direction metadata must be manually verified')
    source = obj.get('source_sha256')
    if not isinstance(source, str) or len(source) != 64 or source != hashlib.sha256(events_path.read_bytes()).hexdigest():
        raise DirectionMetadataError('Direction metadata source checksum mismatch')
    if not isinstance(obj.get('evidence_note'), str) or not obj['evidence_note'].strip():
        raise DirectionMetadataError('Direction evidence note required')
    teams = obj.get('teams')
    if not isinstance(teams, dict) or str(team_id) not in teams:
        raise DirectionMetadataError('No verified direction for selected team')
    periods = teams[str(team_id)]
    if not isinstance(periods, dict) or not periods:
        raise DirectionMetadataError('Invalid direction mapping')
    directions = {}
    for key, value in periods.items():
        if key not in ('1','2','3','4','5') or value not in ('left_to_right','right_to_left'):
            raise DirectionMetadataError('Invalid direction mapping')
        directions[int(key)] = value
    return directions, {'verification_status': 'manually_verified', 'evidence_note': obj['evidence_note'], 'source_sha256': source}
