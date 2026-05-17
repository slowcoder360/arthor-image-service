---
id: s01-skeleton
title: FastAPI app skeleton, pydantic-settings config, RuntimeServices, pytest harness, system.yaml, AGENTS.md, README
depends_on: []
parallel_safe: true
estimated_loc: 350
---

# s01-skeleton — FastAPI app skeleton + project bootstrap

## Summary

Stand up the bare runnable shell of `arthor-image-service`: `pyproject.toml` with the ADR-0001 stack, a FastAPI app with an async `lifespan` and `RuntimeServices` on `app.state.services` (ADR-0002), pydantic-settings config, a `/healthz` route, a pytest harness, and the project-meta files (`system.yaml`, `AGENTS.md`, `README.md`, stub `docs/migrations.md`). No DB, no auth, no providers — those are downstream slices that additively extend this slice's `app/main.py` lifespan.

## Acceptance criteria

- AC-1: `pyproject.toml` declares Python `>=3.13`, runtime deps from ADR-0001 (`fastapi`, `pydantic>=2`, `pydantic-settings`, `asyncpg`, `httpx`, `aiobotocore`, `jinja2`, `openai`, `google-genai`, `Pillow`, `python-dotenv`) and dev deps (`pytest`, `pytest-asyncio`, `httpx` for `TestClient`-style requests, `ruff`, `mypy`). Includes `[tool.pytest.ini_options]` with `testpaths = ["slices", "tests"]`, `asyncio_mode = "auto"`. `[tool.ruff]` and `[tool.mypy]` blocks per ADR-0001 (mypy `strict = true` for `app/`).
- AC-2: `app/main.py` exposes a module-level `app: FastAPI` created with `FastAPI(title="arthor-image-service v1", lifespan=lifespan)` (ADR-0002). The `@asynccontextmanager async def lifespan(app)` calls `configure_logging()`, builds a `RuntimeServices(settings=Settings())`, attaches via `app.state.services = services`, and cleans up in the `finally` block. No DB, no R2, no providers wired in v1 of this slice — downstream slices append to `lifespan` additively.
- AC-3: `app/config.py` exposes `Settings(BaseSettings)` with `env_file = ".env"`, `extra = "ignore"`, and the documented env keys: `database_url: str | None = None`, `fastapi_arthor_shared_secret: str | None = None`, `inspector_admin_token: str | None = None`, `r2_endpoint_url: str | None = None`, `r2_access_key_id: str | None = None`, `r2_secret_access_key: str | None = None`, `r2_bucket: str | None = None`, `openai_api_key: str | None = None`, `google_api_key: str | None = None`, `max_concurrent_packs: int = 4`, `palette_drift_threshold: float = 25.0`, `cold_storage_interval_seconds: int = 86400`, `log_level: str = "INFO"`. A `get_settings()` cached helper using `functools.lru_cache`.
- AC-4: `app/runtime.py` exposes a `RuntimeServices` dataclass with fields: `settings: Settings`, optional `pool`, optional `r2`, optional `asset_pack_semaphore`, optional `providers: dict[str, object]`, optional `background_tasks: list[asyncio.Task]`. All optional fields default to `None` / `field(default_factory=list)`. Documented as "downstream slices populate the optional fields in their lifespan additions."
- AC-5: `GET /healthz` returns `200` with JSON `{"status": "ok", "service": "arthor-image-service", "version": "0.1.0"}`. Defined inline in `app/main.py` (no router yet).
- AC-6: `system.yaml` at repo root validates against `~/arthor-systemmap/schema/system.example.yaml` — minimum fields: `name: arthor-image-service`, `kind: service`, `language: python`, `runtime: fastapi`, `owners: [justin]`, plus the schema's other required fields filled in faithfully.
- AC-7: `AGENTS.md` at repo root: one paragraph describing the service + a module map (`app/payload/`, `app/runs/`, `app/style/`, `app/storage/`, `app/providers/`, `app/routes/`, `app/orchestration/`, `app/inspector/`, `app/jobs/`, `db/migrations/`). Carries the user rule verbatim: *"only change what you need to change do not completely rewrite files. always ask permission before making changes that i did not ask for directly."*
- AC-8: `README.md` documents local run (`source .venv/bin/activate && pip install -e ".[dev]" && uvicorn app.main:app --reload`) and tests (`pytest`).
- AC-9: `docs/migrations.md` is a stub (one paragraph) that s02 will extend.
- AC-10: `tests/conftest.py` exposes a shared `pytest` configuration hook (`pytest_collection_modifyitems` for skip-on-no-db marker), plus an `app_client` fixture returning `httpx.AsyncClient(app=app, base_url="http://testserver")` for FastAPI in-process testing. Marks `requires_db` and `requires_r2` for downstream slices to use.

## Paths in scope

- `pyproject.toml`
- `app/__init__.py`
- `app/main.py`
- `app/config.py`
- `app/runtime.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `system.yaml`
- `AGENTS.md`
- `README.md`
- `docs/migrations.md`

## Paths out of scope (do not touch)

- `slices/**` (this slice's SPEC.md and tests are orchestrator-owned)
- `plan/**`, `packet/**`, `scratch/**`
- `.cursor/builder-os.json` and `.cursor/rules/**`
- `.gitignore` (already exists from packet-intake; do not modify)
- Anything under `app/` other than `app/__init__.py`, `app/main.py`, `app/config.py`, `app/runtime.py` (downstream slices own those folders)
- `db/**` (s02 owns)

## Failing tests the subagent must turn green

- `slices/s01-skeleton/tests/test_app_factory.py` — asserts `from app.main import app` returns a FastAPI instance with the correct title and a registered `/healthz` route.
- `slices/s01-skeleton/tests/test_healthz.py` — asserts `GET /healthz` returns 200 + the documented JSON body.
- `slices/s01-skeleton/tests/test_settings.py` — asserts every documented env key is on `Settings`, defaults are correct, `.env` is honored, `extra="ignore"` survives unknown keys without raising.
- `slices/s01-skeleton/tests/test_runtime_services.py` — asserts `RuntimeServices(settings=...)` builds with only `settings` and all other fields default to `None` / `[]`.
- `slices/s01-skeleton/tests/test_lifespan.py` — asserts the lifespan attaches `services` to `app.state` and tears it down without errors.
- `slices/s01-skeleton/tests/test_system_yaml.py` — asserts `system.yaml` parses as YAML and contains the required arthor-systemmap fields.
- `slices/s01-skeleton/tests/test_agents_md.py` — asserts `AGENTS.md` exists and contains the user rule verbatim.

## Hints

- Mirror `~/arthor-agent/app/main.py:151-184` (the lifespan shape) and `~/arthor-agent/app/config.py:1-60` (the settings shape). Anchored in `scratch/research/02-fastapi-skeleton.md`.
- ADR anchors: [plan/adr/0001-language-and-stack.md](plan/adr/0001-language-and-stack.md), [plan/adr/0002-mirror-arthor-agent-fastapi-shape.md](plan/adr/0002-mirror-arthor-agent-fastapi-shape.md).
- `RuntimeServices` is deliberately a thin dataclass with everything optional so downstream slices can populate without re-litigating the constructor. Do not add validation in v1.
- Use `from contextlib import asynccontextmanager` for the lifespan.
- `system.yaml` schema reference: `~/arthor-systemmap/schema/system.example.yaml` (symlinked under `packet/refs/system.example.yaml`).
- `.venv/` already exists at the repo root with `pyyaml` and `jsonschema` installed (from packet-intake). The subagent may `pip install -e ".[dev]"` to add the rest, but that's outside `paths_in_scope` so don't commit lock files.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s01-skeleton/tests` is fully green, no files under `paths_out_of_scope` were modified, and no test files under `slices/s01-skeleton/tests/` were modified.
