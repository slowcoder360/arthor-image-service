-- LOCAL DEV ONLY — NOT a canonical migration.
--
-- Stand-in for the arthor-agent "harness" tables (agent_runs, tool_calls) that
-- this service reads/writes but does NOT own. In real environments these are
-- owned by arthor-agent / the shared Neon schema (see plan/adr/0004-agent-runs-and-tool-calls.md
-- and system.yaml W11 absorb). DO NOT apply this to production or any shared DB.
--
-- Apply this FIRST, then the canonical chain:
--   psql "$DATABASE_URL" -f db/dev/000_local_harness_bootstrap.sql
--   psql "$DATABASE_URL" -f db/migrations/001_external_media_assets.sql
--   psql "$DATABASE_URL" -f db/migrations/002_image_request_payloads.sql
--   psql "$DATABASE_URL" -f db/migrations/003_tool_calls_cost_columns.sql

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Harness-flavored agent_runs (ADR-0004): cost/token counters + jsonb metadata.
-- No status CHECK and no parent_run_id FK, to mirror the harness shape and avoid
-- blocking this service's run_type/status literals.
CREATE TABLE IF NOT EXISTS agent_runs (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_type           text NOT NULL,
  status             text NOT NULL DEFAULT 'running',
  started_at         timestamptz NULL,
  finished_at        timestamptz NULL,
  cost_cents         int  NOT NULL DEFAULT 0,
  prompt_tokens      int  NOT NULL DEFAULT 0,
  completion_tokens  int  NOT NULL DEFAULT 0,
  metadata           jsonb NOT NULL DEFAULT '{}'::jsonb,
  parent_run_id      uuid NULL,
  site_id            uuid NULL,  -- local-dev only: test fixtures insert this; runtime keeps site_id in metadata
  created_at         timestamptz NOT NULL DEFAULT now()
);

-- Harness-flavored tool_calls (ADR-0004): FK column is run_id (NOT agent_run_id).
-- cost_cents / provider / model_version are intentionally omitted here — migration
-- 003_tool_calls_cost_columns.sql adds them additively.
CREATE TABLE IF NOT EXISTS tool_calls (
  id             bigserial PRIMARY KEY,
  run_id         uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  tool_name      text NOT NULL,
  args           jsonb NOT NULL DEFAULT '{}'::jsonb,
  result         jsonb NOT NULL DEFAULT '{}'::jsonb,
  status         text NOT NULL,
  latency_ms     int  NOT NULL DEFAULT 0,
  error_message  text NULL,
  created_at     timestamptz NOT NULL DEFAULT now()
);

COMMIT;
