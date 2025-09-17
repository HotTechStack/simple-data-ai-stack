-- init-scripts/01-create-nocodb-db.sql
-- This script creates the NocoDB database automatically

-- Create NocoDB database if it doesn't exist
SELECT 'CREATE DATABASE nocodb' 
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nocodb')\gexec

-- Grant permissions to the main user
GRANT ALL PRIVILEGES ON DATABASE nocodb TO postgres;

-- Optional: Create a dedicated user for NocoDB (more secure)
-- DO $$
-- BEGIN
--   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nocodb_user') THEN
--     CREATE ROLE nocodb_user LOGIN PASSWORD 'nocodb_password';
--   END IF;
-- END
-- $$;

-- GRANT ALL PRIVILEGES ON DATABASE nocodb TO nocodb_user;