# FootballIQ — LaLiga Starter (Sprint 01)

Docker-free Mac development starter. **Current capabilities:** FastAPI health check, live LaLiga team lookup through football-data.org, React dark-mode team search, and a PostgreSQL starter schema. **Not yet implemented:** DB persistence/sync, match history, analytics, scouting reports, authentication, rate-limit retry.

## Prerequisites
- Node.js 20.19+ or 22+
- Python 3.11+
- PostgreSQL 14+
- football-data.org API token

## Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API key (never commit it)
set -a; source .env; set +a
uvicorn app.main:app --reload --port 8000
```
Open http://127.0.0.1:8000/api/health .

## Frontend (second terminal)
```bash
cd frontend
npm install
npm run dev
```
Open http://127.0.0.1:5173 .

## PostgreSQL (optional in first run)
```bash
createdb footballiq
psql footballiq -f database/001_init.sql
```
Run the database commands from the repository root. The current API reads the provider directly and does not yet write to PostgreSQL. DB ingestion is the next milestone.

## Security
- API key is server-side only.
- `.env` is gitignored.
- External provider errors are sanitized.
- Verify provider licensing before production redistribution.

## OpponentIQ UI (Sprint 01 design integration)
The frontend now includes team selection, last five finished LaLiga matches, deterministic W/D/L and goals summary, and an explicitly disabled scouting panel. All match data is fetched from the provider; no invented statistics. The API route is `GET /api/laliga/teams/{team_id}/recent-matches?limit=5`. Requires `FOOTBALL_DATA_API_KEY` and the provider's permission to access these endpoints. The provider's commercial licensing and API coverage must be checked before launch. This version does not persist match data to PostgreSQL yet.

## OpponentIQ v2 — selectable analysis window
Choose 5/10/20/30/38/50/100 matches (20 default), home/away/all. The backend validates and filters the requested finished LaLiga matches. Coverage and missing-data states are shown. Tactical Pattern tabs are placeholders, not invented analyses. The provider may return fewer than requested and may limit the available historical window. No PostgreSQL ingestion or tracking/event analysis is implemented yet.

Backend unit test: `cd backend && python -m unittest test_pattern.py`. Frontend: `cd frontend && npm install && npm run build`.
