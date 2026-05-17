---
id: s05-agent-runs-writer
title: agent_runs writer (harness flavor) + tool_calls writer (with cost_cents/provider/model_version) + cost rollup
depends_on: [s02-db-pool-and-migrations-001]
parallel_safe: true
estimated_loc: 350
---

# s05-agent-runs-writer — agent_runs + tool_calls writers + cost rollup

## Summary

The persistence helpers for every run this service creates. Writes to the **arthor-agent harness flavor** of `agent_runs` (ADR-0004 critical drift), with the new `run_type` literals `image_pack_generation | image_slot_regenerate | image_style_preview`. Writes child `tool_calls` rows (FK column **`run_id`**, not `agent_run_id`) with the additive `cost_cents`/`provider`/`model_version` columns from s02's migration 003. Provides the `roll_up_cost` helper so the asset-pack worker can update the parent run's total at completion. Includes the args/result trimming helper per ADR-0004 §6 retention rules.

## Acceptance criteria

- AC-1: `app/runs/agent_runs.py` exports `async def insert_pending_run(pool, *, run_type: str, site_id: uuid.UUID | None, parent_run_id: uuid.UUID | None = None, metadata: dict | None = None) -> uuid.UUID`. Inserts a row with `status = "running"`, `started_at = now()`, `cost_cents = 0`, `prompt_tokens = 0`, `completion_tokens = 0`, `metadata = $metadata or {}`. Returns the new `id`.
- AC-2: `app/runs/agent_runs.py` exports `async def update_run_status(pool, run_id, *, status: str, error: str | None = None, finished: bool = False, metadata_patch: dict | None = None) -> None`. When `finished=True`, sets `finished_at = now()`. When `metadata_patch` is provided, merges into existing `metadata jsonb` (top-level shallow merge via `jsonb_set` per key OR `metadata = metadata || $patch` for shallow). Status must be one of `running | ok | failed`; raises `ValueError` otherwise.
- AC-3: `run_type` allow-list at the writer layer (defensive — the DB column is unconstrained text): `{image_pack_generation, image_slot_regenerate, image_style_preview}`. `ValueError` on others.
- AC-4: `app/runs/tool_calls.py` exports `async def insert_tool_call(pool, *, run_id: uuid.UUID, tool_name: str, args: dict, result: dict, status: str, latency_ms: int, cost_cents: int, provider: str | None, model_version: str | None) -> int`. Uses FK column `run_id` (NOT `agent_run_id`). `status` allow-list `{ok, error, skipped}` (matches the existing arthor-agent CHECK). Returns the inserted `bigserial` id.
- AC-5: `app/runs/tool_calls.py` exports `def trim_args(args: dict) -> dict` and `def trim_result(result: dict) -> dict` per ADR-0004 §6 retention: strip any key whose value is a string longer than 256 chars, keep shape (replace with `{"_trimmed": true, "_original_len": <len>}`), preserve `prompt_hash` always, preserve numeric fields, preserve `provider`/`model_version`/`seed`/`external_id`.
- AC-6: `app/runs/cost_rollup.py` exports `async def roll_up_cost(pool, run_id: uuid.UUID) -> int`. Runs `UPDATE agent_runs SET cost_cents = (SELECT COALESCE(SUM(cost_cents), 0) FROM tool_calls WHERE run_id = $1), prompt_tokens = (SELECT COALESCE(SUM(prompt_tokens), 0) FROM tool_calls WHERE run_id = $1), completion_tokens = (SELECT COALESCE(SUM(completion_tokens), 0) FROM tool_calls WHERE run_id = $1), finished_at = COALESCE(finished_at, now()) WHERE id = $1 RETURNING cost_cents;`. Returns the new total cost in cents.
- AC-7: All three modules use `pool.acquire()` async context managers, never raw connections. No transaction wrappers in v1 (single-statement inserts are atomic).

## Paths in scope

- `app/runs/__init__.py`
- `app/runs/agent_runs.py`
- `app/runs/tool_calls.py`
- `app/runs/cost_rollup.py`

## Paths out of scope (do not touch)

- `db/migrations/**` (s02 owns the DDL)
- `app/payload/**` (s04 owns; payload uses these writers but does not own them)
- `app/storage/**`, `app/providers/**`, `app/routes/**`, `app/orchestration/**`, `app/inspector/**`
- `app/main.py`, `app/config.py`, `app/runtime.py`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s05-agent-runs-writer/tests/test_insert_pending_run.py` — `requires_db` — insert returns a uuid; row exists with `status="running"`, correct `run_type`, `started_at` set, `cost_cents=0`.
- `slices/s05-agent-runs-writer/tests/test_run_type_allow_list.py` — `image_pack_generation`/`image_slot_regenerate`/`image_style_preview` accepted; `bogus_type` raises `ValueError` at the writer (no DB write attempted).
- `slices/s05-agent-runs-writer/tests/test_update_run_status.py` — `requires_db` — status transitions `running → ok`; `finished=True` sets `finished_at`; `metadata_patch` merges shallow.
- `slices/s05-agent-runs-writer/tests/test_insert_tool_call.py` — `requires_db` — inserts a row; FK column is `run_id`; `cost_cents`/`provider`/`model_version` round-trip.
- `slices/s05-agent-runs-writer/tests/test_tool_call_status_allow_list.py` — `ok`/`error`/`skipped` accepted; `running` rejected (CHECK violation surfaces from DB).
- `slices/s05-agent-runs-writer/tests/test_trim_args.py` — long strings replaced with `{"_trimmed": true, "_original_len": N}`; `prompt_hash` preserved; nested dicts trimmed recursively; numbers/bools/None untouched.
- `slices/s05-agent-runs-writer/tests/test_trim_result.py` — same as args; preserves `provider`/`model_version`/`seed`/`external_id` even if they happen to be long.
- `slices/s05-agent-runs-writer/tests/test_roll_up_cost.py` — `requires_db` — create a run, insert 3 tool_calls with `cost_cents={5, 7, 11}`; roll_up_cost returns 23; agent_runs row reflects 23 and finished_at is set.
- `slices/s05-agent-runs-writer/tests/test_roll_up_cost_empty.py` — `requires_db` — run with zero tool_calls rolls up to `cost_cents=0` without error.

## Hints

- ADR anchors: [plan/adr/0004-agent-runs-and-tool-calls.md](plan/adr/0004-agent-runs-and-tool-calls.md) (critical drift — `tool_calls.run_id`), [plan/CONTEXT.md](plan/CONTEXT.md) §"Schema vocabulary".
- This is the harness-flavored table; column names: `id, run_type, status, started_at, finished_at, cost_cents, prompt_tokens, completion_tokens, metadata, parent_run_id`. **Not** the arthor-ai Drizzle flavor — do not include `site_id`, `input_payload`, `output_summary` columns. The site_id link for image runs lives in `metadata->>'site_id'` or via the `external_media_assets.site_id` column.
- Wait — re-read ADR-0004 carefully: the harness `agent_runs` does not have `site_id`. The packet's contract puts `site_id` on `external_media_assets` (which has it). For runs, `site_id` rides on `agent_runs.metadata.site_id` (string). The `insert_pending_run(pool, *, site_id=...)` parameter takes the site_id and stuffs it into `metadata`.
- The `tool_calls` CHECK on `status` is `{ok, error, skipped}`. Do not pass `running` (the row is inserted only after the call completes per ADR-0007 §"Cost-tracking pattern").
- `prompt_tokens`/`completion_tokens` aggregate from `tool_calls` only when those columns exist on `tool_calls`. They do per arthor-agent's existing schema. If they don't exist for some reason, the rollup falls back to `0`.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s05-agent-runs-writer/tests` is fully green (DB-required tests skipped if no DATABASE_URL), no files under `paths_out_of_scope` were modified, and no test files under `slices/s05-agent-runs-writer/tests/` were modified.
