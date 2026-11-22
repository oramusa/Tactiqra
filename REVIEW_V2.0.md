# FootballIQ v2.0 — Human review quality gate

1. Run `python local_pipeline.py --events /absolute/path/3773386.json --match-id 3773386 --output-dir results` in `backend/`.
2. Open `results/manual_review.csv`. For each candidate, inspect the corresponding **original StatsBomb event sequence**, enter `correct`, `false_positive`, or `uncertain` in `review_decision`, and explain why in `review_notes`.
3. Run `python review_gate.py --report results/pilot_report.json --reviewed-csv results/manual_review.csv --output results/review_quality.json`.
4. The report shows candidate **sample precision** only. It does **not** estimate recall or full-match accuracy, because missed turnovers are not measured.

Do not use provisional findings as verified coaching advice. Open data license is not a commercial license grant. Database migrations and frontend production build are not validated in this package.
