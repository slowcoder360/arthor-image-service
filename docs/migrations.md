# Database migrations

Database schema for this service is managed with versioned SQL files under `db/migrations/`. Apply them **only** on a **dev Neon branch** (never production without W11 coordination and a written rollout plan).

## Apply order

Run in sequence:

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
