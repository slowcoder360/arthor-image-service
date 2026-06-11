# HANDOFF — W21-H hero candidates (builder-time)

> **Justin:** paste `plan/ORCHESTRATOR.md` meta prompt — not this file.

**Workstream:** Generate **exactly 3 homepage hero images** for builder `HeroTriad` — not full asset-pack.

**Consumer:** arthor-ai `HeroPreviewFrame` + `HeroTriad` (arthor-ai `plan/HANDOFF-W41-ATELIER.md`).

**Done-when:** `POST /images/hero-candidates/generate` + `GET /images/hero-candidates/{run_id}`; 3 temp R2 URLs; shared style profile; HMAC auth; pytest with mocked provider.

---

## API

```text
POST /images/hero-candidates/generate
  Input: site_id or style profile + 3 variant angle hints (headline/subhead per variant)
  Output: 202 + agent_run_id

GET /images/hero-candidates/{run_id}
  Output: { status, variants: [{ id, image_url, ... }] }
```

**Idempotency:** `hero:{site_id}:{variant_set_hash}`

**Aspect:** homepage hero only. Reuse existing provider worker + R2 patterns from asset-pack slices.

---

## Out of scope

- Full `POST /images/asset-pack/generate` build-pipeline integration (see `plan/adr/0010-payload-contract-v1.md` for full pack).
- Section/card/og slots.

---

## Read order

1. This file
2. `plan/CONTEXT.md`
3. `plan/adr/0010-payload-contract-v1.md` (narrow payload only)
4. Existing asset-pack worker code

---

## Agent prompt

```
You are W21-H-A in ~/arthor-image-service.

Read ONLY plan/HANDOFF-W21-H-HERO-CANDIDATES.md and existing image generation worker code.

Task: POST /images/hero-candidates/generate + GET poll; exactly 3 homepage heroes; HMAC; idempotency; R2 temp URLs; pytest with mocked provider.

Branch pod/w21-h-hero-candidates. Do not merge to main.
```
