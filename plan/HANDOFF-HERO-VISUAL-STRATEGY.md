# Handoff — Hero visual strategy, OpenAI-only, QA gates

- **From:** W21-H hero session (compiler v2, A/B lab, creative direction brainstorm)
- **Date:** 2026-06-11
- **Branch:** `pod/w21-h-hero-candidates` (local work; verify `git status` before assuming remote)
- **Supersedes for creative/ops direction:** `plan/HANDOFF-HERO-PROMPT-PIPELINE.md` (still useful for file map; decisions below are current)

---

## What we're doing

Move hero-candidates from **equipment/industry prompts** to a **visual strategy layer** (scene archetypes, authenticity modes, reference plans) with **OpenAI-only** generation for heroes. Keep the pipeline **deterministic** (lookup tables + templates, no LLM in compile/QA path). Add **deterministic post-gen gates** to flag bad images before they reach the builder. arthor-ai already ships `hero_candidates.2`; pass an updated consumer doc after image-service pods land — no blocker on arthor-ai today.

---

## Decisions (locked for now)

| Decision | Rationale |
|----------|-----------|
| **Drop Google for heroes** | A/B: artifacts, UI/text hallucination, safe-zone failures, chair bias. OpenAI (`gpt-image-2`) materially better on humans, no painted copy, composition. Google code stays for asset-pack; heroes default OpenAI only. |
| **Compiler v2 job-first** | `hero_job` (trust/experience/outcome) from tone; industry = backdrop modifier. Shipped in `hero_archetypes.py` + `hero_prompt_compiler.py` v2.0. Still converges on consultation/chair — needs **scene catalog** layer. |
| **Ingress ≠ provider prompt** | Left panel in A/B lab is arthor-ai **request contract** (business, headlines for metrics). Provider text is `metadata.hero_provider_prompts[]` after compile. Headlines must never appear in provider prompts (verified). |
| **Strategy before longer prompts** | ~2.4k-char layout essays hurt Google and may still steer OpenAI to wrong scenes. Next win is **what to request**, not more instructions. |
| **Optional LLM improver off** | `hero_prompt_improve_enabled=False` default. Keeps compile deterministic. |
| **arthor-ai contract** | v2 implemented on their side (`copy_overlay`, `copy_metrics`, `payload_version`). New fields (visual strategy, references, edit kinds) = follow-up doc after our pods — do not block current integration. |

---

## Creative direction (from brainstorm)

### Hero jobs (tone mapping)

| Tone | Job | Intent |
|------|-----|--------|
| search | trust (+ outcome hint) | Recognition, warmth |
| story | experience (+ trust) | Feel of the place / relationship |
| offer | outcome | Result customer buys |

### Scene archetypes (catalog — not yet implemented)

Small reusable set; industry modulates, does not define subject.

| Archetype | Example (family dental) | Avoid |
|-----------|-------------------------|-------|
| `shared_joy` | Mom + daughter smiling at each other | Empty operatory, equipment hero |
| `confident_smile` | Natural adult smile, warm light | Stock grin at camera |
| `threshold_invitation` | Dentist in doorway, welcoming gesture | Seated consultation in chairs |
| `threshold_relief` | Family leaving, relaxed | Clinical room as hero |
| `desk_side_guidance` | Plan talk at table, no dental chairs | Authority-only default for GP |
| `environment_warmth` | Light, materials, kid corner — no people | Fallback if faces fail QA |

**Family GP dental triad (proposed default):** search → `shared_joy` or `confident_smile`; story → `shared_joy` / `threshold_relief`; offer → `confident_smile` / outcome. **Not** seated consultation.

**Selection inputs:** `icp_summary`, `priority_services`, `tone_angle`, optional explicit `scene_archetype` from arthor.

### Authenticity modes

| Mode | User uploads | Promise |
|------|--------------|---------|
| `stylized` | None | Professional vibe, not literal space |
| `space_anchored` | `interior` ref | Lighting/materials match; new composition |
| `likeness_anchored` | `team` headshot + consent | OpenAI edit + preserve prompt; "inspired by," not passport |

References: extend `customer_reference_assets` with `usage_hint` + optional `note`. Builder UI sets **role** (required); note optional. Image-service builds `reference_plan` — no clarification loop at compile time.

### Multi-reference + edits (future contract sketch)

- Up to N refs with `role`, `usage_hint`, `note`, `asset_id`
- OpenAI `gpt-image-2` supports multi-image edit; we only pass **first** ref today (`openai_image.py`)
- **Edit kinds:** `retry` (seed), `tweak` (modifier on brief), `reference` (swap refs), `rescene` (new archetype)
- Hero **regenerate-variant** endpoint does not exist yet (pack has `POST /images/regenerate-slot`)

---

## What’s implemented (image-service)

- **Compiler v2.0** — job-first prompts, anti-chair avoid lists, softer safe-zone language (`app/style/hero_archetypes.py`, `app/style/hero_prompt_compiler.py`)
- **POST pre-compile** — `hero_provider_prompts[]` on run metadata (`app/routes/hero_candidates.py`)
- **Worker** — loads precompiled prompts; parallel triad; prompt_hash cache (`app/orchestration/hero_worker.py`)
- **OpenAI default** — `gpt-image-2`, `HERO_DEFAULT_PROVIDER=openai_image`
- **v2 contract** — ADR `plan/adr/0011-hero-candidates-v2.md`
- **A/B inspector** — ingress vs compiled prompts labeled; compiler version in results; stale-run reconcile
- **QA hooks (partial)** — `check_palette_drift`, `classify_hero_failure`, `failure_mode` on asset metadata; `scripts/hero_quality_batch.py` for offline CLIP/palette
- **Tests** — hero compiler + pipeline tests green (16+)

### Known gaps / bugs observed

- Old A/B runs in DB still **compiler v1.0** (chair/operatory) — must launch **fresh** runs after server restart; UI warns if v≠2.0
- Google Pro (`gemini-3-pro-image`) tested — slow, still hallucinates UI/copy/safe zones
- Prompt cache can replay prior image for same `site_id` + `prompt_hash` + provider — bust on compiler version bump
- Hero path: `reference_images=None` always — pack path has reference conditioning only

---

## Determinism & anti-complexity principles

**Do**

1. **Strategy = lookup tables** — `(industry, icp_keywords, tone) → scene_archetype + authenticity_mode`. No LLM.
2. **Compiler = catalog + short brief + fixed layout tail** — target &lt;800 chars scene body; layout rules in versioned template fragment.
3. **QA = deterministic checks only** — no LLM judge in v1.
4. **Version everything** — `compiler_version`, `strategy_version`, `scene_catalog_version` on run metadata; cache keys include versions.
5. **Typed edits** — builder sends `edit_kind`, not raw provider prompts.
6. **One provider for heroes** — OpenAI only; removes A/B matrix explosion.
7. **Fail open, flag hard** — bad images get `failure_mode` + still stored; builder can retry; optional auto-retry **once** on specific modes with seed+1.

**Don’t**

- LLM prompt improver on hot path (canary only if ever)
- Per-industry prose templates (dozens of NAICS blocks)
- Long ingress → provider passthrough
- Google hero path until strategy + QA stable
- ControlNet / face-swap vendors until OpenAI edit path exhausted

---

## Self-catch bad generations (QA gate design)

Goal: **automatic flags before builder shows image**, not auto-fix. All deterministic.

| Check | Method | `failure_mode` | Auto-retry? |
|-------|--------|----------------|-------------|
| Rendered text / UI | OCR or high-contrast edge heuristic in top 14% + left safe zone | `rendered_text` / `rendered_ui` | Once, seed+1 |
| Palette off-brand | Existing `check_palette_drift` | `palette_drift` | No (flag only) |
| Safe zone violated | Left inset mean variance / edge density vs center (simple CV) | `safe_zone_violation` | Once |
| Wrong scene class | Optional CLIP text match vs archetype label (offline calibrated) | `scene_mismatch` | No in v1 |
| Provider errors | Existing string classify | `moderation_blocked`, etc. | Per retry policy |
| Likeness drift | Deferred — needs edit path + human review |

**Pipeline placement:** after `generate_single`, before `mark_asset_uploaded`. Patch `external_media_assets.metadata.failure_mode`; surface in poll response + builder. **Do not fail run** unless all 3 variants hard-fail.

**Existing code:** `app/quality/hero_failure_modes.py` (extend modes), `app/quality/palette_variance.py`, `scripts/hero_quality_batch.py`.

**Explicitly out of v1:** LLM vision judge, ControlNet, per-image human review in image-service.

---

## Proposed pods (spin off from here)

Execute in order; each pod = branch + handoff slice + tests-first where behavior is new.

### Pod H1 — OpenAI-only heroes (small)

- `HERO_DEFAULT_PROVIDER=openai_image` enforced for hero worker
- A/B lab: hide or disable Google arm; label "OpenAI heroes only"
- Default sample payload `default_provider_hint: openai_image`
- Document in ADR / `.env.example`
- **No** delete Google provider — pack may still use it

### Pod H2 — Visual strategy layer + scene catalog

- New `app/style/hero_visual_strategy.py` — resolve archetype + authenticity mode from ingress
- Scene catalog JSON or Python dict (versioned)
- Compiler v3: strategy output → short scene brief (replace job+industry prose soup)
- Tests: family dental → `shared_joy` not consultation; compiler_version 3.0
- Persist `hero_visual_strategy` on run metadata

### Pod H3 — Deterministic QA gates

- `app/quality/hero_post_checks.py` — text-in-safe-zone, safe-zone occupancy
- Wire in `hero_worker._finalize_hero_slot`
- Extend `failure_mode` enum + poll API
- Optional: single auto-retry on `rendered_text` / `safe_zone_violation`
- Tests with synthetic PNG fixtures

### Pod H4 — Reference assets (optional uploads)

- Extend hero ingress: `customer_reference_assets[]` with `usage_hint`, `note`
- Resolve URL → bytes; `reference_plan` in metadata
- Worker: OpenAI edit when refs present; multi-image when provider upgraded
- Likeness consent flag (boolean on asset or policy)
- **Defer** until H2 stable

### Pod H5 — Hero edit / regenerate-variant

- `POST /images/hero-candidates/regenerate-variant` (mirror pack regenerate)
- Edit kinds: retry, tweak, reference, rescene
- Supersession pattern unchanged
- Inspector or builder contract doc for arthor

### Pod H6 — arthor-ai consumer doc (read-only deliverable)

- Update `plan/adr/0011` or new `0012` with strategy fields, reference shape, edit API
- Pass to arthor-ai team after H2–H3 land; they already have v2

---

## arthor-ai coordination

- **Now:** They send `hero_candidates.2`; image-service compiles v2 prompts; OpenAI generates.
- **Later:** Optional `visual_strategy` / enriched `customer_reference_assets` on ingress — arthor builder captures role + note on upload.
- **Do not** require arthor changes for H1–H3; strategy can be derived server-side from existing fields (`icp_summary`, `industry`, `tone_angle`).

Files on their side (reference): `hero-candidates-types.ts`, `build-hero-payload.ts`.

---

## What's next (single concrete step)

**Pod H1:** OpenAI-only hero path + remove Google from A/B default — small PR, unblocks honest iteration on OpenAI quality while H2 is planned.

Command to resume: read this file + `app/style/hero_archetypes.py` + `app/style/hero_prompt_compiler.py`; implement Pod H1 or start Pod H2 per Justin's priority.

---

## Open questions

- Auto-retry once on QA failure — yes/no for builder UX?
- CLIP `scene_mismatch` in production gate or inspector-only?
- Full triad re-run vs single-variant edit as default builder action?
- Pack generation: keep Google or OpenAI-only entire service?

---

## Files to read

1. `plan/HANDOFF-HERO-VISUAL-STRATEGY.md` — this file
2. `app/style/hero_archetypes.py`, `app/style/hero_prompt_compiler.py`
3. `app/routes/hero_candidates.py`, `app/orchestration/hero_worker.py`
4. `plan/adr/0011-hero-candidates-v2.md`
5. `app/quality/hero_failure_modes.py`, `app/quality/palette_variance.py`
6. `app/inspector/hero_ab.py`, templates under `app/inspector/templates/hero_ab*.html`
7. `plan/deep-research-report (18).md` — provider research (Google deprioritized)

## Do not re-read

- Full agent transcript
- Entire `slices/` tree unless touching pack regenerate patterns

## Quirks

- **Server restart required** after compiler/env changes — uvicorn loads code at startup only
- **Poll URLs are DB-only** — not Google/OpenAI status
- **Compiled prompts** only on runs after v2 deploy; old run links show v1 chair prompts
- **Ingress textarea** is not the provider prompt — check Results → Compiled prompts

---

## Runtime (local)

- Uvicorn: `http://127.0.0.1:8010`
- `GOOGLE_IMAGE_MODEL` may be set but **heroes should ignore Google** after Pod H1
- Inspector A/B: `/inspector/hero-ab`
