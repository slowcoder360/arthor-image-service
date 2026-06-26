# Hero layout-archetype wave — orchestration log

## 2026-06-25 — research + slice + tests-first

**Objective:** Stop being fragile for non-local-service web design. Add a deterministic `hero_layout_archetype` decision layer *above* the photographic scene/corpus pipeline so tech/agency/SaaS brands get the right hero composition + imagery instead of a forced full-bleed human photo. Hero-only v1.

**Outcome:** Research landed, wave sliced (s17–s21), red suite committed. Ready to dispatch builders. No production `app/` code written this run.

### What changed (this run)
- Dispatched 3 Composer-2.5 research pods (OS builders, layout taxonomy, anti-slop skill files) → `plan/research/POD-A|B|C-*.md`.
- Synthesis + decisions → `plan/research/SYNTHESIS-hero-layout-archetype.md`.
- Operator locked: hero-only; deterministic routing (no LLM); `brand_mode` explicit upstream field, industry map only as stopgap; static data vendored from seo-core via env-pointed path; **`product_screenshot` never synthesized** (client capture or deterministic fallback); image-service emits decision + imagery, never HTML.
- Sliced 5 vertical slices `s17`–`s21` with SPEC.md + `slices/README.md` wave section.
- Wrote orchestrator-owned red suite under each slice's `tests/`.

### Verify
| timestamp | wave | verify | notes |
|-----------|------|--------|-------|
| 2026-06-25 | s17–s21 red | red as intended | `36 failed (AC-tagged), 2 passed (back-compat guards), 0 collection errors` via `.venv/bin/python -m pytest slices/s17-layout-archetype-data slices/s18-layout-archetype-resolver slices/s19-brand-mode-contract slices/s20-archetype-avoid-lists slices/s21-hero-imagery-branching` |

## 2026-06-25 — implementation (managed to completion)

Implemented all five slices directly in dependency order (L0→L3); each slice's suite green, then full regression.

- **s17** `data/layout_archetypes/{catalog,brand_mode_routing,industry_brand_mode}.yaml` + `app/layout/catalog.py` (loader, `LayoutCatalogError`, `PHOTO_LAYOUTS`, `clear_layout_cache`) + `app/config.py` `layout_archetype_data_path`.
- **s18** `app/layout/resolver.py` — `resolve_hero_layout_archetype()` + `HeroLayoutDecision`; import-isolated from scene/payload/provider.
- **s19** `HeroCandidatesRequest.brand_mode` field; route records `hero_layout_decision` on run metadata (corpus + live).
- **s20** trimmed `GLOBAL_HERO_AVOID` (copy-zone bans moved to `full_bleed_photo_overlay` in catalog) + `hero_avoid_for_archetype()`. Note: `GLOBAL_HERO_AVOID` had no external consumer, so no prompt-builder rewire was needed.
- **s21** `app/style/hero_abstract_prompt.py`; route branches imagery on the decision — photo path unchanged, abstract signal for non-photo, typed `hero_imagery.kind="none"` for typographic, `client_capture`-or-abstract-fallback for product_screenshot (never synthesized); poll surfaces `layout_archetype` + `imagery_type`; `product_capture_url` field added. Corrected one over-broad red test (scoped the screenshot scan to the prompt).

**Verify:** `44 passed` (wave + `tests/test_hero_candidates.py`); `95 passed` across `tests/` — no regressions. All status flipped to **green** in `slice-status.md` / `slices/README.md`.

### Open issues / for next session
- **Not committed / not merged** — changes live on the working branch awaiting Justin review.
- Abstract live-image *generation* is emitted as a prompt signal on run metadata; wiring it through `hero_worker` to actually produce + upload an abstract asset (vs. emitting the decision+prompt) is the remaining integration. Tests pin the contract (deterministic prompt, no people/slop), not a generated asset.
- Upstream (arthor-ai/seo-service): materialize the explicit `brand_mode` field on the brand packet; seo-core authors the three vendored data files (in-repo copies are the v1 default).
- Confirm `product_capture_url` field name with the builder payload owner.
- seo-core is the authoring home for `catalog.yaml` / `brand_mode_routing.yaml` / `industry_brand_mode.yaml`; s17 vendors an in-repo default copy + `LAYOUT_ARCHETYPE_DATA_PATH` env override. Upstream materialization of the explicit `brand_mode` field on the brand packet is an arthor-ai/seo-service task (out of this repo).
- `product_capture_url` (client-supplied screenshot) field shape is defined by s21; confirm the canonical name with the builder payload owner.
