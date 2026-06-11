# HANDOFF — W21-H deploy + smoke (service side)

> **Justin:** paste `plan/ORCHESTRATOR.md` meta prompt — not this file.

**Workstream:** Make hero-candidates API **reachable** from arthor-ai dev/staging. Code landed on `pod/w21-h-hero-candidates` @ `11c5f14` — this slice is deploy + ledger, not new endpoints.

**Consumer:** arthor-ai `HANDOFF-W21-H-CONSUMER-WIREUP.md` (separate repo).

**Done-when:** Local or staging uvicorn serves signed POST → poll → 3 URLs (mocked provider in CI; real provider optional for manual smoke); `agent-control/dev-launch-ledger.md` documents happy path; pytest green.

---

## Already built

| Route | File |
|-------|------|
| `POST /images/hero-candidates/generate` | `app/routes/hero_candidates.py` |
| `GET /images/hero-candidates/{run_id}` | same |
| Request model | `app/payload/hero_models.py` |
| Worker | `app/orchestration/hero_worker.py` |
| Tests | `tests/test_hero_candidates.py` |

Branch: `pod/w21-h-hero-candidates`. Do not re-implement — verify, deploy, document.

---

## Deploy checklist

1. `pytest tests/test_hero_candidates.py -q` green (venv with project deps).
2. Env: `FASTAPI_ARTHOR_SHARED_SECRET`, `DATABASE_URL` (Neon dev branch), R2 creds, provider API key (`google_nano_banana` default).
3. Run uvicorn; HMAC smoke: signed POST with body from `tests/test_hero_candidates.py` `_build_hero_request()`.
4. Poll until `status: complete` and `urls.length === 3`.
5. Record commands + URLs in `agent-control/dev-launch-ledger.md`.

---

## POST example (minimal reference)

See `tests/test_hero_candidates.py` function `_build_hero_request()` — canonical valid payload.

Idempotency key pattern: `hero:{site_id}:{hash}`.

---

## Out of scope

- Changing GET/POST shape (consumer adapts in arthor-ai W21-H-C)
- Full asset-pack routes
- Merge to `main` without Justin
- Prod Neon apply without Q14 `\d` + W11 coordination

---

## Report back

Branch SHA, pytest exit code, base URL Justin should set in arthor-ai `ARTHOR_IMAGE_SERVICE_BASE_URL`, any blocker (DB pool, R2, provider).
