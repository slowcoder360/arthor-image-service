---
id: s18-layout-archetype-resolver
title: Thin standalone deterministic hero layout-archetype resolver
depends_on: [s17-layout-archetype-data]
parallel_safe: true
estimated_loc: 220
---

# s18-layout-archetype-resolver — `brand_mode → archetype` (lift-and-shift ready)

## Summary

A **thin, standalone, deterministic** resolver: given a `brand_mode` (and an optional industry string for the stopgap path), return the chosen `hero_layout_archetype` and its `imagery_type`. No LLM. It reads only the s17 static catalog/routing/map and is **fully decoupled from scene resolution** (`hero_visual_strategy.py`) so it lifts-and-shifts unchanged into the planning brain's `design_plan` module later (sibling to slot_copy + asset_pack_plan).

This slice is pure decision logic + a typed result object. It does NOT touch the payload, the route, prompts, or imagery generation — those are s19/s20/s21.

## Acceptance criteria

- AC-1: `app/layout/resolver.py` exposes `resolve_hero_layout_archetype(*, brand_mode: str | None, industry: str | None = None) -> HeroLayoutDecision`.
- AC-2: `HeroLayoutDecision` is a frozen dataclass: `archetype: str`, `imagery_type: str`, `scene_catalog_eligible: bool`, `brand_mode: str`, `brand_mode_source: Literal["explicit", "industry_stopgap", "default"]`, `decision_version: str`.
- AC-3: Resolution order is deterministic: (a) if `brand_mode` is provided → route via `brand_mode_routing`; (b) elif `industry` provided → derive `brand_mode` via the s17 `industry_brand_mode` map (`brand_mode_source="industry_stopgap"`), then route; (c) else → a documented safe default archetype (`split_copy_image`) with `brand_mode_source="default"`.
- AC-4: The resolver applies the routing `fallback` chain when the primary archetype is unavailable/disabled, honoring the **never-synthesize-a-screenshot** rule: `product_screenshot` resolves to its archetype id (the *decision*), but `imagery_type` is `product_ui` and the fallback chain (`abstract_gradient_3d → centered_copy_cta`) is exposed on the decision as `imagery_fallbacks: tuple[str, ...]` for s21 to use when no client capture exists.
- AC-5: Same inputs → same `HeroLayoutDecision` (deterministic; snapshot test). No randomness, no time, no I/O beyond the cached s17 loaders.
- AC-6: Import isolation: `app/layout/resolver.py` must NOT import `app.style.hero_visual_strategy`, `app.style.hero_archetypes`, `app.payload.hero_models`, `app.routes.*`, or `app.providers.*`. It may import only `app.layout.catalog` and stdlib/pydantic. (Enforced by test.)
- AC-7: Unknown `brand_mode` (not in routing table) falls back to the documented default archetype with `brand_mode_source="default"` — never raises.

## Paths in scope

- `app/layout/resolver.py`

## Paths out of scope (do not touch)

- `app/layout/catalog.py`, `data/layout_archetypes/**` (s17 — read-only here)
- `app/style/**` (scene resolution stays decoupled)
- `app/payload/**`, `app/routes/**`, `app/orchestration/**`, `app/providers/**`, `app/storage/**`, `app/inspector/**`
- `app/main.py`, `app/config.py`, `app/runtime.py`
- `db/**`, `slices/**` (except own `tests/`), `plan/**`, `packet/**`

## Failing tests the subagent must turn green

- `test_explicit_brand_mode_routes.py` — `brand_mode="ai_platform"` → `centered_copy_cta`; `brand_mode_source="explicit"`.
- `test_industry_stopgap.py` — no `brand_mode`, `industry="AI marketing agency"` → derives a tech/agency mode; `brand_mode_source="industry_stopgap"`.
- `test_default_when_no_signal.py` — neither provided → `split_copy_image`, `brand_mode_source="default"`.
- `test_product_screenshot_fallbacks.py` — `brand_mode="tech_saas"` → archetype `product_screenshot`, `imagery_type="product_ui"`, `imagery_fallbacks == ("abstract_gradient_3d", "centered_copy_cta")`.
- `test_unknown_brand_mode_safe_default.py` — unknown mode → default archetype, no raise.
- `test_resolver_deterministic.py` — repeated calls return equal decisions.
- `test_resolver_import_isolation.py` — resolver imports neither scene nor payload nor provider modules.

## Hints

- This module is the centerpiece of the "build it to move" instruction — keep it import-light and free of FastAPI/DB/provider coupling so the planning brain can vendor it as-is.
- `imagery_type` and `imagery_fallbacks` are the contract s21 acts on; the resolver decides, it never generates.
- Cross-check the routing/fallback values against `data/layout_archetypes/brand_mode_routing.yaml` (s17) — do not duplicate the table in code.

## Done signal

Subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s18-layout-archetype-resolver/tests` is green, no out-of-scope path modified, no test file modified.
