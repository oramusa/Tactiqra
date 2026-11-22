# FootballIQ v1.9 — Offline-to-API validation

## What was verified

- `pytest -q` from `backend/`: 12 passed (synthetic/contract tests).
- A synthetic StatsBomb-shaped JSON file ran through `local_pipeline.py`, producing a report, CSV and SHA-256 manifest.
- The report was loaded by the FastAPI Evidence summary, transitions, and review-export endpoints using TestClient.
- The pipeline rejects an empty JSON array without producing a report.

## Real LaLiga pilot (not yet executed)

1. Obtain `data/events/3773386.json` from the official `hudl/open-data` GitHub repository, respecting its terms.
2. Run from `backend/`:

```bash
python3 -m pip install -r requirements.txt
python3 local_pipeline.py --events /absolute/path/3773386.json --match-id 3773386 --output-dir ./results
FOOTBALLIQ_PILOT_REPORT="$PWD/results/pilot_report.json" uvicorn app.main:app --reload
```

3. Run frontend separately using `npm install && npm run dev` (not verified here).
4. Review the exported `results/manual_review.csv` against original provider events. Fill the blank reviewer fields. A CSV with 10 rows is **not** evidence that 10 cases were validated.

## Boundaries

- No production database changed; PostgreSQL schema is not migrated.
- No full-match tactical accuracy claims or commercial data license implied.
- Local report API is not production-safe for public deployment without access controls.
- Match source SHA-256 is captured in the report and manifest; SHA-256 establishes file identity, not correctness.
