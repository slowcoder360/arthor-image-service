# Next orchestrator brief — canonical start-here

Last run: `agent-control/orchestration-runs/2026-06-25-layout-archetype-wave.md`. Phase: hero layout-archetype wave (s17–s21) **implemented + green** (44 wave/regression, 95 full `tests/`). **Not committed / not merged** — awaiting Justin review. Next: review → commit → (optional) wire abstract live-generation through `hero_worker`.

## Read first (in order)
1. This file
2. `agent-control/slice-status.md` — hero layout-archetype wave section (status)
3. `plan/research/SYNTHESIS-hero-layout-archetype.md` — the proposal + locked decisions
4. `slices/README.md` — "Wave LB-layout" section (deps + dispatch order)
5. The `slices/s17..s21/SPEC.md` for whichever slice you're dispatching
6. `plan/CONTEXT.md` — shared vocabulary (deterministic vs inference, StyleProfile)

## This run does only
- Dispatch the layout-archetype builders in dependency order: **L0 `s17` → L1 `s18` → L2 `s19`+`s20` (parallel) → L3 `s21`**.
- Each builder turns its own `slices/<id>/tests` green without touching `paths_out_of_scope` or any `tests/` file.
- Re-run each slice's verifier independently after the builder returns; flip status in `slice-status.md`.

## Done means
- `.venv/bin/python -m pytest slices/s17-layout-archetype-data slices/s18-layout-archetype-resolver slices/s19-brand-mode-contract slices/s20-archetype-avoid-lists slices/s21-hero-imagery-branching` fully green (was: 36 failed / 2 passed / 0 errors).
- Existing hero suites stay green: `.venv/bin/python -m pytest tests/test_hero_candidates.py`.

## Do not
- Do not write HTML / section composition in image-service — emit decision + imagery (or typed `hero_imagery.kind="none"`) only; arthor-ai owns layout.
- Do not let the resolver import scene/payload/provider modules (s18 lift-and-shift constraint).
- Do not synthesize a product screenshot — client capture or deterministic fallback only.
- Do not add a private industry→brand_mode map in image-service — it lives in the vendored data + resolver.
- Do not expand scope to full-page sections; this wave is hero-only.

## Operator queue
- Confirm `product_capture_url` (client-supplied screenshot) field name with the builder payload owner.
- Upstream: materialize the explicit `brand_mode` field on the brand packet (arthor-ai/seo-service); seo-core authors the three static data files that s17 vendors.

## Driver
Next session should drive the registry via `orchestrate-build` (or `dispatch-builder` per slice).
