# Validation status — v1.6

- `cd backend && pytest -q`: **6 passed** (executed in this environment).
- Additional negative tests: malformed evidence ID list; invalid report transition structure.
- `cd frontend && npm install --offline && npm run build`: **not completed**. Required npm packages are not cached; registry access is unavailable. Do not claim a successful React build.
- PostgreSQL migration: **not applied**.
- Full historical LaLiga match processing and manual review of 10 positions: **not completed**.
- StatsBomb open data is historical pilot material; commercial licensing not established.

## Run on Mac

```bash
cd backend
python3 -m pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
# Separate terminal:
cd frontend
npm install
npm run build
npm run dev
```

Optional `FOOTBALLIQ_PILOT_REPORT=/absolute/path/to/pilot_report.json` is server-side only. No report means insufficient_data; no tactical findings are fabricated.
