# FootballIQ: Real match preflight

This is a local validation workflow, **not evidence that the real match has already been downloaded or checked**.

1. Download the StatsBomb Open Data event JSON for match 3773386 from the official open-data repository:
   `https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/3773386.json`
2. Place the file in `backend/data/3773386.json` (create `data/` first).
3. In `backend/` run:

   ```bash
   python3 real_match_preflight.py data/3773386.json --output data/preflight-3773386.json
   ```

4. Review `status`, team IDs, event totals, invalid/duplicate IDs, coordinate errors, and SHA-256. **Match identity remains unverified** until separately checked against StatsBomb match metadata and another provider.
5. Only if status is `structurally_valid`, configure the historical endpoints:

   ```bash
   export FOOTBALLIQ_HISTORICAL_EVENTS="$PWD/data/3773386.json"
   ```

   Then run the existing FastAPI app as documented in README. Historical APIs read this file; this is not a live LaLiga feed.

Security: Do not commit downloaded datasets or credentials. Confirm StatsBomb's applicable open-data attribution and license terms before redistribution.
