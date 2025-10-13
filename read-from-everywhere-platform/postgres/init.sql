CREATE TABLE IF NOT EXISTS ingestion_runs (
    source_name TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    run_id TEXT NOT NULL,
    raw_object_key TEXT NOT NULL,
    processed_object_key TEXT NOT NULL,
    row_count INTEGER,
    schema_version INTEGER,
    schema_hash TEXT,
    succeeded_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_schemas (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    version INTEGER NOT NULL,
    schema_hash TEXT NOT NULL,
    schema JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source_name, version),
    UNIQUE (source_name, schema_hash)
);

CREATE TABLE IF NOT EXISTS ingestion_failures (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    run_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    error TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE VIEW ingestion_run_summary AS
SELECT
    source_name,
    row_count,
    schema_version,
    succeeded_at,
    raw_object_key,
    processed_object_key
FROM ingestion_runs;
