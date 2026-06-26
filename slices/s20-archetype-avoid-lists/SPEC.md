---
id: s20-archetype-avoid-lists
title: Per-archetype avoid-lists replacing the global GLOBAL_HERO_AVOID
depends_on: [s17-layout-archetype-data, s18-layout-archetype-resolver]
parallel_safe: true
estimated_loc: 160
---

# s20-archetype-avoid-lists — Split GLOBAL_HERO_AVOID by archetype

## Summary

Today `GLOBAL_HERO_AVOID` in `app/style/hero_archetypes.py` is a single flat tuple applied to every hero. Some items are genuinely global ("rendered words or signage text"), but others are **archetype-specific and actively wrong for other archetypes** — most notably `"blank left half or empty void reserved for copy"`, which is *required geometry* for `split_copy_image`. This slice splits the list: truly-global avoids stay in code; archetype-specific avoids are sourced from the s17 catalog `avoid` field; and the prompt compiler merges `global + archetype` avoids based on the resolved archetype.

## Acceptance criteria

- AC-1: `GLOBAL_HERO_AVOID` is reduced to only the items that apply to **every** archetype (e.g. `stock smile staring at camera`, `field-service provider facing camera when no team likeness refs`, `website mockups`, `rendered words or signage text`). The two copy-zone items (`blank left half or empty void reserved for copy`, `sterile copy-zone wall with no scene continuity`) are **removed** from the global tuple.
- AC-2: The removed copy-zone items now live under `full_bleed_photo_overlay.avoid` in `data/layout_archetypes/catalog.yaml` (authored in s17; this slice verifies/consumes them). `split_copy_image.avoid` must NOT contain a "blank left half" ban (its copy column is intended geometry).
- AC-3: A new helper `hero_avoid_for_archetype(archetype: str) -> tuple[str, ...]` returns `GLOBAL_HERO_AVOID + catalog_avoid(archetype)`, deterministic and de-duplicated, order-stable (global first).
- AC-4: The hero prompt builder uses `hero_avoid_for_archetype(decision.archetype)` instead of the bare `GLOBAL_HERO_AVOID` when an archetype decision is available; when no decision is present (legacy path), it falls back to `GLOBAL_HERO_AVOID` unchanged so existing corpus/live behavior is preserved.
- AC-5: `abstract_gradient_3d.avoid` and `typographic_no_image.avoid` include the anti-slop image bans from POD-C: no people / human subjects, no rainbow or indigo-purple gradient.
- AC-6: No change to scene archetype selection or `INDUSTRY_VISUAL_TRIAD`; this slice only touches the avoid-list assembly.

## Paths in scope

- `app/style/hero_archetypes.py` (reduce `GLOBAL_HERO_AVOID`; add `hero_avoid_for_archetype`)
- the hero prompt-builder call site that currently consumes `GLOBAL_HERO_AVOID` (identify via grep; likely `app/style/prompts.py` or the compiler) — additive switch to the archetype-aware helper with a legacy fallback
- `data/layout_archetypes/catalog.yaml` — only if the s17 `avoid` values need finalizing per AC-2/AC-5 (additive)

## Paths out of scope (do not touch)

- `app/layout/resolver.py`, `app/layout/catalog.py` (read-only)
- `app/payload/**`, `app/routes/**`, `app/orchestration/**`, `app/providers/**`, `app/storage/**`, `app/inspector/**`
- `app/style/hero_visual_strategy.py` (scene catalog — untouched), `app/style/hero_taste_corpus.py`
- `app/main.py`, `app/config.py`
- `db/**`, `slices/**` (except own `tests/`), `plan/**`, `packet/**`

## Failing tests the subagent must turn green

- `test_global_avoid_trimmed.py` — `GLOBAL_HERO_AVOID` no longer contains the "blank left half" / "copy-zone wall" items.
- `test_full_bleed_keeps_copy_zone_ban.py` — `hero_avoid_for_archetype("full_bleed_photo_overlay")` contains the blank-left-half ban.
- `test_split_allows_copy_column.py` — `hero_avoid_for_archetype("split_copy_image")` does NOT contain any blank-left-half ban.
- `test_abstract_bans_people_and_purple.py` — abstract/typographic avoid-lists include "no people" + "no indigo/purple gradient".
- `test_avoid_dedup_order.py` — global items appear first, no duplicates.
- `test_legacy_fallback_unchanged.py` — when no archetype decision is supplied, the builder still uses the trimmed `GLOBAL_HERO_AVOID` (no crash, deterministic).

## Hints

- First `grep` for `GLOBAL_HERO_AVOID` to find every consumer; the only behavioral switch is at the prompt-builder call site. Keep the legacy fallback so this slice does not depend on s21 being merged.
- This slice and s19 are disjoint (different files) and can run in parallel.
- Keep the avoid copy text identical to today's strings when moving them, so prompt hashes change only where intended.

## Done signal

Subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s20-archetype-avoid-lists/tests` is green, no out-of-scope path modified, no test file modified.
