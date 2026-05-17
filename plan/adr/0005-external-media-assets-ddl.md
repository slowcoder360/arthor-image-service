# ADR 0005: external_media_assets DDL

- Status: proposed
- Date: 2026-05-17

## Context

`db-schema-audit.md` §4b names `external_media_assets` as a concept (provider, external_id, status, expiration) and explicitly says "Concrete shapes TBD when the repo is bootstrapped." Research subagent #5 confirmed the table does not exist anywhere in the codebases. arthor-image-service is the first concrete consumer and gets to define the full DDL.

## Options considered

- **Define the full DDL in this repo per the packet's draft row shape.** Standard.
- **Wait for arthor-content to define it first.** arthor-content is in Phase 0 (voice interviewer) and has no media generation yet; would block W21 indefinitely.
- **Use jsonb-everything for v1, lock the shape in W11.** Loses the relational benefits (indexes, queries, FK integrity).

## Decision

**Define the full DDL in this repo's `db/migrations/001_external_media_assets.sql`** per the packet's draft row shape, with refinements from the research:

```sql
-- Migration 001: external_media_assets table.
-- arthor-image-service is the first concrete consumer of the schema-audit §4b concept.
-- Run manually against a dev Neon branch. Do NOT apply to prod; coordinate with W11.

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

**Note on `site_id` FK:** intentionally **no FK** to `sites` because (a) this service writes raw SQL while `sites` is owned by arthor-ai's Drizzle, and (b) cross-writer FKs are fragile during W11's absorb. Application code is responsible for `site_id` validity.

**Status state machine:**
```
pending  ──► generated ──► uploaded ──► (active)
                  │                          │
                  ▼                          ▼
                failed                  superseded
```
- Newly-created row: `pending`.
- After provider returns: `generated`.
- After R2 upload succeeds: `uploaded` (terminal active state).
- On any failure: `failed` (terminal).
- When a slot is regenerated: previous row transitions `uploaded → superseded` and `metadata.replaced_by = <new_id>` is set. The new row goes through `pending → generated → uploaded`.

**Metadata jsonb keys** (required vs optional):

| Key | Required? | Type | Notes |
|---|---|---|---|
| `slot_id` | required | string | Identifies which slot in the pack this asset belongs to |
| `slot_intent` | required | string | Copy of the slot's `intent` field at generation time |
| `style_profile_id` | required | string | UUID of the StyleProfile resolved for this run (lives on `agent_runs.metadata.style_profile.id`) |
| `prompt_hash` | required | string | SHA-256 of the resolved slot prompt |
| `seed` | required | int or null | Provider seed used; null if provider doesn't accept one |
| `determinism_level` | required | enum | `strict | best-effort | none` per ADR-0007 |
| `run_id` | required | string | Same as `agent_run_id` column, denormalized for query convenience |
| `replaced_by` | optional | string | New `id` when this row becomes `superseded` |
| `original_run_id` | optional | string | If this asset was forked from another run via "rerun from payload" |
| `palette_drift` | optional | bool | True if palette-variance check exceeded threshold |
| `palette_extracted` | optional | array | Dominant hex colors extracted from the generated image |
| `provider_response_shape` | optional | object | Trimmed (no body) provider response shape for audit |

## Consequences

What gets easier:
- All required cost-rollup queries are FK-indexed.
- GUI run-detail page can `SELECT * FROM external_media_assets WHERE agent_run_id = $1 ORDER BY metadata->>'slot_id'`.
- Pack-consistency grid: one query.

What gets harder:
- W11 has to decide whether to keep this DDL verbatim or refactor (e.g. lift `slot_id` to a column). Acceptable.
- Adding more allow-list provider values requires a migration (CHECK constraint). v1 starts with 3; this is fine.
