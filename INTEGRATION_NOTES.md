# FootballIQ OpponentIQ Evidence Integration v1.5

The existing OpponentIQ React/Vite frontend is connected to a read-only FastAPI historical pilot evidence API. Offline engine modules and a SQL schema draft are included.

Backend: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload`
Frontend: `cd frontend && npm install && npm run dev`
Optional before backend start: `export FOOTBALLIQ_PILOT_REPORT=/absolute/path/to/pilot_report.json`. Without this, the Evidence tab shows an insufficient-data state.

Historical pilot data is explicitly separate from the currently selected team. No fabricated demo statistics, no live event feed, no licensed commercial data, no database writes. The PostgreSQL schema has not been applied. Production requires organization auth, validated provider rights, data persistence and independent match-level validation.
