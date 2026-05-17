---
id: s15-cost-rollup-views
title: /inspector/cost — per-run, per-day, per-site, per-provider, per-slot-type rollups with date/site/provider filters
depends_on: [s05-agent-runs-writer, s13-inspector-shell]
parallel_safe: false
estimated_loc: 350
---

# s15-cost-rollup-views — Cost rollup views (`/inspector/cost`)

## Summary

The cost-visibility surface. `/inspector/cost` renders five rollups: per-run (recent), per-day (last 30), per-site (top 25 sites by spend), per-provider (the two v1 providers), per-slot-type (hero / section_accent / card / og / portrait / background). Filters: date range, site_id, provider. Queries roll up `tool_calls.cost_cents` joined to `agent_runs` (for run_type and metadata.site_id) and to `external_media_assets` (for slot-type derivation via `metadata.slot_id` — slot kind comes from `image_request_payloads.payload.slots[].slot_kind`).

## Acceptance criteria

- AC-1: `app/inspector/cost.py` exports five async query functions: `cost_per_run(pool, *, limit=25, date_from, date_to, site_id, provider) -> list[CostRow]`, `cost_per_day(pool, *, days=30, site_id, provider) -> list[DailyCostRow]`, `cost_per_site(pool, *, limit=25, date_from, date_to, provider) -> list[SiteCostRow]`, `cost_per_provider(pool, *, date_from, date_to, site_id) -> list[ProviderCostRow]`, `cost_per_slot_type(pool, *, date_from, date_to, site_id, provider) -> list[SlotTypeCostRow]`. Each returns a small `@dataclass` row type.
- AC-2: `GET /inspector/cost` (added to `app/inspector/router.py`) renders `templates/cost.html` with all five rollups for the default window (last 30 days, no site filter, all providers). Auth + cache-control inherited from s13.
- AC-3: `GET /inspector/cost?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&site_id=<uuid>&provider=<name>` applies the filters across all five rollups. Empty filters mean "no filter."
- AC-4: `app/inspector/templates/cost.html` extends s13's `base.html`, renders five tables with sticky headers. All `cost_cents` columns display as dollars with 2 decimals (`$0.42`). Pagination is not needed in v1 (each rollup is capped at 25-30 rows).
- AC-5: Per-slot-type rollup derives `slot_kind` by joining `external_media_assets.metadata.slot_id` to `image_request_payloads.payload->'slots'` and pulling the slot's `slot_kind`. SQL uses `jsonb_path_query` or unnests `payload->'slots'` per row.
- AC-6: Queries use the indexes from s02 (`idx_tool_calls_provider`, `idx_ema_agent_run`, etc.). Document the query plan rationale in code comments for any rollup that requires a non-trivial join.

## Paths in scope

- `app/inspector/cost.py`
- `app/inspector/templates/cost.html`
- `app/inspector/router.py` (additive — add the `/cost` route only; do not rewrite s13/s14 routes)

## Paths out of scope (do not touch)

- `app/inspector/__init__.py`, `app/inspector/csrf.py`, `app/inspector/queries.py`, `app/inspector/templates/base.html`, `app/inspector/templates/login.html`, `app/inspector/templates/run_list.html`, `app/inspector/templates/run_detail.html`, `app/inspector/templates/slot_prompt_modifier.html`, `app/inspector/templates/variants_grid.html`, `app/inspector/templates/pack_consistency_grid.html`, `app/inspector/templates/soft_delete_form.html`, `app/inspector/static/**` (s13/s14 own)
- `app/auth/**`, `app/payload/**`, `app/runs/**`, `app/style/**`, `app/storage/**`, `app/providers/**`, `app/routes/**`, `app/orchestration/**`, `app/quality/**`, `app/callback/**`, `app/jobs/**`
- `app/main.py`, `app/config.py`, `app/runtime.py`
- `db/**`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s15-cost-rollup-views/tests/test_cost_per_run_query.py` — `requires_db` — three runs with known costs → rollup returns them sorted by `started_at DESC` with correct totals.
- `slices/s15-cost-rollup-views/tests/test_cost_per_day_query.py` — `requires_db` — runs across 5 days → `cost_per_day(days=30)` returns 5 rows in chronological order with daily sums.
- `slices/s15-cost-rollup-views/tests/test_cost_per_site_query.py` — `requires_db` — runs across 3 sites → top-25 sorted by total descending.
- `slices/s15-cost-rollup-views/tests/test_cost_per_provider_query.py` — `requires_db` — `openai_image` + `google_nano_banana` totals match SUM(tool_calls.cost_cents WHERE provider=$1).
- `slices/s15-cost-rollup-views/tests/test_cost_per_slot_type_query.py` — `requires_db` — slot-kind derivation via payload join works; rollup correct.
- `slices/s15-cost-rollup-views/tests/test_cost_route_renders.py` — `requires_db` — GET /inspector/cost (authed) → 200 + HTML containing all five rollup table headers.
- `slices/s15-cost-rollup-views/tests/test_cost_route_filters.py` — `requires_db` — `?date_from=...&site_id=...&provider=...` constrains all five rollups.
- `slices/s15-cost-rollup-views/tests/test_cost_dollar_formatting.py` — 4200 cents renders as `$42.00`.

## Hints

- ADR anchors: [plan/adr/0004-agent-runs-and-tool-calls.md](plan/adr/0004-agent-runs-and-tool-calls.md) (cost rollup query shape), [plan/CONTEXT.md](plan/CONTEXT.md) §"Schema vocabulary".
- The nav link to `/inspector/cost` exists from s13's base.html. s13 deferred the route; this slice fills it.
- Per-slot-type rollup is the gnarliest query — write the slot-kind join carefully and test against a fixture with multiple slot kinds. Add a code-comment explaining the EXPLAIN plan rationale.
- Filters default to "no filter" — render the form with the current filter values pre-populated so Justin can iterate.
- `parallel_safe: false` because this slice extends `app/inspector/router.py` (which s13 and s14 also edit). Sequences after s14.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s15-cost-rollup-views/tests` is fully green (DB-required tests skipped if no DATABASE_URL), no files under `paths_out_of_scope` were modified, and no test files under `slices/s15-cost-rollup-views/tests/` were modified.
