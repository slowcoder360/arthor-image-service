-- Migration 003: tool_calls cost columns (additive). Run manually against a dev Neon branch. Do NOT apply to prod; coordinate with W11.

BEGIN;

ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS cost_cents int NOT NULL DEFAULT 0;
ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS provider text NULL;
ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS model_version text NULL;
CREATE INDEX IF NOT EXISTS idx_tool_calls_provider ON tool_calls (provider);

COMMIT;
