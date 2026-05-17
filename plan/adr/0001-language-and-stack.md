# ADR 0001: Language and stack

- Status: proposed
- Date: 2026-05-17

## Context

The packet (`packet/SPEC.md`) declares this is a FastAPI service mirroring `arthor-seo-service`'s pattern. `arthor-seo-service` is unbuilt, so we infer from `arthor-agent`, which is already FastAPI + Python.

## Options considered

- **Python + FastAPI** — consistent with arthor-agent, the only existing FastAPI sibling. Mature image-generation SDKs (openai-python, google-genai). `aiobotocore` for async R2. `asyncpg` mature and battle-tested.
- **TypeScript + Hono/Express** — consistent with arthor-ai. Cuts down on cross-language tooling. But: arthor-ai is the only TS service and it's primarily a Next.js app, not a backend service; we'd be inventing patterns. Image SDKs are TS-OK but less mature than Python equivalents.
- **Python + Litestar** — newer, faster than FastAPI. But: zero ecosystem precedent and adds a learning cost for any future arthor-agent maintainer.

## Decision

**Python 3.13 + FastAPI**, matching the language and HTTP framework of arthor-agent. Specific libraries:

| Concern | Library |
|---|---|
| HTTP framework | `fastapi` |
| Validation | `pydantic` (v2) |
| Config | `pydantic-settings` |
| DB driver | `asyncpg` |
| HTTP client (outbound callback) | `httpx` (async) |
| R2 / S3 client | `aiobotocore` |
| Templates | `jinja2` (via `fastapi.templating.Jinja2Templates`) |
| Static assets | `fastapi.staticfiles.StaticFiles` |
| OpenAI image | `openai` (official Python SDK) |
| Gemini image | `google-genai` (official Python SDK) |
| Image post-processing (palette extraction) | `Pillow` (already required for dimension validation) |
| Test framework | `pytest` + `pytest-asyncio` |
| Lint / format | `ruff` |
| Type check | `mypy` (strict on `app/`) |

Project layout (per ADR-0002): `pyproject.toml` at root; `app/` for runtime code; `db/` for raw SQL migrations + queries; `tests/` for pytest; `docs/` for runbooks; `static/` + `app/templates/` for the inspector.

## Consequences

What gets easier:
- Recruiting any future arthor-agent maintainer to read this code with zero context-switch cost.
- Shared idioms across the two FastAPI services (auth, app.state, migrations).

What gets harder:
- Cross-language type sharing with arthor-ai's TS payload contract. Mitigation: keep the v1 payload schema language-agnostic (`docs/payload-schema.v1.json` is the source of truth; both sides validate against it).
