---
id: s16-cold-storage-cron
title: Daily asyncio cold-storage cron — rotate superseded R2 objects older than 30 days to cold/ prefix
depends_on: [s07-r2-uploader]
parallel_safe: true
estimated_loc: 250
---

# s16-cold-storage-cron — Daily cold-storage rotation cron

## Summary

The retention enforcer. An infinite-loop `asyncio.create_task` started from the lifespan that sleeps `settings.cold_storage_interval_seconds` (default 86400 = 24h) between sweeps. Each sweep queries `external_media_assets WHERE status = 'superseded' AND updated_at < now() - interval '30 days' AND r2_key NOT LIKE 'cold/%'`, calls `move_to_cold_storage` (s07) per row, and updates the `r2_key`. Active assets (`status = 'uploaded'`) stay forever; superseded assets within 30 days stay accessible. Per ADR-0005 + intake decision (30-day retention then cold-storage).

## Acceptance criteria

- AC-1: `app/jobs/cold_storage.py` exports `async def cold_storage_worker(services: RuntimeServices) -> None`. Infinite-loop coroutine: per iteration, fetches eligible rows, processes each, sleeps `services.settings.cold_storage_interval_seconds`. Wraps each row's processing in `try/except` so one bad row doesn't kill the worker.
- AC-2: `app/jobs/cold_storage.py` exports `async def sweep_once(pool, r2_client) -> int` that runs one sweep and returns the count of rows moved. This is the unit-testable surface; the worker is a thin loop around it.
- AC-3: Eligibility query: `SELECT id, r2_key FROM external_media_assets WHERE status = 'superseded' AND updated_at < now() - interval '30 days' AND r2_key IS NOT NULL AND r2_key NOT LIKE 'cold/%'`. The `r2_key NOT LIKE 'cold/%'` guard prevents re-processing.
- AC-4: Per eligible row: call `move_to_cold_storage(r2, src_key=r2_key)` (s07) → update the row: `UPDATE external_media_assets SET r2_key = $new_key, r2_url = NULL, updated_at = now(), metadata = metadata || jsonb_build_object('cold_storage_moved_at', to_jsonb(now())) WHERE id = $id`. `r2_url` cleared because the public URL is no longer valid post-rotation; cold-storage retrieval requires explicit recovery (documented in `docs/retention.md`).
- AC-5: `app/main.py` lifespan additively spawns the cron: `services.background_tasks.append(asyncio.create_task(cold_storage_worker(services)))`. On shutdown, the lifespan cancels and awaits the task with a small timeout (5s) to allow in-flight sweeps to drain.
- AC-6: `docs/retention.md` documents: (a) the 30-day-then-cold rule, (b) the `cold/<key>` prefix convention, (c) the recovery procedure (`aws s3 cp s3://bucket/cold/<key> s3://bucket/<key>` then update the row — manual; no automatic recovery in v1), (d) the cron interval and how to tune it, (e) the "active assets stay forever" guarantee.
- AC-7: Cron is opt-out: if `settings.cold_storage_interval_seconds == 0`, the worker exits immediately (useful for local dev).

## Paths in scope

- `app/jobs/__init__.py`
- `app/jobs/cold_storage.py`
- `app/main.py` (additive — lifespan spawn + shutdown drain only)
- `docs/retention.md`

## Paths out of scope (do not touch)

- `app/storage/**` (s07 owns; this slice consumes `move_to_cold_storage`)
- `app/auth/**`, `app/payload/**`, `app/runs/**`, `app/style/**`, `app/providers/**`, `app/routes/**`, `app/orchestration/**`, `app/quality/**`, `app/callback/**`, `app/inspector/**`
- `app/config.py`, `app/runtime.py` (the `background_tasks` field on `RuntimeServices` is already declared in s01; the `cold_storage_interval_seconds` setting too)
- `db/migrations/**`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s16-cold-storage-cron/tests/test_sweep_once_no_eligible.py` — `requires_db` — empty DB → returns 0; no R2 calls made.
- `slices/s16-cold-storage-cron/tests/test_sweep_once_moves_eligible.py` — `requires_db` — seed three superseded rows older than 30 days → `sweep_once` returns 3; mocked R2 client received 3 copy+delete pairs; rows updated with `cold/` prefix.
- `slices/s16-cold-storage-cron/tests/test_sweep_once_skips_recent_superseded.py` — `requires_db` — superseded row newer than 30 days → not moved.
- `slices/s16-cold-storage-cron/tests/test_sweep_once_skips_uploaded.py` — `requires_db` — `uploaded` row is NEVER moved regardless of age.
- `slices/s16-cold-storage-cron/tests/test_sweep_once_skips_already_cold.py` — `requires_db` — row with `r2_key` already `cold/...` → skipped.
- `slices/s16-cold-storage-cron/tests/test_sweep_once_continues_on_error.py` — `requires_db` — mock `move_to_cold_storage` to raise on the second row; first and third still processed; return value reflects the count of successes.
- `slices/s16-cold-storage-cron/tests/test_sweep_clears_r2_url.py` — `requires_db` — after move, `r2_url` is NULL on the row.
- `slices/s16-cold-storage-cron/tests/test_cold_storage_disabled.py` — when `cold_storage_interval_seconds == 0`, `cold_storage_worker` returns immediately without entering the loop.
- `slices/s16-cold-storage-cron/tests/test_retention_doc_completeness.py` — `docs/retention.md` contains the documented sections (parse for keywords: "30 days", "cold/", "recovery", "interval", "active assets").

## Hints

- ADR anchor: [plan/adr/0005-external-media-assets-ddl.md](plan/adr/0005-external-media-assets-ddl.md) §"R2 retention" + intake decision (30 days then cold-storage prefix).
- The lifespan spawn pattern mirrors arthor-agent: `services.background_tasks.append(asyncio.create_task(...))`. On shutdown, iterate and `task.cancel()` then `await asyncio.wait_for(task, timeout=5)` swallowing `CancelledError` and `TimeoutError`.
- The cron uses `services.pool` and `services.r2`. Both are populated by s02 / s07 lifespan extensions; this slice only adds the spawn.
- Use `asyncio.sleep(services.settings.cold_storage_interval_seconds)`. For test ergonomics, do NOT busy-wait — tests call `sweep_once` directly, not the worker loop.
- `sweep_once` is the unit-test surface. Tests inject a mocked R2 client (`moto` decorator). The loop body is tiny and tested via `test_cold_storage_disabled`.
- `parallel_safe: true` because the lifespan extension is small and additive; no file conflicts with s11/s12/s13/s14/s15 if sequenced after them. Mark `true` because the slice graph allows running s16 alongside the inspector slices once s07 is green — but in practice it will run in the final wave after s15 to keep the `app/main.py` edits ordered.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s16-cold-storage-cron/tests` is fully green (DB-required tests skipped if no DATABASE_URL, R2 mocked), no files under `paths_out_of_scope` were modified, and no test files under `slices/s16-cold-storage-cron/tests/` were modified.
