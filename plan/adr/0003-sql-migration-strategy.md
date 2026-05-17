# ADR 0003: SQL migration strategy

- Status: proposed
- Date: 2026-05-17

## Context

The packet says "write migrations in numbered files (`001_*.sql`, `002_*.sql`, ...) so the unified-schema-push agent (W11) can absorb them later." Research subagent #3 documented that arthor-agent uses `phaseN_<description>.sql` instead, with manual `psql "$DATABASE_URL" -f` apply and no schema_migrations tracking table. arthor-ai uses Drizzle Kit with `__drizzle_migrations` bookkeeping.

## Options considered

- **Adopt packet's `001_*.sql` zero-padded numeric** — independent counter per service; W11 reconciles.
- **Adopt arthor-agent's `phaseN_<description>.sql`** — consistent across the two FastAPI services on the same shared DB.
- **Adopt Alembic** — Python-native migrations with auto-generation and bookkeeping. But: arthor-agent doesn't use it; introducing Alembic here breaks the "mirror the pattern" rule and adds tooling to W11's absorb work.

## Decision

**Adopt the packet's `001_*.sql` zero-padded numeric naming.** The packet's instruction wins because:

1. arthor-image-service starts a fresh counter independent of arthor-agent's phase history.
2. W11 will re-number or rewrite migration files at absorb time regardless of source convention; zero-padded numerics give W11 a clean monotonic series.
3. The first three migrations (per ADR-0005 and the slice list) have natural numeric sequencing without arbitrary "phase" semantics.

Specifics:

- Path: `db/migrations/`
- File naming: `NNN_snake_case_description.sql`, three-digit zero-padded
- Initial files:
  - `001_external_media_assets.sql`
  - `002_image_request_payloads.sql`
  - `003_tool_calls_cost_columns.sql`
- Header convention (mirroring arthor-agent):
  ```sql
  -- Migration 001: external_media_assets table.
  -- Run manually against a dev Neon branch. Do NOT apply to prod; coordinate with W11.

  BEGIN;
  ```
- Footer: `COMMIT;`
- Idempotency: liberal `IF NOT EXISTS` on tables, indexes, enum values.
- No `schema_migrations` tracking table in v1; apply checklist lives at `docs/migrations.md`.
- DEV branch only: `DATABASE_URL=postgresql://...neon-dev-branch...?sslmode=require`. Production application is W11's responsibility.
- Forward-only. Rollback documented as prose in `docs/migrations.md`.

## Consequences

What gets easier:
- W11 sees a clean series and can rename / merge / wrap as it sees fit.
- Local dev apply is one command: `psql "$DATABASE_URL" -f db/migrations/NNN_*.sql`.

What gets harder:
- No automated tracking of "what's been applied where." Mitigation: `docs/migrations.md` is the human-tracked single source of truth, and every PR description states which migrations were added.
- Reconciling our `001_..` with arthor-agent's `phase11_..` falls to W11.
