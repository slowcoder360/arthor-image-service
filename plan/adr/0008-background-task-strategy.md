# ADR 0008: Background-task strategy

- Status: proposed
- Date: 2026-05-17

## Context

The packet says "FastAPI background tasks or a simple worker queue." Research subagent #2 found that arthor-agent uses `asyncio.create_task` for all background work — no FastAPI `BackgroundTasks`, no Celery, no RQ. arthor-agent's lifespan launches multiple `asyncio.create_task` workers (outbound consumer, EEAT drip scheduler, memory maintenance) and handlers fire `asyncio.create_task` for fire-and-forget operations.

Asset-pack generation is a multi-second to multi-minute operation that must accept the request, return 202, and complete asynchronously. The cold-storage cron is a daily background task.

## Options considered

- **A. `asyncio.create_task` from the lifespan + from handlers** — matches arthor-agent exactly. Zero new infrastructure. Concurrency is limited by what one Python process can hold.
- **B. FastAPI `BackgroundTasks`** — diverges from arthor-agent's convention. Limited (runs after response; can't continue past request lifetime).
- **C. External worker queue (Celery / RQ / arq)** — heavyweight. Justified only when concurrency outgrows a single-process asyncio loop.

## Decision

**Option A: `asyncio.create_task` from the lifespan + from handlers.**

Specifics:

- Cold-storage cron is an infinite-loop `async def cold_storage_worker(services)` started from the lifespan as `asyncio.create_task(...)`. Sleeps for `settings.cold_storage_interval_seconds` (default 86400) between sweeps.
- Asset-pack background workers are spawned per-request inside `POST /images/asset-pack/generate`:
  ```python
  async def asset_pack_generate(request: Request, payload: PayloadV1):
      services = request.app.state.services
      run_id = await services.runs.insert_pending_run(payload)
      asyncio.create_task(
          services.asset_pack.run_in_background(run_id=run_id, payload=payload)
      )
      return AcceptResponse(agent_run_id=run_id, status="accepted")
  ```
- Each background task wraps itself in `try/except` and writes a final `agent_runs.status` (`ok` or `failed`) plus the error message. Unhandled exceptions are logged but do not crash the event loop.
- Concurrency limit: `settings.max_concurrent_packs` (default 4) using `asyncio.Semaphore` held in `RuntimeServices.asset_pack_semaphore`. Acquire before generating; release on completion (or exception).

**Graduation trigger (documented for future ADR):**

We graduate to an external worker queue (likely `arq` with Redis, which arthor-agent already uses for cache) when **any one** of these is true:
1. `max_concurrent_packs > 8` and we still see queued runs sitting `pending` for more than 60 seconds during steady-state load.
2. The service needs to scale horizontally (more than one Python process running).
3. We need persistent retries surviving process restarts.

None of these conditions hold for v1 (Justin-only, dev-only, single-instance).

## Consequences

What gets easier:
- Zero new infrastructure for v1.
- Mirrors arthor-agent so cross-service maintenance is uniform.

What gets harder:
- A crashed process drops in-flight runs (run remains `pending` forever). Mitigation: a startup-time `RECONCILE` step in the lifespan re-marks any `running` or `pending` runs older than 1 hour as `failed`, with an error message indicating "process restart."
- The 4-pack concurrency ceiling is low. For v1 (Justin-only) it's plenty. The graduation trigger is documented so this doesn't bite silently.
