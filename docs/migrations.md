# Database migrations

Database schema for this service is managed with versioned SQL files under `db/migrations/`. Apply them **only** on a **dev Neon branch** (never production without W11 coordination and a written rollout plan).

## Q14 before apply

On the **target Neon branch**, capture live shape before running any DDL:

```sql
\d external_media_assets
\d image_request_payloads
\d tool_calls
\d agent_runs
```

Or use `information_schema.columns` if `psql` is unavailable.

## Reconcile with arthor-ai `drizzle/0015`

W11 custodian (`~/arthor-ai/drizzle/0015_image_service_tables.sql`) creates:

- `external_media_assets` — matches `db/migrations/001_external_media_assets.sql`
- `image_request_payloads` — matches `db/migrations/002_image_request_payloads.sql`
- `tool_calls` — full harness table **including** `cost_cents`, `provider`, `model_version`

**Apply rules:**

1. If `external_media_assets` and `image_request_payloads` already exist (0015 applied) → **skip 001 and 002**.
2. If `tool_calls` exists from arthor-agent **without** cost columns → run **003 only** (`ADD COLUMN IF NOT EXISTS`).
3. If 0015 applied → **003 is a no-op** but safe to run.
4. Never create duplicate tables; all service migrations use `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`.

Fresh local dev (no shared Neon): bootstrap harness first, then 001→003 — see `db/dev/000_local_harness_bootstrap.sql`.

## Apply order

Run in sequence when tables are missing:

1. `db/migrations/001_external_media_assets.sql`
2. `db/migrations/002_image_request_payloads.sql`
3. `db/migrations/003_tool_calls_cost_columns.sql`

## Commands

```bash
psql "$DATABASE_URL" -f db/migrations/001_external_media_assets.sql
psql "$DATABASE_URL" -f db/migrations/002_image_request_payloads.sql
psql "$DATABASE_URL" -f db/migrations/003_tool_calls_cost_columns.sql
```

Set `DATABASE_URL` to your isolated dev branch DSN. **Do not** run these against production; W11 owns prod DDL.

## Rollback (dev only)

Prefer restoring a fresh dev branch. Conceptually: drop indexes created above, then drop dependent tables (`external_media_assets`, `image_request_payloads`) if you must unwind — only when no valuable data exists. Migration `003` only adds nullable/new columns with defaults; columns can be left in place (`IF EXISTS` drops are optional and non-destructive if you choose to remove them later).

The `asyncpg` pool in `app/main.py` connects when `DATABASE_URL` is configured in settings; migrations themselves are applied manually via `psql` as shown.
