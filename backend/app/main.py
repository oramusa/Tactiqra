import os
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .evidence_api import router as evidence_router
from .heatmap_api import router as heatmap_router
from match_trends import summarize
BASE = 'https://api.football-data.org/v4'

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=20) as client:
        app.state.client = client
        yield

app = FastAPI(title='FootballIQ API', lifespan=lifespan)
app.include_router(evidence_router)
app.include_router(heatmap_router)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173'], allow_methods=['GET'], allow_headers=['*'])

@app.get('/api/health')
def health():
    return {'status': 'ok'}

@app.get('/api/laliga/teams')
async def teams():
    token = os.getenv('FOOTBALL_DATA_API_KEY')
    if not token:
        raise HTTPException(503, 'FOOTBALL_DATA_API_KEY is not configured')
    try:
        response = await app.state.client.get(f'{BASE}/competitions/PD/teams', headers={'X-Auth-Token': token})
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise HTTPException(429 if status == 429 else 502, 'Football data provider request failed') from exc
    except httpx.RequestError as exc:
        raise HTTPException(502, 'Football data provider unavailable') from exc
    payload = response.json()
    return {'competition': 'PD', 'teams': [{'id': t['id'], 'name': t['name'], 'shortName': t.get('shortName'), 'crest': t.get('crest')} for t in payload.get('teams', [])]}

def normalize_matches(raw_matches, team_id: int, limit: int, venue: str):
    # Do not trust the provider to return only matches involving the requested team.
    # Duplicate match IDs can otherwise inflate the apparent history coverage.
    eligible = []
    seen_ids = set()
    for m in sorted(raw_matches, key=lambda item: (item.get('utcDate') or '', item.get('id') or 0), reverse=True):
        if not isinstance(m, dict) or m.get('competition', {}).get('code') != 'PD' or m.get('status') != 'FINISHED':
            continue
        home = m.get('homeTeam') or {}
        away = m.get('awayTeam') or {}
        match_id = m.get('id')
        if match_id is None or match_id in seen_ids or team_id not in (home.get('id'), away.get('id')):
            continue
        if venue == 'home' and home.get('id') != team_id:
            continue
        if venue == 'away' and away.get('id') != team_id:
            continue
        if not home.get('id') or not away.get('id'):
            continue
        seen_ids.add(match_id)
        eligible.append(m)
        if len(eligible) == limit:
            break
    return [{
        'id': m['id'], 'utcDate': m.get('utcDate'),
        'homeTeam': {'id': m['homeTeam']['id'], 'name': m['homeTeam']['name']},
        'awayTeam': {'id': m['awayTeam']['id'], 'name': m['awayTeam']['name']},
        'homeGoals': (m.get('score', {}).get('fullTime') or {}).get('home'),
        'awayGoals': (m.get('score', {}).get('fullTime') or {}).get('away'),
    } for m in eligible]

@app.get('/api/laliga/teams/{team_id}/recent-matches')
async def recent_matches(team_id: int, limit: int = Query(20, ge=1, le=100), venue: str = 'all'):
    if venue not in ('all', 'home', 'away'):
        raise HTTPException(422, 'venue must be all, home or away')
    token = os.getenv('FOOTBALL_DATA_API_KEY')
    if not token:
        raise HTTPException(503, 'FOOTBALL_DATA_API_KEY is not configured')
    try:
        # Request a broader window for venue filtering. Provider may impose its own limits.
        response = await app.state.client.get(
            f'{BASE}/teams/{team_id}/matches',
            params={'competitions': 'PD', 'status': 'FINISHED', 'limit': min(100, limit * (3 if venue != 'all' else 1))},
            headers={'X-Auth-Token': token},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(429 if exc.response.status_code == 429 else 502, 'Football data provider request failed') from exc
    except httpx.RequestError as exc:
        raise HTTPException(502, 'Football data provider unavailable') from exc
    payload = response.json()
    provider_matches = payload.get('matches', [])
    matches = normalize_matches(provider_matches, team_id, limit, venue)
    return {'teamId': team_id, 'competition': 'PD', 'requestedCount': limit,
            'selectedCount': len(matches), 'venue': venue, 'matches': matches,
            'coverageNote': 'Provider response does not contain enough eligible matches; this does not prove older matches do not exist.' if len(matches) < limit else None,
            'coverage': {'requested': limit, 'selected': len(matches),
                         'ratio': round(len(matches) / limit, 4),
                         'complete': len(matches) == limit,
                         'providerReturned': len(provider_matches),
                         'providerRequestLimit': min(100, limit * (3 if venue != 'all' else 1)),
                         'source': 'football-data.org', 'competition': 'PD',
                         'scoreOnly': True}}


@app.get('/api/v1/opponentiq/match-windows')
async def independent_match_windows(
    own_team_id: int = Query(..., gt=0), opponent_team_id: int = Query(..., gt=0),
    own_match_limit: int = Query(20, ge=1, le=100),
    opponent_match_limit: int = Query(10, ge=1, le=100),
    own_venue: str = 'all', opponent_venue: str = 'all',
):
    """Separate team-specific history windows; no invented event-based metrics."""
    if own_team_id == opponent_team_id:
        raise HTTPException(422, 'Select two distinct teams')
    if own_venue not in ('all', 'home', 'away') or opponent_venue not in ('all', 'home', 'away'):
        raise HTTPException(422, 'Invalid venue filter')
    own = await recent_matches(own_team_id, own_match_limit, own_venue)
    opponent = await recent_matches(opponent_team_id, opponent_match_limit, opponent_venue)
    return {
        'status': 'match_selection_only',
        'own': own, 'opponent': opponent,
        'trends': {'own': summarize(own), 'opponent': summarize(opponent)},
        'comparison_ready': bool(own['selectedCount'] and opponent['selectedCount']),
        'coverage': {'ownComplete': own['selectedCount'] == own['requestedCount'],
                     'opponentComplete': opponent['selectedCount'] == opponent['requestedCount'],
                     'bothComplete': own['selectedCount'] == own['requestedCount'] and opponent['selectedCount'] == opponent['requestedCount']},
        'warning': 'Scoreline trends only; event heatmaps and tactical metrics require separately licensed, matched event data. Current provider endpoint is LaLiga-only.',
    }

from app.event_coverage_api import router as event_coverage_router
app.include_router(event_coverage_router)

from .tactical_batch_api import router as tactical_batch_router
app.include_router(tactical_batch_router)

from app.event_explorer_api import router as event_explorer_router
app.include_router(event_explorer_router)

from app.evidence_chain_api import router as evidence_chain_router
app.include_router(evidence_chain_router)

from .data_quality_api import router as data_quality_router
app.include_router(data_quality_router)

from .match_event_report_api import router as match_event_report_router
app.include_router(match_event_report_router)

from .possession_sequence_api import router as possession_sequence_router
app.include_router(possession_sequence_router)

from .transition_candidate_api import router as transition_candidate_router
app.include_router(transition_candidate_router)

from .historical_multi_match_api import router as historical_multi_match_router
app.include_router(historical_multi_match_router)
