# ORCHESTRATOR — arthor-image-service (Builder populate wave)

**You paste only the meta prompt at the bottom.**

**Status:** W21-H-A **DONE** on `pod/w21-h-hero-candidates` @ `11c5f14`. Active slice = **deploy smoke** for arthor-ai consumer.

---

## Slice queue

| ID | Status | HANDOFF | Branch | Done when |
|----|--------|---------|--------|-----------|
| W21-H-A | DONE | `HANDOFF-W21-H-HERO-CANDIDATES.md` | `pod/w21-h-hero-candidates` | pytest green |
| **W21-H-D** | OPEN | `HANDOFF-W21-H-DEPLOY-SMOKE.md` | same branch | uvicorn smoke + dev-launch-ledger filled |

**Downstream (arthor-ai repo):** W21-H-C consumer wire-up — separate chat.

---

## Operating rules

- Exactly 3 hero variants — not full asset-pack.
- Do not change API shape without syncing arthor-ai consumer HANDOFF.
- Idempotency key: `hero:{site_id}:{variant_set_hash}`
- Do not merge to `main` without Justin.

---

## Meta prompt (paste this)

```
You are the Tier-1 orchestrator for ~/arthor-image-service — deploy smoke wave.

Read FIRST:
- plan/ORCHESTRATOR.md
- plan/HANDOFF-W21-H-DEPLOY-SMOKE.md
- plan/HANDOFF-W21-H-HERO-CANDIDATES.md (reference only — already landed)
- plan/CONTEXT.md

Checkout pod/w21-h-hero-candidates. W21-H-A is done.

Your job:
1. pytest tests/test_hero_candidates.py green.
2. Run local/staging uvicorn with DATABASE_URL + R2 + provider keys + FASTAPI_ARTHOR_SHARED_SECRET.
3. HMAC smoke: POST generate + GET poll → 3 urls; document in agent-control/dev-launch-ledger.md.
4. Push branch if fixes needed; report SHA + base URL for arthor-ai ARTHOR_IMAGE_SERVICE_BASE_URL.

Do not merge to main. Do not start asset-pack integration.
```
