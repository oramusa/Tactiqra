# FootballIQ v2.6 — Historical event heatmap pilot

- New deterministic StatsBomb raw event-location density grid (12x8 by default) for team and/or player ID; event type filter; event-ID evidence for every occupied grid cell.
- New local-only read-only API `GET /api/v1/heatmap/events?team_id=<StatsBomb team id>`; optional `player_id`, `event_type`, `columns`, `rows`.
- Set `FOOTBALLIQ_HISTORICAL_EVENTS=/absolute/path/to/3773386.json` in the backend environment before starting it.
- The frontend has a **separate historical pilot panel**, deliberately not tied to current football-data.org LaLiga selection (the providers use different IDs).
- This map is **not tracking data**, not direction-normalized, not a multi-match aggregation, and does not measure time spent in zones. Never present it as player movement intensity.
- For multi-match heatmaps, implement match-by-match attack-direction normalization and match/minute denominators before comparisons.
- No real full-match heatmap was generated in this environment. Tests use synthetic fixtures.
