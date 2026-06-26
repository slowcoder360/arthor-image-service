---
id: s19-brand-mode-contract
title: brand_mode payload field + stopgap derivation + archetype on run metadata
depends_on: [s18-layout-archetype-resolver]
parallel_safe: true
estimated_loc: 180
---

# s19-brand-mode-contract — Materialize `brand_mode` + persist the decision

## Summary

Make `brand_mode` a first-class, explicit field on the hero request, materialized upstream by the builder/packet. Image-service **reads** it and only falls back to the s17 `industry_brand_mode` map as a v1 stopgap when the field is absent — there is no private industry→mode derivation living in image-service. This slice also persists the resolved `HeroLayoutDecision` onto the run metadata so arthor-ai (and the inspector) can read the chosen archetype + imagery contract. It wires the resolver into the request path only enough to record the decision; the **imagery branching itself is s21**.

## Acceptance criteria

- AC-1: `HeroCandidatesRequest` (`app/payload/hero_models.py`) gains an optional explicit field `brand_mode: str | None = None` (extra still `forbid`; field is additive and backward-compatible — existing corpus payloads without it still validate).
- AC-2: A single call site computes the decision via `resolve_hero_layout_archetype(brand_mode=hero_req.brand_mode, industry=hero_req.business.industry)`. The industry stopgap is reached **only** when `brand_mode is None` — assert no other module re-derives brand_mode.
- AC-3: In `app/routes/hero_candidates.py` `generate_hero_candidates`, the resolved decision is added to `metadata_patch` under `hero_layout_decision` (serialized `HeroLayoutDecision`: archetype, imagery_type, scene_catalog_eligible, brand_mode, brand_mode_source, imagery_fallbacks, decision_version). Additive to the existing patch dict; no existing keys changed.
- AC-4: The decision is recorded for **both** corpus and live modes (it is orthogonal to `generation_mode`). No behavior change to corpus fulfillment in this slice.
- AC-5: `brand_mode_source` is faithfully recorded (`explicit` when the field was sent, `industry_stopgap` when derived, `default` when neither available).
- AC-6: No change to provider prompts, no change to imagery selection, no new provider calls in this slice — purely contract + metadata.

## Paths in scope

- `app/payload/hero_models.py` (additive `brand_mode` field only)
- `app/routes/hero_candidates.py` (additive: compute decision + add `hero_layout_decision` to `metadata_patch`)

## Paths out of scope (do not touch)

- `app/layout/**` (s17/s18 — read-only here)
- `app/style/**` (no prompt/avoid/scene changes here — that's s20/s21)
- `app/orchestration/**`, `app/providers/**`, `app/storage/**`, `app/inspector/**`
- `app/main.py`, `app/config.py`
- `db/**`, `slices/**` (except own `tests/`), `plan/**`, `packet/**`

## Failing tests the subagent must turn green

- `test_brand_mode_field_optional.py` — a payload without `brand_mode` still validates; one with `brand_mode="agency"` validates and round-trips.
- `test_decision_explicit_source.py` — request with explicit `brand_mode` → `metadata_patch["hero_layout_decision"]["brand_mode_source"] == "explicit"`.
- `test_decision_stopgap_source.py` — request without `brand_mode` but with a tech industry → `brand_mode_source == "industry_stopgap"`.
- `test_decision_recorded_corpus_and_live.py` — `hero_layout_decision` present in metadata for both `generation_mode="corpus"` and `"live"`.
- `test_no_private_brand_mode_derivation.py` — grep/AST: `app/routes/hero_candidates.py` does not contain its own industry→mode mapping; it calls `resolve_hero_layout_archetype` only.
- `test_metadata_patch_additive.py` — existing metadata keys (`style_profile`, `hero_visual_strategy`, `generation_mode`, …) remain unchanged when `hero_layout_decision` is added.

## Hints

- Keep the route edit surgical: compute the decision near where `visual_strategy` is resolved (~line 146) and add one key to `metadata_patch` (~line 159). Do not refactor the surrounding flow.
- `brand_mode` is materialized upstream; image-service must not infer it from anything except the explicit field or the vendored stopgap map. This is the line that prevents the decision forking when it migrates to the planning brain.
- Serialization helper for `HeroLayoutDecision` can live next to the dataclass in `app/layout/resolver.py` if needed — but if so, that belongs to s18; here just call `.to_dict()`/`dataclasses.asdict`.

## Done signal

Subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s19-brand-mode-contract/tests` is green, no out-of-scope path modified, no test file modified.
