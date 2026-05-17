-- Migration 001: external_media_assets table. Run manually against a dev Neon branch. Do NOT apply to prod; coordinate with W11.

BEGIN;

CREATE TABLE IF NOT EXISTS external_media_assets (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider        text NOT NULL,
  external_id     text NULL,
  model_version   text NOT NULL,
  status          text NOT NULL DEFAULT 'pending',
  expiration      timestamptz NULL,
  r2_key          text NULL,
  r2_url          text NULL,
  width           integer NULL,
  height          integer NULL,
  bytes           bigint NULL,
  metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
  agent_run_id    uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  site_id         uuid NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT external_media_assets_provider_chk
    CHECK (provider IN ('openai_image', 'google_imagen', 'google_nano_banana')),
  CONSTRAINT external_media_assets_status_chk
    CHECK (status IN ('pending', 'generated', 'uploaded', 'failed', 'superseded'))
);

CREATE INDEX IF NOT EXISTS idx_ema_site_created      ON external_media_assets (site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ema_agent_run         ON external_media_assets (agent_run_id);
CREATE INDEX IF NOT EXISTS idx_ema_status            ON external_media_assets (status);
CREATE INDEX IF NOT EXISTS idx_ema_provider_model    ON external_media_assets (provider, model_version);
CREATE INDEX IF NOT EXISTS idx_ema_metadata_slot     ON external_media_assets ((metadata->>'slot_id'));

COMMIT;
