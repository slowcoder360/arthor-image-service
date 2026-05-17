# ADR 0002: Mirror arthor-agent FastAPI shape

- Status: proposed
- Date: 2026-05-17

## Context

`arthor-seo-service` is unbuilt; the only FastAPI sibling is `arthor-agent`. Research subagent #2 documented its conventions: `app/` folder, `pydantic-settings`, `asyncpg.create_pool` in `db/pool.py`, `RuntimeServices` dataclass on `app.state.services`, `asyncio.create_task` for background work, no `Depends`, no `BackgroundTasks`, no Celery. Routers organized per-feature module.

## Options considered

- **Mirror arthor-agent exactly** — zero conventions to invent; future seo-service can also mirror.
- **Adopt FastAPI best practices (Depends, BackgroundTasks)** — better-documented patterns externally, but every difference between the two services becomes a tax on cross-service work.
- **Hybrid (mirror app shape; use Depends + BackgroundTasks)** — splits the difference. Risk: half-following a convention is worse than not following it.

## Decision

**Mirror arthor-agent exactly.** Specifically:

- App instance at `app/main.py` with `FastAPI(title="arthor-image-service v1", lifespan=lifespan)`. No `version=` until v1.1 is meaningful.
- Async `@asynccontextmanager lifespan` that:
  - Calls `configure_logging()`
  - Creates `RuntimeServices` (asyncpg pool, R2 client, settings, providers registry)
  - Attaches to `app.state.services`
  - Spawns `asyncio.create_task` for background workers (cold-storage cron)
  - Cleans up in the `finally` block
- `app/config.py` with `pydantic-settings` `BaseSettings`, `.env` loading, `extra="ignore"`.
- `app/runtime.py` with `RuntimeServices` dataclass.
- `db/pool.py` with `asyncpg.create_pool` and `init_pool(settings.database_url)`.
- Feature modules: `app/auth/`, `app/payload/`, `app/providers/`, `app/style/`, `app/r2/`, `app/persistence/`, `app/inspector/` (or `app/routers/inspector.py`).
- Handlers read `request.app.state.services` directly. **No `Depends`.**
- Background work uses `asyncio.create_task`. **No `BackgroundTasks`. No Celery.**

`pyproject.toml` adds what arthor-agent lacks: a `[tool.pytest]`, `[tool.ruff]`, `[tool.mypy]` block and a console-script entry-point `arthor-image-service = "app.main:run"` so `uvicorn app.main:app` and `arthor-image-service` both work.

## Consequences

What gets easier:
- Cross-service navigation between arthor-agent and arthor-image-service is zero-friction.
- `arthor-seo-service` later inherits the pattern at no design cost.

What gets harder:
- Departing from arthor-agent's conventions later (e.g. if `Depends` becomes worth the lift) requires updating both services in sync. Acceptable tax.
