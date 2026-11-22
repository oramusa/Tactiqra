# FootballIQ v1.7 validation

- Backend: `cd backend && pytest -q` => 8 passed (2026-11-12).
- Frontend: `npm run build` attempted, blocked by missing installed React / @types/react dependencies; not a verified build. Install dependencies before retrying.
- New checks: report match ID, event count, transition evidence ID type, verification status, cross-match references. Invalid reports return HTTP 503 rather than misleading evidence.
- Historical match analysis: NOT performed in this version; no real-world tactical accuracy claim.
- PostgreSQL migration: NOT applied.
- Do not deploy without auth, validated licensed data and manual evidence review.
