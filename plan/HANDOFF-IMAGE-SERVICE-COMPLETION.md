# HANDOFF — Image-service product completion (remaining slices)

- **Audience:** Tier-1 orchestrator + Composer subagents in `~/arthor-image-service`
- **Date:** 2026-06-12
- **Branch:** `main`
- **Justin operator lanes (NOT this orchestrator):** vertical hero prompt tuning in inspector / cohort eval — see `HANDOFF-VERTICAL-PROMPTS-AND-USER-ASSETS.md` § V1

---

## Goal

Finish **image-service execution** so user photos, logos, section images, and headshots can flow: **ingest → analyze → auto-treat → generate/edit → R2** — with minimal user input upstream (chat/builder confirm via preview, not quizzes).

**Out of scope (other repos):**

- arthor-ai hero consumer contract / builder wire-up
- arthor-agent SMS copy + `media_confirmation_mode` + preview links
- seo-service `asset_pack_plan` (on `main` already)
- Vertical industry prompt matrix (Justin)

---

## Architecture (locked)

| Layer | Owner |
|-------|-------|
| Ingest | arthor-agent (SMS/email W22/W23) + arthor-ai (web upload) → `user_media_assets` |
| **Analyze + treat + generate** | **arthor-image-service (this handoff)** |
| Plan slots | arthor-seo-service `asset_pack_plan` |
| Merge + submit pack | arthor-ai `RunImagePack` |
| Confirm with user | arthor chat/builder — **default auto + site preview**; confirm-first only low confidence / likeness |
| Place URLs | Cursor / template-repo |

---

## UX default (product — implement analyze confidence for this)

Non-technical users give minimal info. **Default `auto`:**

1. Upload arrives (any channel) → **analyze** (deterministic)
2. If confidence ≥ threshold → apply `recommended_treatment` without asking
3. Generate/edit → preview link → user approves site look (publish gate unchanged)

**Exception `confirm_first`:** low analyze confidence, face-in-hero, likeness — max 3 chips.

Optional user setting later: `media_confirmation_mode: auto | confirm_first` (stored arthor-agent/ai — not this repo).

Image-service stores **`analyze_snapshot` + `recommended_treatment` + `confidence`** on asset metadata; does not send SMS.

---

## Already shipped on `main`

| Area | Evidence |
|------|----------|
| s01–s16 core | asset-pack generate, regenerate-slot, style preview, inspector, R2, callbacks |
| Hero pipeline H1–H6 | `hero_worker.py`, `hero_candidates.py`, compiler v3.2, refs, regenerate-variant |
| ADR-0010 PayloadV1 | `app/payload/models.py` |
| ADR-0012 OpenAI heroes | hero path only |
| `customer_reference_assets` | hero ingress + `hero_reference_plan.py` |
| Pack worker | `app/orchestration/pack_worker.py` — uses **`build_slot_prompt`** (older path), not hero serializer |

---

## Remaining slices (dependency order)

| ID | Slice | Depends | Done when |
|----|-------|---------|-----------|
| **U1** | **`POST /images/assets/analyze`** | — | HMAC route; deterministic signals (mime, dims, aspect, blur, alpha, optional face count/bbox); returns `capabilities`, `recommended_roles[]`, `recommended_treatment`, `confidence` 0–1, `confirm_first_required` bool; pytest; inspector upload lab page |
| **U2** | **Treatment router** | U1 | Pure function `route_treatment(analyze) → TreatmentPlan`; rule table documented in module docstring; unit tests for logo/headshot/interior/ambiguous cases |
| **U3** | **`enhance_headshot` edit** | U1, U2 | New `HeroEditKind` + pack-level regenerate hook; fixed serializer templates (not LLM); QA: face present, sharpness delta; pytest + inspector replay |
| **U4** | **Pack non-hero quality parity** | — | `section_accent`, `card`, `og`, `portrait`, `background` slots use OpenAI serializer variant sharing hero industry/backdrop rules where `slot_kind=hero` uses hero path today; palette QA unchanged; fixture PayloadV1 E2E test |
| **U5** | **User refs in asset-pack** | U1, U4 | `customer_reference_assets` + `ReferencePolicy` honored in pack_worker (condition slots on hero or ref edit per slot); extend `hero_reference_plan` → shared `reference_plan.py` |
| **U6** | **Logo placement manifest** | U1 | Analyze `logo_candidate` → `placement_only` treatment; `GET /images/placements/{site_id}` or analyze embed — **no generation**; returns slot→url map for Cursor |
| **U7** | **Illustrated register (v1)** | U4 | `register_default: illustrated` → `serialize_openai_illustration_prompt()`; one `card` slot prototype; pytest |
| **U8** | **Asset-pack dev E2E ledger** | U4 | `agent-control/dev-launch-ledger.md` documents full pack smoke (fixture PayloadV1 + callback or poll); not hero-only |

**Do not start U7 until U4 green.** **Do not change hero poll/generate JSON** without Justin.

---

## U1 — Analyze API shape (v1)

```
POST /images/assets/analyze
Auth: HMAC (same as hero/asset-pack)

Request:
{
  "asset_id": "uuid-or-stable-id",
  "url": "https://...",           // or r2_key — one required
  "source_channel": "web | sendblue | email_attachment",
  "declared_purpose": "optional string from caller — never trusted alone"
}

Response:
{
  "analyze_version": "1.0",
  "asset_id": "...",
  "mime": "image/jpeg",
  "width": 1200, "height": 1600,
  "capabilities": {
    "logo_candidate": false,
    "headshot_eligible": true,
    "enhance_recommended": true,
    "reference_eligible": true,
    "hero_background_candidate": false
  },
  "recommended_roles": ["team"],
  "recommended_treatment": "enhance_headshot",
  "confidence": 0.86,
  "confirm_first_required": false,
  "warnings": []
}
```

**Deterministic only:** Laplacian blur, alpha detection, aspect class, optional lightweight face detector (document library choice). **No LLM classification.**

---

## Code touch map (by slice)

| Slice | Primary files |
|-------|----------------|
| U1 | `app/routes/asset_analyze.py` (new), `app/quality/asset_analyze.py` (new), `app/inspector/…` |
| U2 | `app/routing/treatment_router.py` (new) |
| U3 | `app/orchestration/hero_worker.py`, `app/style/hero_openai_prompt_serializer.py`, `app/payload/hero_models.py` |
| U4 | `app/orchestration/pack_worker.py`, `app/style/prompts.py` or new `pack_openai_serializer.py` |
| U5 | `app/style/reference_plan.py` (extract from hero), `pack_worker.py` |
| U6 | `app/routes/placements.py` (new) |
| U7 | `app/style/illustration_serializer.py` (new) |
| U8 | `agent-control/dev-launch-ledger.md`, `tests/test_asset_pack_e2e.py` (new or extend) |

---

## Hard constraints

- Deterministic compile/analyze/route — **no LLM on hot path**
- Heroes: OpenAI only (ADR-0012)
- Marketing headlines never in provider prompts
- Idempotency on mutating generate routes unchanged
- pytest green per slice before next slice
- Pod branch `pod/u<N>-<slug>` or direct `main` small commits — Justin approves merge

---

## Cross-repo contracts (read-only)

- `plan/HERO-CANDIDATES-CONSUMER.md` — arthor-ai adapter waits until Justin freezes API
- `plan/adr/0010-payload-contract-v1.md` — pack shape
- seo-service: `asset_pack_plan` response embedded in execution packets
- W22 ingest: `user_media_assets` — analyze writes snapshot into `metadata` jsonb via caller or future callback

---

## Verification ladder

| Tier | Check |
|------|-------|
| T1 | Slice unit tests green |
| T2 | Inspector manual path for slice |
| T3 | U8 full asset-pack smoke documented |
| T4 | Justin visual pass on: enhanced selfie, logo placement, one service page pack |

---

## Update log

- **2026-06-12** — Initial completion slice map U1–U8 + auto-preview UX default.
