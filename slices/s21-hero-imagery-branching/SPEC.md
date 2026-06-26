---
id: s21-hero-imagery-branching
title: Hero imagery branching — photo / abstract / typed no-image, archetype-driven
depends_on: [s18-layout-archetype-resolver, s19-brand-mode-contract, s20-archetype-avoid-lists]
parallel_safe: false
estimated_loc: 380
---

# s21-hero-imagery-branching — Resolver drives what imagery the hero gets

## Summary

The integration slice. The resolved `hero_layout_decision` now **branches imagery generation** inside the hero-candidates flow:

- **photo-eligible** archetypes (`split_copy_image`, `full_bleed_photo_overlay`) → existing scene/photo pipeline, unchanged.
- **`abstract_gradient_3d`** (and `centered_copy_cta` when it opts into abstract) → a **new generated-imagery prompt branch** using the existing providers — no people, restrained palette, no text. This is the only net-new generation path.
- **`typographic_no_image`** → emit a typed **"no hero image"** result (a structured signal in the response/metadata) so arthor-ai composes a type-only hero. No provider call.
- **`product_screenshot`** → **never generated.** Use a client-supplied capture if present on the request; when absent, fall back deterministically along `decision.imagery_fallbacks` (`abstract_gradient_3d → centered_copy_cta`). A synthetic screenshot is never produced.

Image-service still emits **only the decision + imagery (or the typed no-image signal)** — never HTML. arthor-ai composes the layout from the archetype.

## Acceptance criteria

- AC-1: Branch selection is driven solely by `hero_layout_decision` from s19 — no second resolution, no industry re-derivation.
- AC-2: Photo-eligible archetypes preserve current behavior exactly (corpus + live paths): same scene selection, same prompts except the archetype-aware avoid-list from s20. Regression guard: existing hero tests stay green.
- AC-3: `abstract_gradient_3d` builds a new deterministic provider prompt from a dedicated template (new function in `app/style/`), seeded from `base_seed + variant_index`, carrying the abstract avoid-list (no people, no indigo/purple gradient). Generated via the existing provider routing (`hero_default_provider`). `imagery_type="generative_abstract"` recorded per asset.
- AC-4: `typographic_no_image` produces **no provider call**; the response/metadata carries a typed `hero_imagery: {"kind": "none", "reason": "typographic_no_image"}` (or equivalent documented shape) and the run completes `ok`.
- AC-5: `product_screenshot`: if the request carries a client capture reference → record it as the hero asset (no generation); else apply `decision.imagery_fallbacks` in order and generate the first available branch (`abstract_gradient_3d`). A test asserts **no synthetic-screenshot prompt is ever constructed**.
- AC-6: Every emitted asset records `layout_archetype` + `imagery_type` in its metadata; the poll response surfaces `layout_archetype` alongside the existing fields.
- AC-7: Backward compatibility: a request that resolves to `split_copy_image` via the default path behaves identically to today for the existing corpus verticals (dental etc.) — no change to served corpus URLs.

## Paths in scope

- `app/routes/hero_candidates.py` (branch on `hero_layout_decision`; surface `layout_archetype` in poll response)
- `app/style/` — new abstract prompt template module/function (e.g. `app/style/hero_abstract_prompt.py`)
- `app/orchestration/hero_worker.py` (route the abstract branch through the existing background generation; additive)
- `app/payload/hero_models.py` — only if a typed `hero_imagery`/client-capture field is needed (additive, optional)

## Paths out of scope (do not touch)

- `app/layout/**` (read-only)
- `app/style/hero_visual_strategy.py` scene catalog internals (selection unchanged), `app/style/hero_taste_corpus.py` corpus loader
- `app/providers/**` (reuse existing providers; no new provider)
- `app/config.py`, `app/main.py`, `app/storage/**`, `app/inspector/**`
- `db/**`, `slices/**` (except own `tests/`), `plan/**`, `packet/**`

## Failing tests the subagent must turn green

- `test_photo_eligible_unchanged.py` — `split_copy_image` / `full_bleed_photo_overlay` follow the existing scene pipeline; corpus served URLs unchanged for `dental`.
- `test_abstract_branch_prompt.py` — `abstract_gradient_3d` builds a deterministic abstract prompt with no people and no purple-gradient language; seeded reproducibly.
- `test_typographic_no_image.py` — `typographic_no_image` makes **zero** provider calls and emits `hero_imagery.kind == "none"`; run status `ok`.
- `test_product_screenshot_never_generates_ui.py` — no client capture → falls back to `abstract_gradient_3d`; asserts no screenshot-style prompt was constructed.
- `test_product_screenshot_uses_client_capture.py` — client capture present → recorded as hero asset, no generation.
- `test_asset_metadata_has_archetype.py` — each emitted asset metadata has `layout_archetype` + `imagery_type`; poll response surfaces `layout_archetype`.
- `test_no_html_emitted.py` — response contains imagery/URLs or the typed no-image signal only; never HTML/markup.

## Hints

- This slice integrates s18–s20; sequence it last. `parallel_safe: false` because it edits `app/routes/hero_candidates.py` + `app/orchestration/hero_worker.py`.
- Keep the abstract prompt template small and deterministic, mirroring `variant_subject_primary` style; pull its avoid-list from `hero_avoid_for_archetype("abstract_gradient_3d")` (s20).
- The "never synthesize a screenshot" rule (the operator's trust-over-flex call) is the load-bearing constraint of AC-5 — test it explicitly.
- Do not introduce HTML/section composition here — emit decision + imagery only; arthor-ai owns layout.

## Done signal

Subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s21-hero-imagery-branching/tests` is green, the existing hero suites remain green, no out-of-scope path modified, no test file modified.
