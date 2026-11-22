# FootballIQ v2.5 — one-command historical pilot

From the `backend` directory, with Python dependencies installed:

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q
python3 download_and_validate.py --match-id 3773386 --output-dir historical_pilot
```

Outputs are in `backend/historical_pilot/source/3773386.json` and `backend/historical_pilot/results/` (`pilot_report.json`, `manual_review.csv`, `source_manifest.json`). The program checks source checksum and evidence references, but it **does not** independently certify tactical correctness. Human review of 10 real candidate transitions is still required. A network connection to raw.githubusercontent.com is needed. The sample match is historical and the tool does not include a commercial data license.
