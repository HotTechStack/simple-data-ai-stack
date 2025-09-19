-- PostgreSQL initialization script for DuckLake catalog
-- This runs automatically when the container starts

-- Ensure the ducklake_catalog database exists
-- (Already created via POSTGRES_DB env var, but good to be explicit)

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE ducklake_catalog TO postgres;

-- Set up any additional configuration
ALTER DATABASE ducklake_catalog SET timezone = 'UTC';

-- Create extension for better performance (optional)
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Log that setup is complete
DO $$
BEGIN
    RAISE NOTICE 'DuckLake catalog database initialized successfully';
END $$;
