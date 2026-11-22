# v1.8: Evidence interoperability fix

Critical integration fix: the actual transition engine emits `verification_status: "provisional"` while v1.7's evidence API rejected it. v1.8 accepts that status without treating it as independently verified.

New read-only GET `/api/v1/evidence/review-export?limit=10` generates a CSV for expert review, with blank decision and notes fields. The UI exposes the download.

No full-match real-world validation, PostgreSQL migration, production build or commercial data license is claimed. Do not deploy publicly without authentication and authorization.
