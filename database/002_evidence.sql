-- FootballIQ evidence storage; additive migration, no DROP operations.
CREATE TABLE IF NOT EXISTS fiq_source_records (
  source_record_id TEXT PRIMARY KEY, provider TEXT NOT NULL, match_id TEXT NOT NULL,
  sha256 CHAR(64) NOT NULL, source_uri TEXT, raw_payload JSONB NOT NULL,
  imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(provider, match_id, sha256)
);
CREATE TABLE IF NOT EXISTS fiq_analysis_runs (
  analysis_run_id UUID PRIMARY KEY, match_id TEXT NOT NULL,
  source_record_id TEXT NOT NULL REFERENCES fiq_source_records(source_record_id),
  algorithm_version TEXT NOT NULL, window_seconds SMALLINT NOT NULL CHECK (window_seconds IN (5,8,10,12)),
  status TEXT NOT NULL CHECK (status IN ('provisional','needs_review','validated','insufficient_data')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  report JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS fiq_transition_occurrences (
  analysis_run_id UUID NOT NULL REFERENCES fiq_analysis_runs(analysis_run_id) ON DELETE CASCADE,
  occurrence_id TEXT NOT NULL, start_event_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'provisional', outcome JSONB NOT NULL,
  PRIMARY KEY (analysis_run_id, occurrence_id)
);
CREATE TABLE IF NOT EXISTS fiq_transition_evidence (
  analysis_run_id UUID NOT NULL, occurrence_id TEXT NOT NULL,
  event_id TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  PRIMARY KEY (analysis_run_id, occurrence_id, event_id),
  FOREIGN KEY (analysis_run_id, occurrence_id)
    REFERENCES fiq_transition_occurrences(analysis_run_id, occurrence_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS fiq_analysis_runs_match_idx ON fiq_analysis_runs(match_id, created_at DESC);
