-- Read-only role for the text-to-SQL agent (W3 D1). Run as a superuser after dbt build.
-- The LLM's SQL only ever runs as this role: SELECT on marts, nothing else, 10s timeout.
-- Idempotent: safe to run on every seed.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'crickql_reader') THEN
        CREATE ROLE crickql_reader LOGIN PASSWORD 'crickql_reader';
    END IF;
END $$;

ALTER ROLE crickql_reader SET statement_timeout = '10s';
ALTER ROLE crickql_reader SET default_transaction_read_only = on;
ALTER ROLE crickql_reader SET search_path = marts;

REVOKE ALL ON SCHEMA public FROM crickql_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA raw FROM crickql_reader;
REVOKE ALL ON SCHEMA raw FROM crickql_reader;

GRANT USAGE ON SCHEMA marts TO crickql_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO crickql_reader;
-- dbt recreates tables on every build, so grant on future tables too.
-- Assumes dbt runs as the role executing this script.
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO crickql_reader;
