# arthor-image-service

FastAPI service for Arthor image generation, asset packs, and inspector tooling. Canonical payload contract: `plan/adr/0010-payload-contract-v1.md`.

## Local run

Create a virtual environment, install the package in editable mode with dev extras, configure `.env`, then start uvicorn (same shape as arthor-seo-service):

```bash
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

Default dev base URL: `http://127.0.0.1:8010`. Health: `GET /healthz`.

Manual HMAC driver (service must be running):

```bash
python scripts/send_request.py preview    # POST /images/style-profile/preview
python scripts/send_request.py generate   # POST /images/asset-pack/generate
```

## Tests

```bash
pytest
```

Slice-scoped tests live under `slices/<id>/tests/`; shared pytest hooks are in `tests/conftest.py`. CI and local runs ignore `packet/` refs (`pytest.ini`).

Validated 2026-06-07: `232 passed, 73 skipped` (skipped = `requires_db` / `requires_r2` without live infra).

## Environment

| Variable | Required for | Notes |
|----------|--------------|-------|
| `DATABASE_URL` | Persistence | Shared Neon dev branch; see `docs/migrations.md` |
| `FASTAPI_ARTHOR_SHARED_SECRET` | HMAC ingress + outbound callbacks | Same secret as arthor-ai / seo-service |
| `INSPECTOR_ADMIN_TOKEN` | `/inspector/*` GUI | Bearer on login form |
| `R2_ENDPOINT_URL` | Asset upload | Cloudflare R2 S3-compatible endpoint |
| `R2_ACCESS_KEY_ID` | R2 | |
| `R2_SECRET_ACCESS_KEY` | R2 | |
| `R2_BUCKET` | R2 | e.g. `arthor-media` |
| `OPENAI_API_KEY` | OpenAI image provider | At least one provider key for real generation |
| `GOOGLE_API_KEY` | Gemini / nano-banana provider | |

Optional tuning: `MAX_CONCURRENT_PACKS`, `PALETTE_DRIFT_THRESHOLD`, `COLD_STORAGE_INTERVAL_SECONDS`, `LOG_LEVEL` — see `.env.example`.

## Pinned model versions

Recorded at implementation time on every asset and `tool_calls` row:

| Provider | `model_version` | Source |
|----------|-----------------|--------|
| OpenAI Images | `gpt-image-1` | `app/providers/openai_image.py` |
| Google nano-banana | `gemini-2.5-flash-image` | `app/providers/google_nano_banana.py` |

Bump these constants when rotating provider models; update cost tables in the same change.

## Database migrations

See `docs/migrations.md`. **Do not apply to prod** without W11 coordination. Reconcile with arthor-ai `drizzle/0015_image_service_tables.sql` before apply (Q14 `\d` first).

## Inspector

Operator-only HTMX UI at `/inspector/runs`, `/inspector/runs/{id}`, `/inspector/cost`. Authenticate via `POST /inspector/login` with `INSPECTOR_ADMIN_TOKEN`.
