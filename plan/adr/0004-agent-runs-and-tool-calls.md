# ADR 0004: agent_runs and tool_calls flavor + additive extensions

- Status: proposed
- Date: 2026-05-17

## Context

Research subagent #4 found a critical structural fact: **two different `agent_runs` tables exist on the same shared Neon DB.**

- **arthor-agent harness** `agent_runs` (`db/migrations/phase10_arthor_harness.sql`): has `cost_cents`, `prompt_tokens`, `completion_tokens`, `metadata jsonb`, `status` CHECK, `started_at/finished_at`, `parent_run_id` (no FK), `run_type` unconstrained text.
- **arthor-ai Drizzle** `agentRuns` (`lib/db/schema.ts`): has `site_id` FK, `input_payload jsonb`, `output_summary jsonb`, `run_type` typed enum (no image_* values), `started_at/completed_at`. **No cost columns.**

`tool_calls` exists only in arthor-agent. FK column is `run_id` (NOT `agent_run_id`!). Columns: `id (bigserial)`, `run_id`, `tool_name`, `args jsonb`, `result jsonb`, `status` CHECK, `latency_ms`, `error_message`, `created_at`. **No `cost_cents`, no `provider`, no `model_version`.**

The packet's "cost rolls up to `agent_runs.cost_cents`" and "every provider call writes a `tool_calls` row with `cost_cents`, `latency_ms`, `provider`, `model_version`" implicitly assumes the arthor-agent harness shape.

## Options considered

- **A. Write to arthor-agent harness flavor; extend `tool_calls` additively** — packet's cost-rollup story works as written. Three new columns on `tool_calls` (`cost_cents int NOT NULL DEFAULT 0`, `provider text NULL`, `model_version text NULL`). New `run_type` text literals: `image_pack_generation`, `image_slot_regenerate`, `image_style_preview`. No schema changes to arthor-ai's Drizzle table.
- **B. Write to arthor-ai Drizzle flavor; extend it additively** — would require adding cost columns to a table arthor-ai owns; violates "don't write to arthor-ai's tables" rule.
- **C. Create a brand-new `image_runs` table** — duplicates concepts; loses the shared cost-rollup infrastructure the packet specifies.

## Decision

**Option A: Write to the arthor-agent harness `agent_runs` flavor and additively extend `tool_calls`.**

Specifics:

- This service reads from and writes to the **harness-flavored** `agent_runs` (the one with `cost_cents`, `prompt_tokens`, `completion_tokens`, `metadata jsonb`). No new columns added to `agent_runs` in v1.
- `tool_calls.run_id` is the FK column name (not `agent_run_id`). Slice specs must spell this correctly.
- Migration `003_tool_calls_cost_columns.sql` adds three columns:
  ```sql
  ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS cost_cents int NOT NULL DEFAULT 0;
  ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS provider text NULL;
  ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS model_version text NULL;
  CREATE INDEX IF NOT EXISTS idx_tool_calls_provider ON tool_calls (provider);
  ```
- New `run_type` text values used by this service:
  - `image_pack_generation` — full asset-pack run
  - `image_slot_regenerate` — single-slot rerun
  - `image_style_preview` — cheap style probe
- No CHECK constraint on `run_type` in the harness table, so no migration is needed for the new values.
- arthor-ai's Drizzle enum gets these three values added in a coordinated W11 push — out of scope for this repo.
- Cost rollup at run completion: `UPDATE agent_runs SET cost_cents = (SELECT COALESCE(SUM(cost_cents), 0) FROM tool_calls WHERE run_id = $1), prompt_tokens = ..., completion_tokens = ..., finished_at = now() WHERE id = $1`.
- `tool_calls.args` and `tool_calls.result` get **trimmed jsonb** per `db-schema-audit.md` §6 (shape + key fields + `prompt_hash` + provider response shape + token counts only — never full prompts or full response bodies). 90-day retention applies.

## Consequences

What gets easier:
- The packet's cost-capture story works verbatim against the harness shape.
- arthor-agent and arthor-image-service share one cost-rollup query pattern.

What gets harder:
- W11's reconciliation: arthor-ai's Drizzle `agentRuns` is missing the cost columns and the `metadata jsonb`. W11 absorbs by adding them to Drizzle (additive); existing arthor-ai code is unaffected.
- Anyone reading code in arthor-ai who expects `agent_runs.cost_cents` to exist will be confused until W11 lands. Mitigation: this ADR is the single artifact pointing at the drift.
