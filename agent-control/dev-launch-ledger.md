# Dev E2E Failure Ledger — arthor-image-service (W21 Track A)

Path-unblocker ledger for Pod I-A prod readiness. Updated 2026-06-07 on branch `pod/w21-track-a`.

## Current Target Path

App: arthor-image-service (FastAPI)
Path: HMAC-signed `POST /images/asset-pack/generate` → background pack worker → R2 upload → Postgres rows → HMAC callback
Goal: Reproducible dev happy path documented; pytest green without live Postgres/R2 for unit slice coverage

## Status

- [x] App boots (`GET /healthz` → 200, no pool required)
- [x] Env vars load (`app/config.py` Settings + `.env.example`)
- [x] Auth works (s03: HMAC verify; bad/missing sig → 401)
- [ ] DB connects (local `localhost:5440` not running this session — see Migration status)
- [x] Main happy path completes (pytest mocks: s10 asset-pack + callback, s07 R2 moto, s08/s09 providers)
- [x] Webhooks/callbacks work (s10 `test_callback_signed_and_posted`, `test_callback_status_complete_vs_partial`)
- [x] Logs are clean enough to debug (`LOG_LEVEL=INFO` default)

---

## Validated commands (2026-06-07)

### Install + test

```bash
cd ~/arthor-image-service
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

**Result:** exit code `0` — `232 passed, 73 skipped, 1 warning` (73 skips = `requires_db` / `requires_r2` without live infra).

### Local deploy (same hosting shape as seo-service: uvicorn + `.env`)

```bash
source .venv/bin/activate
cp .env.example .env   # fill secrets (see README § Environment)
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

**Base URL:** `http://127.0.0.1:8010` (matches `scripts/send_request.py`).

**Health check:**

```bash
curl -s http://127.0.0.1:8010/healthz | jq .
# {"status":"ok","service":"arthor-image-service","version":"0.1.0"}
```

### HMAC smoke (manual, service must be running + DB migrated)

```bash
python scripts/send_request.py preview   # cheap style probe
python scripts/send_request.py generate  # full pack (needs providers + R2 + DB)
```

Unsigned POST → `401`. Signed POST with MVP PayloadV1 → `202` + `agent_run_id` (s10 tests cover idempotent replay).

### Inspector GUI smoke (pytest, mocked DB)

Covered by s13 (`/inspector/runs`, `/inspector/runs/{id}`) and s15 (`/inspector/cost`). Login: `POST /inspector/login` with `INSPECTOR_ADMIN_TOKEN` → session cookie → Bearer-free HTMX pages.

---

## Migration status (Q14)

**Target:** shared dev Neon branch (W11 custodian: arthor-ai `drizzle/0015_image_service_tables.sql`).

**Probe attempted 2026-06-07:** `DATABASE_URL` in `.env` points at `localhost:5440/arthor_image`; connection refused (no local Postgres). `psql` not on PATH. Schema reconciliation documented below; live `\d` deferred to operator when dev Neon or local Docker is up.

### Reconcile service `001`–`003` vs arthor-ai `drizzle/0015`

| Object | Service migration | Drizzle 0015 | Apply rule |
|--------|-------------------|--------------|------------|
| `external_media_assets` | `001_external_media_assets.sql` | `CREATE TABLE` same columns/indexes | Skip 001 if table exists (IF NOT EXISTS safe) |
| `image_request_payloads` | `002_image_request_payloads.sql` | `CREATE TABLE` same + UNIQUE idempotency | Skip 002 if table exists |
| `tool_calls` cost cols | `003_tool_calls_cost_columns.sql` | 0015 creates full `tool_calls` **with** `cost_cents`, `provider`, `model_version` | If harness `tool_calls` exists **without** those columns → run **003 only**. If 0015 applied → **003 is no-op** (`ADD COLUMN IF NOT EXISTS`) |

**Do not duplicate:** If W11 Phase B already applied `drizzle/0015` on the branch, do **not** re-run 001–002. Running 003 alone is harmless.

### Q14 probe script (run when DB is reachable)

```bash
python - <<'PY'
import asyncio, asyncpg, os
async def main():
    url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(url)
    for t in ("external_media_assets", "image_request_payloads", "tool_calls", "agent_runs"):
        n = await conn.fetchval(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name=$1", t)
        print(t, "present" if n else "MISSING")
    await conn.close()
asyncio.run(main())
PY
```

### Local-only bootstrap (not shared Neon)

```bash
psql "$DATABASE_URL" -f db/dev/000_local_harness_bootstrap.sql
psql "$DATABASE_URL" -f db/migrations/001_external_media_assets.sql
psql "$DATABASE_URL" -f db/migrations/002_image_request_payloads.sql
psql "$DATABASE_URL" -f db/migrations/003_tool_calls_cost_columns.sql
```

---

## Pinned model versions (at build time)

| Provider | `model_version` constant | Env key |
|----------|-------------------------|---------|
| OpenAI Images | `gpt-image-1` (`app/providers/openai_image.py`) | `OPENAI_API_KEY` |
| Google Gemini / nano-banana | `gemini-2.5-flash-image` (`app/providers/google_nano_banana.py`) | `GOOGLE_API_KEY` |

Stamped on every `external_media_assets` row and `tool_calls.model_version`.

---

## Blockers

(none for Track A unit/contract scope — live E2E blocked on operator Postgres + R2 + provider keys)

### D001 — Live dev Neon `\d` not captured

Status: Deferred
Severity: Non-blocker for pytest / contract tests
Reason deferred: No reachable dev DB in this pod session
Suggested follow-up: Justin or W11 agent runs Q14 probes on target Neon branch before prod apply

---

## Deferred Issues

### D002 — arthor-ai integration (Track B)

Reason deferred: Out of repo scope for Pod I-A
Evidence: No `ArthorImageClient` in arthor-ai yet (handoff § Track B)
Suggested follow-up: Pod I-B per `arthor-image-service-launch-handoff.md`
