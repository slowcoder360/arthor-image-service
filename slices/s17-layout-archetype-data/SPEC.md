---
id: s17-layout-archetype-data
title: Vendored hero layout-archetype static data + env-pointed loader
depends_on: []
parallel_safe: true
estimated_loc: 300
---

# s17-layout-archetype-data — Static catalog + routing, vendored from seo-core

## Summary

Land the **static data** that the layout-archetype layer resolves against, plus a thin deterministic loader. Three vendored files describe (1) the hero layout-archetype catalog, (2) the `brand_mode → archetype` routing table with deterministic fallbacks, and (3) the `industry → brand_mode` map used only as a v1 stopgap when an explicit `brand_mode` field is absent. These files are the **single source shared with seo-service**: they are authored in seo-core and vendored here, the same way image-section-templates are vendored — an env var points at the on-disk location, defaulting to the in-repo copy under `data/layout_archetypes/`.

This slice ships **data + loader only**. No resolution logic, no payload changes, no prompt changes. The loader mirrors the existing `hero_taste_corpus` loader style (lru-cached, deterministic, no LLM).

## Acceptance criteria

- AC-1: Vendored data under `data/layout_archetypes/`:
  - `catalog.yaml` — `catalog_version` + one entry per archetype id: `split_copy_image`, `full_bleed_photo_overlay`, `centered_copy_cta`, `abstract_gradient_3d`, `typographic_no_image`, `product_screenshot`. Each entry carries: `imagery_type` (`real_photo` | `product_ui` | `generative_abstract` | `abstract_or_none` | `none`), `scene_catalog_eligible` (bool), `avoid` (list[str] — per-archetype avoid items consumed later by s20), and a one-line `structure` note.
  - `brand_mode_routing.yaml` — `brand_mode → default archetype` plus an ordered `fallback` list per archetype (e.g. `product_screenshot: [abstract_gradient_3d, centered_copy_cta]`) honoring the "never synthesize a screenshot" rule.
  - `industry_brand_mode.yaml` — `industry/slug substring → brand_mode` (the v1 stopgap map).
- AC-2: `app/config.py` gains one additive setting `layout_archetype_data_path: str | None = None`. When unset, the loader uses the in-repo `data/layout_archetypes/`. When set, it points at the vendored seo-core copy (file-or-dir).
- AC-3: `app/layout/catalog.py` exposes deterministic loaders: `load_layout_catalog()`, `load_brand_mode_routing()`, `load_industry_brand_mode_map()`, each `@lru_cache`d and returning frozen dataclasses/tuples (no mutable module state). A `clear_layout_cache()` mirrors `clear_corpus_cache()`.
- AC-4: Loaders are pure data access — they do NOT import scene resolution, payload models, providers, or prompt code. (Enforced by an import-isolation test.)
- AC-5: Catalog parse is strict: unknown `imagery_type`, missing `imagery_type`, or an archetype id not in the known set → the loader raises a typed `LayoutCatalogError` at load time (fail fast on bad vendored data).
- AC-6: `archetype_ids()` returns the catalog ids sorted; `PHOTO_LAYOUTS` is derived from `scene_catalog_eligible: true` entries, not hardcoded.

## Paths in scope

- `data/layout_archetypes/catalog.yaml`
- `data/layout_archetypes/brand_mode_routing.yaml`
- `data/layout_archetypes/industry_brand_mode.yaml`
- `app/layout/__init__.py`
- `app/layout/catalog.py`
- `app/config.py` (additive — one new setting only)

## Paths out of scope (do not touch)

- `app/layout/resolver.py` (s18)
- `app/payload/**`, `app/routes/**`, `app/style/**`, `app/orchestration/**`, `app/providers/**`, `app/storage/**`, `app/inspector/**`, `app/jobs/**`
- `app/main.py`, `app/runtime.py`
- `data/hero_taste_corpus/**`
- `db/**`
- `slices/**` (except this slice's own `tests/`), `plan/**`, `packet/**`

## Failing tests the subagent must turn green

- `test_catalog_loads_all_archetypes.py` — all 6 ids load; each has a valid `imagery_type`.
- `test_photo_layouts_derived.py` — `PHOTO_LAYOUTS == {split_copy_image, full_bleed_photo_overlay}` derived from `scene_catalog_eligible`.
- `test_routing_fallbacks.py` — `product_screenshot` routing fallback never contains `product_screenshot` and starts with `abstract_gradient_3d`.
- `test_env_path_override.py` — setting `layout_archetype_data_path` at a temp dir loads that copy instead of the in-repo default.
- `test_bad_catalog_raises.py` — a catalog with an unknown `imagery_type` raises `LayoutCatalogError`.
- `test_loader_import_isolation.py` — `app.layout.catalog` does not import `app.style.hero_visual_strategy`, `app.payload`, or `app.providers` (AST/import scan).

## Hints

- Mirror `app/style/hero_taste_corpus.py` for loader style: `Path(__file__).resolve().parents[N]`, `@lru_cache`, frozen dataclasses, `clear_*_cache()`.
- The `avoid` field in `catalog.yaml` is authored here but **consumed in s20**; this slice only stores/validates it.
- Keep the data shape close to the `LAYOUT_CATALOG` block proposed in `plan/research/SYNTHESIS-hero-layout-archetype.md` §1 and the routing table in §2.
- Do NOT hardcode `brand_mode` derivation logic — that's the stopgap consumer in s19. This slice only ships the `industry_brand_mode.yaml` data + its loader.

## Done signal

Subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s17-layout-archetype-data/tests` is green, no out-of-scope path was modified, and no test file under this slice was modified.
