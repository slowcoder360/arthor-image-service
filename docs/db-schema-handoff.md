# arthor-image-service — DB schema handoff

Self-contained DDL for provisioning a database that `arthor-image-service` can run against.
All SQL is inline here; no access to the service repo is required.

## Read this first (clears up two common assumptions)

- **This service is Python / asyncpg with raw SQL migrations — it does NOT use Drizzle.**
  The Drizzle `agentRuns` table belongs to a *different* repo (arthor-ai).
- **This service does NOT own or alter `agent_runs`.** It reads/writes the existing
  **arthor-agent harness** `agent_runs` (the flavor with `cost_cents`, `prompt_tokens`,
  `completion_tokens`, `metadata jsonb`). It stores `site_id` inside `metadata`, so it needs
  **no column changes** to `agent_runs`.

## What the service owns vs. depends on

| Table | Owner | Section below |
|---|---|---|
| `agent_runs` | arthor-agent harness (prerequisite) | §1 |
| `tool_calls` (base) | arthor-agent harness (prerequisite) | §1 |
| `tool_calls` cost columns | arthor-image-service (additive) | §4 |
| `external_media_assets` | arthor-image-service | §2 |
| `image_request_payloads` | arthor-image-service | §3 |

If your target DB **already has** the arthor-agent harness `agent_runs` + `tool_calls`,
skip §1 and apply §2 → §3 → §4 only. If it's a fresh/standalone DB, apply §1 first.

## Apply order

1. §1 prerequisite harness tables (only if not already present)
2. §2 `external_media_assets`
3. §3 `image_request_payloads`
4. §4 `tool_calls` cost columns (additive)

---

## §1. Prerequisite harness tables (arthor-agent-owned)

> Include only if the DB does not already have these. In production these come from
> arthor-agent's own migrations; reproduced here so a standalone DB can be provisioned.
> FK column on `tool_calls` is **`run_id`** (NOT `agent_run_id`).

```sql
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Harness-flavored agent_runs: cost/token counters + jsonb metadata.
-- No status CHECK (run_type/status literals vary by caller); site_id lives in metadata.
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
  created_at         timestamptz NOT NULL DEFAULT now()
);

-- Harness-flavored tool_calls. cost_cents/provider/model_version are added in §4.
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
```

---

## §2. external_media_assets (service-owned)

```sql
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
```

---

## §3. image_request_payloads (service-owned)

```sql
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
```

---

## §4. tool_calls cost columns (service-owned, additive)

> Additive only. Safe to run against an existing `tool_calls` table.

```sql
BEGIN;

ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS cost_cents int NOT NULL DEFAULT 0;
ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS provider text NULL;
ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS model_version text NULL;
CREATE INDEX IF NOT EXISTS idx_tool_calls_provider ON tool_calls (provider);

COMMIT;
```

---

## Notes

- `gen_random_uuid()` requires the `pgcrypto` extension (built into core on PG 13+; the
  `CREATE EXTENSION IF NOT EXISTS pgcrypto;` in §1 covers older versions).
- The service runtime does **not** require a `site_id` column on `agent_runs` (it keeps
  `site_id` in `metadata`). The repo's local test fixtures reference `agent_runs.site_id`;
  that is a local-test-only concern and is intentionally omitted from this production-facing
  schema.
- `tool_calls.run_id` is the FK column name — not `agent_run_id`.
