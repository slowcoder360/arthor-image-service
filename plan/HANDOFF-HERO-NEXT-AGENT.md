# Handoff — Hero pipeline landed; next: site-wide images + brand illustrations

- **From:** Hero Visual Strategy wave + dental backdrop + OpenAI serializer session
- **Date:** 2026-06-11
- **Branch:** `pod/w21-h-hero-candidates` (push after this handoff)
- **Consumer doc:** `plan/HERO-CANDIDATES-CONSUMER.md` → pass to arthor-ai
- **Do not merge to `main` without Justin**

---

## What shipped (verified + Justin-approved visually)

| Layer | Status | Notes |
|-------|--------|-------|
| H1–H6 hero wave | **DONE** | OpenAI-only, compiler v3.x, QA gates, refs, regenerate-variant |
| Dental backdrop fix | **DONE** | Clinic reception/consult cues; exclude home interiors |
| **OpenAI serializer v3.2** | **DONE** | `hero_openai_prompt_serializer.py` — model-native brief, not debug labels |
| Inspector viewport lab | **DONE** | Desktop vs mobile; stale banner expects compiler **v3.2** |
| Regenerate smoke fixes | **DONE** | JSON payload parse + `get_image_provider_for_services` |

**Justin feedback:** Desktop hero v3.2 results are **excellent** — spacing/comp/realism kept; backdrop now reads dental, not residential.

**Prompt shape sent to gpt-image-2:**
```
Create a photorealistic homepage hero background plate for …
Subject: …
Setting: … (dental clinic anchors)
Composition: … (positive safe-zone language)
Photography: …
Invariants: … (not long Avoid lists)
```

**Research:** DR 20 in `plan/deep-research-report (20).md`; subagent confirmed OpenAI prefers **line-broken plain English**, explicit **photorealistic**, **Invariants** over Avoid lists; **no XML/JSON wrappers**.

---

## Runtime

- Local: `http://127.0.0.1:8010`
- Inspector: `/inspector/hero-ab` — launch **fresh** runs (no old `desktop_run=` URLs; v3.0 runs show stale banner)
- Restart uvicorn after compiler changes
- Postgres: `arthor-image-pg` on `:5440`

---

## Code map (hero — done)

| Area | Path |
|------|------|
| Visual strategy + dental backdrop | `app/style/hero_visual_strategy.py` |
| OpenAI serializer | `app/style/hero_openai_prompt_serializer.py` |
| Compiler | `app/style/hero_prompt_compiler.py` (`COMPILER_VERSION = "3.2"`) |
| Worker | `app/orchestration/hero_worker.py` |
| Routes | `app/routes/hero_candidates.py` |
| Consumer contract | `plan/HERO-CANDIDATES-CONSUMER.md` |
| ADR | `plan/adr/0012-hero-openai-only-and-visual-strategy.md` (accepted) |

---

## Immediate follow-ups (small, hero-only)

1. **Desktop → mobile seed** — User wants winning desktop asset as reference for mobile (same people/setting). H4 edit path exists; wire `source_hero_asset_id` or `mobile_from_desktop` edit kind.
2. **arthor-ai consumer** — W21-H-C wire-up from `HERO-CANDIDATES-CONSUMER.md` (refs, regenerate, `failure_mode`).
3. **Hero `quality=high`** for finals — API param in `openai_image.py`, not prompt (DR 20).

---

## Path 1 — Site-wide image generation (headers + section images)

### Justin's intent

Beyond homepage hero triad: generate **headers for other pages** and **images for other sections** (services, about, etc.) with **exact pixel dimensions** per slot.

### Architecture tension (needs decision with Justin)

| Option | Owner of page comp | Flow |
|--------|-------------------|------|
| **A — image-service centric** | arthor-ai / builder agent submits per-slot payloads (like today hero) | Cursor agent or builder reads sitemap → POST narrow contracts per asset |
| **B — SEO service centric** | **arthor-seo-service** owns sitemap, keyword planning, copy gen, **and full-page composition** | SEO service passes **one batch payload** to image-service: all image requests for a site with dimensions, tone, page_id, slot_id |
| **C — hybrid** | SEO service emits **page spec / asset manifest** (JSON); image-service executes | Manifest = source of truth for pixel sizes + copy-safe zones; no LLM in image-service |

**Context shift:** Sitemap + keyword + copy planning **moved to SEO service** — Option B/C more aligned than having Cursor agent hand-craft payloads.

### Open questions for next agent

- Does SEO service already have (or plan) a **page layout / asset manifest** schema?
- Reuse **asset-pack** pipeline (`PayloadV1` + slots) vs new **site-images** contract?
- Same **StyleProfile** + **OpenAI serializer** pattern for non-hero slots?
- Idempotency: `site:{site_id}:page:{page_id}:slot:{slot_id}` ?
- Inspector: new lab or extend hero-ab?

### Suggested first step

Read SEO service handoffs for page comp output shapes; draft ADR comparing **manifest-from-SEO** vs **per-request-from-builder**. Do **not** implement until Justin picks A/B/C.

---

## Path 2 — On-brand infographics & illustrations

### Justin's intent

Generate **infographics, illustrations, ad creatives** on-brand — often **user-requested** or **SEO/CRO-driven**. Better results from **OpenAI image model** than Remotion for static/hero-adjacent graphics.

### Ideas in flight

- **Brand style token** — lighting, feel, colors, register (photo vs illustrated) persisted per site; feeds all generators (hero already uses `StyleProfile`).
- **SVG standardization** — latest idea files mention SVGs for consistent outputs; tradeoff vs raster from OpenAI.
- **Page screenshot as seed** — space-anchored / layout-anchored generation (extend H4 reference plan: `interior` / full-page screenshot ref).

### Open questions

| Question | Notes |
|----------|-------|
| SVG vs PNG pipeline? | OpenAI → PNG → trace/SVG? Or illustrated **register** in StyleProfile + raster only? |
| Separate **run_type** (`illustration`, `infographic`, `ad_creative`) vs slot_kind on pack? | |
| CRO/SEO trigger | Who decides an infographic is needed — manifest field `asset_kind: infographic`? |
| Multi-step | Generate illustration → QA (palette drift exists) → optional edit with brand ref |
| Animated | Still out of scope for image-service? Remotion only for motion? |

### Suggested first step

Inventory `app/style/profile.py`, `StyleProfile`, pack slot kinds; read brainstorm **idea19–22** / SVG mentions in `~/arthor-brainstorm/inbox/`. Prototype **one** illustrated slot with serializer variant (`serialize_openai_illustration_prompt`) sharing brand tokens — no new API until manifest shape is clear.

---

## Hard constraints (carry forward)

- Heroes: **OpenAI only** (ADR 0012)
- Compile/strategy/QA: **deterministic**, no LLM on hot path
- Ingress headlines → **copy_metrics only**, never provider prompts
- Provider prompts: **model-native** via serializer, not inspector debug format
- Do not merge to `main` without Justin

---

## Read first (next session)

1. `plan/HANDOFF-HERO-NEXT-AGENT.md` — this file
2. `plan/HANDOFF-HERO-VISUAL-STRATEGY.md`
3. `plan/HERO-CANDIDATES-CONSUMER.md`
4. `plan/deep-research-report (20).md`
5. `app/style/hero_openai_prompt_serializer.py`
6. SEO service: page comp / output shapes (cross-repo — `~/arthor-seo-service/plan/`)
7. Brainstorm: `~/arthor-brainstorm/inbox/idea19.md`–`idea22.md`, SVG threads

---

## Do not re-do

- Hero H1–H6 pods
- Dental backdrop + serializer unless regressions
- Full triad smoke (6+ images) without Justin asking

---

## Single concrete next step (pick with Justin)

**If hero mobile seed:** small pod — desktop asset → reference edit for mobile viewport.

**If site-wide images:** cross-repo read → ADR **who owns page comp manifest** (SEO vs image-service).

**If illustrations:** StyleProfile + illustrated register + one prototype slot.
