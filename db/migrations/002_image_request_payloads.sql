-- Migration 002: image_request_payloads table. Run manually against a dev Neon branch. Do NOT apply to prod; coordinate with W11.

BEGIN;

CREATE TABLE IF NOT EXISTS image_request_payloads (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_run_id    uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  payload_version text NOT NULL,
  payload         jsonb NOT NULL,
  payload_hash    text NOT NULL,
  idempotency_key text NOT NULL,
  source          text NOT NULL DEFAULT 'arthor-ai',
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT image_request_payloads_idem_unique UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_irp_agent_run    ON image_request_payloads (agent_run_id);
CREATE INDEX IF NOT EXISTS idx_irp_payload_hash ON image_request_payloads (payload_hash);

COMMIT;
