---
id: s02-db-pool-and-migrations-001
title: asyncpg pool + the three foundational SQL migrations (external_media_assets, image_request_payloads, tool_calls cost columns)
depends_on: [s01-skeleton]
parallel_safe: true
estimated_loc: 400
---

# s02-db-pool-and-migrations-001 — DB pool + foundational migrations

## Summary

Land the asyncpg pool at `db/pool.py`, wire it into `app/main.py`'s lifespan additively, and ship the three foundational SQL migrations: `001_external_media_assets.sql` (full ADR-0005 DDL), `002_image_request_payloads.sql` (full ADR-0010 DDL), and `003_tool_calls_cost_columns.sql` (additive `cost_cents`/`provider`/`model_version` columns + provider index per ADR-0004). Extend `docs/migrations.md` with the apply checklist (dev Neon branch only; W11 owns prod). No data writers in this slice — those live in s04 (payload repo), s05 (runs writer), and s07 (asset writer).

## Acceptance criteria

- AC-1: `db/pool.py` exports `async def init_pool(database_url: str) -> asyncpg.Pool` (uses `asyncpg.create_pool` with `min_size=1, max_size=10`) and `async def close_pool(pool)`. Mirrors `~/arthor-agent/db/pool.py:6-12`.
- AC-2: `app/main.py` lifespan additively calls `init_pool(settings.database_url)` when `settings.database_url` is set and attaches the pool to `services.pool`. When `database_url` is unset, lifespan logs a single warning and leaves `services.pool = None` (matches the s01 contract that fields are optional). On shutdown, lifespan awaits `close_pool(services.pool)`.
- AC-3: `db/migrations/001_external_media_assets.sql` matches the ADR-0005 DDL **verbatim**: `BEGIN;`, `CREATE TABLE IF NOT EXISTS external_media_assets (...)` with `provider/external_id/model_version/status/expiration/r2_key/r2_url/width/height/bytes/metadata/agent_run_id/site_id/created_at/updated_at`, the two CHECK constraints (`provider` allow-list `{openai_image, google_imagen, google_nano_banana}`, `status` allow-list `{pending, generated, uploaded, failed, superseded}`), no FK on `site_id`, FK on `agent_run_id REFERENCES agent_runs(id) ON DELETE CASCADE`, the five indexes `(idx_ema_site_created, idx_ema_agent_run, idx_ema_status, idx_ema_provider_model, idx_ema_metadata_slot)`, `COMMIT;`.
- AC-4: `db/migrations/002_image_request_payloads.sql` matches the ADR-0010 DDL **verbatim**: `id uuid PK`, `agent_run_id` FK ON DELETE CASCADE, `payload_version text NOT NULL`, `payload jsonb NOT NULL`, `payload_hash text NOT NULL`, `idempotency_key text NOT NULL` with UNIQUE constraint `image_request_payloads_idem_unique`, `source text NOT NULL DEFAULT 'arthor-ai'`, `created_at timestamptz NOT NULL DEFAULT now()`, plus `idx_irp_agent_run` and `idx_irp_payload_hash`.
- AC-5: `db/migrations/003_tool_calls_cost_columns.sql` is additive only: `ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS cost_cents int NOT NULL DEFAULT 0;`, `ADD COLUMN IF NOT EXISTS provider text NULL;`, `ADD COLUMN IF NOT EXISTS model_version text NULL;`, `CREATE INDEX IF NOT EXISTS idx_tool_calls_provider ON tool_calls (provider);`. Does NOT touch `tool_calls.status` CHECK or `tool_calls.run_id` FK (ADR-0004 critical drift: column is `run_id`, NOT `agent_run_id`).
- AC-6: All three migration files share the standard header `-- Migration NNN: <description>. Run manually against a dev Neon branch. Do NOT apply to prod; coordinate with W11.` and are wrapped in `BEGIN;` / `COMMIT;`.
- AC-7: `docs/migrations.md` (extended from s01's stub) documents: (a) the apply order 001 → 002 → 003, (b) the exact `psql "$DATABASE_URL" -f db/migrations/NNN_*.sql` command, (c) the dev-Neon-branch-only rule with the W11 coordination note, (d) the rollback prose (drop indexes then drop tables; the additive 003 columns may stay since `IF EXISTS`-style DROPs are non-destructive).

## Paths in scope

- `db/__init__.py` (empty marker)
- `db/pool.py`
- `db/migrations/001_external_media_assets.sql`
- `db/migrations/002_image_request_payloads.sql`
- `db/migrations/003_tool_calls_cost_columns.sql`
- `docs/migrations.md` (extend, do not rewrite)
- `app/main.py` (additive lifespan delta only — wrap existing logic; the user rule forbids rewriting)

## Paths out of scope (do not touch)

- `app/config.py`, `app/runtime.py` (s01 owns; the `pool` field on `RuntimeServices` is already declared optional)
- Any other `app/**` module
- `pyproject.toml`, `system.yaml`, `AGENTS.md`, `README.md`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s02-db-pool-and-migrations-001/tests/test_pool_factory.py` — asserts `init_pool` returns an `asyncpg.Pool` and `close_pool` cleans it up (marked `requires_db`, skipped if `DATABASE_URL` env-var is unset).
- `slices/s02-db-pool-and-migrations-001/tests/test_lifespan_pool_wiring.py` — asserts that with `DATABASE_URL` set, lifespan attaches `services.pool`; with it unset, `services.pool is None` and a warning is logged.
- `slices/s02-db-pool-and-migrations-001/tests/test_migration_001_ddl.py` — parses `001_external_media_assets.sql` as text and asserts: `BEGIN/COMMIT`, presence of every column from ADR-0005, both CHECK constraints with the documented allow-lists, all five indexes by name, FK on `agent_run_id` with `ON DELETE CASCADE`, NO FK on `site_id`.
- `slices/s02-db-pool-and-migrations-001/tests/test_migration_002_ddl.py` — parses `002_image_request_payloads.sql` and asserts: UNIQUE on `idempotency_key`, both indexes by name, FK ON DELETE CASCADE on `agent_run_id`.
- `slices/s02-db-pool-and-migrations-001/tests/test_migration_003_ddl.py` — parses `003_tool_calls_cost_columns.sql` and asserts: only `ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS` statements + one `CREATE INDEX IF NOT EXISTS`; no other DDL; `cost_cents` has `NOT NULL DEFAULT 0`; `provider` and `model_version` are nullable. Asserts FK column reference uses `run_id` (sanity check that nothing leaked from a typo).
- `slices/s02-db-pool-and-migrations-001/tests/test_migration_headers.py` — asserts every migration file has the standard header and is wrapped in `BEGIN;` / `COMMIT;`.
- `slices/s02-db-pool-and-migrations-001/tests/test_migrations_doc.py` — asserts `docs/migrations.md` documents the apply order, the W11 coordination warning, and the dev-only rule.
- `slices/s02-db-pool-and-migrations-001/tests/test_migrations_apply_smoke.py` — `requires_db` smoke test: against a clean dev DB, applies 001 → 002 → 003 in order via `psycopg`/`asyncpg.execute`, then verifies the tables/columns exist via `information_schema`. Skipped when `DATABASE_URL` is unset.

## Hints

- ADR anchors: [plan/adr/0003-sql-migration-strategy.md](plan/adr/0003-sql-migration-strategy.md), [plan/adr/0004-agent-runs-and-tool-calls.md](plan/adr/0004-agent-runs-and-tool-calls.md), [plan/adr/0005-external-media-assets-ddl.md](plan/adr/0005-external-media-assets-ddl.md), [plan/adr/0010-payload-contract-v1.md](plan/adr/0010-payload-contract-v1.md) (the `image_request_payloads` DDL block).
- **Critical drift to honor (ADR-0004):** `tool_calls.run_id`, NOT `tool_calls.agent_run_id`. Every reference (including comments) must spell this correctly.
- The orchestrator-approved plan-text said `app/db/pool.py`; ADR-0002 + the arthor-agent mirror say `db/pool.py` at the repo root. **The ADR wins.** Use `db/pool.py`; the `app/db/` folder is not created.
- DDL is verbatim from ADR-0005 + ADR-0010. Resist the urge to "improve" indexes or rename columns.
- The lifespan delta to `app/main.py` should be a single guarded block: `if services.settings.database_url: services.pool = await init_pool(...)`. Match the user rule: additive only, no rewrite of the s01 lifespan body.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s02-db-pool-and-migrations-001/tests` is fully green (DB-required tests skipped cleanly if no `DATABASE_URL`), no files under `paths_out_of_scope` were modified, and no test files under `slices/s02-db-pool-and-migrations-001/tests/` were modified.
