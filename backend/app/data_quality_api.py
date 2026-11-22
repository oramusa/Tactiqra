"""Read-only, explicitly scoped status of the configured historical StatsBomb event file."""
import os
from pathlib import Path
from fastapi import APIRouter
from real_match_preflight import inspect_file

router = APIRouter(prefix='/api/v1/data-quality', tags=['data-quality'])

@router.get('/historical-events')
def historical_events_quality():
    configured = os.getenv('FOOTBALLIQ_HISTORICAL_EVENTS', '').strip()
    if not configured:
        return {'status': 'not_configured', 'message': 'No local historical event file configured', 'match_identity_verified': False}
    path = Path(configured)
    try:
        result = inspect_file(path)
    except (ValueError, OSError, UnicodeError, TypeError) as exc:
        return {'status': 'rejected', 'message': 'Configured event file could not be validated', 'match_identity_verified': False}
    return {'status': result['status'], 'match_identity_verified': False,
            'events': result['events'], 'teams': result['teams'],
            'failures': result['failures'], 'sha256': result['sha256'],
            'identity_status': result['identity_status'],
            'message': result['note']}
