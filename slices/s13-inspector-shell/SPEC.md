---
id: s13-inspector-shell
title: Jinja2 + HTMX inspector shell — /inspector/login, /inspector/runs list, /inspector/runs/{id} detail
depends_on: [s05-agent-runs-writer, s07-r2-uploader]
parallel_safe: false
estimated_loc: 800
---

# s13-inspector-shell — Inspector GUI shell (auth + list + detail)

## Summary

The first concrete inspector in the arthor ecosystem (per ADR-0006 §"For browser convenience"). FastAPI + Jinja2 + HTMX, no JS framework. Mounted on `/inspector/*` behind `require_inspector_token`. v1 ships three read views: `/inspector/login` (POST sets the cookie per ADR-0006), `/inspector/runs` (paginated list with run_type filter), `/inspector/runs/{id}` (full run detail — payload, resolved style profile, per-slot prompts, every asset variant, every tool_call cost, per-slot palette-drift flag). The iteration controls (prompt-modifier, fork-rerun, side-by-side variants, pack-consistency grid, soft-delete) live in s14 which extends this slice's templates and router.

## Acceptance criteria

- AC-1: `app/inspector/router.py` exposes an `APIRouter` mounted on `/inspector` with the `require_inspector_token` middleware applied to all routes EXCEPT `/inspector/login`. `app/main.py` lifespan additively mounts the router with `app.include_router(inspector_router, prefix="/inspector")`.
- AC-2: `GET /inspector/login` returns the login HTML form (token entry). `POST /inspector/login` accepts a form-encoded `token` field, validates against `settings.inspector_admin_token` (constant-time), on success calls `issue_inspector_cookie` (s03) and redirects to `/inspector/runs`; on failure renders the same form with a 401 error message.
- AC-3: `POST /inspector/login` AND every other inspector POST require CSRF protection: a double-submit cookie pattern (`arthor_csrf_token` cookie + hidden form field `csrf_token`). `app/inspector/csrf.py` exports `def issue_csrf_token(response) -> str` and `def verify_csrf_token(request) -> None` (raises 403 on mismatch). SameSite=Strict on both cookies.
- AC-4: `GET /inspector/runs?page=1&run_type=<filter>` returns paginated HTML list (25 per page) of agent_runs (image_* run_types only), sorted `started_at DESC`. Filter param `run_type` is optional, allow-list against the three known values. Pagination links use `?page=N`.
- AC-5: `GET /inspector/runs/{id}` returns the run detail view: agent_runs row metadata (status, cost_cents, started_at, finished_at), the resolved StyleProfile (from `agent_runs.metadata.style_profile`), the original payload (from `image_request_payloads`), every `external_media_assets` row for this run (grouped by `metadata.slot_id`, showing all variants in created_at order), every `tool_calls` row (provider, model_version, cost_cents, latency_ms, status). Renders palette-drift badge on assets with `metadata.palette_drift = true`. Renders provider-response shape (trimmed).
- AC-6: `app/inspector/templates/base.html` defines the layout: nav bar with link to `/inspector/runs` + `/inspector/cost` (s15 fills the cost route), `<meta name="htmx-config" content="...">`, includes `static/htmx.min.js` + `static/inspector.css`. Renders the CSRF token in a hidden meta tag for HTMX `hx-headers`.
- AC-7: `app/inspector/templates/run_list.html` extends `base.html`, renders the table + pagination + filter form. Uses HTMX `hx-get` for pagination links (server-rendered partial responses; falls back to full-page links if JS disabled).
- AC-8: `app/inspector/templates/run_detail.html` extends `base.html`, renders the documented run-detail layout. v1 layout is plain HTML; s14 introduces the per-slot iteration controls.
- AC-9: `app/inspector/static/htmx.min.js` is vendored verbatim (download from htmx.org; document version + SHA-256 in code comment for audit). `app/inspector/static/inspector.css` is a small (<200 line) hand-rolled stylesheet — dark mode default, monospace headings, generous whitespace.
- AC-10: `app/inspector/static/` is mounted via `StaticFiles(directory="app/inspector/static")` from `app/inspector/router.py`.
- AC-11: All HTML responses set `Cache-Control: no-store` (admin views should never be cached).
- AC-12: Asset thumbnails render via `r2_url` directly. If `r2_url` is unset (asset still pending/failed), render a placeholder badge.

## Paths in scope

- `app/inspector/__init__.py`
- `app/inspector/router.py`
- `app/inspector/csrf.py`
- `app/inspector/queries.py` (read-only DB queries for the list + detail views)
- `app/inspector/templates/base.html`
- `app/inspector/templates/login.html`
- `app/inspector/templates/run_list.html`
- `app/inspector/templates/run_detail.html`
- `app/inspector/static/htmx.min.js` (vendored)
- `app/inspector/static/inspector.css`
- `app/main.py` (additive — mount the inspector router + StaticFiles)

## Paths out of scope (do not touch)

- `app/inspector/cost.py` (s15 owns) — the nav link points at `/inspector/cost` but the route is added in s15
- `app/inspector/templates/cost.html`, `app/inspector/templates/slot_prompt_modifier.html`, `app/inspector/templates/variants_grid.html`, `app/inspector/templates/pack_consistency_grid.html`, `app/inspector/templates/soft_delete_form.html` (s14/s15 own)
- `app/auth/**` (s03), `app/payload/**`, `app/runs/**`, `app/storage/**`, `app/providers/**`, `app/routes/**`, `app/orchestration/**`, `app/quality/**`, `app/callback/**`, `app/jobs/**`
- `app/config.py`, `app/runtime.py`
- `db/**`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s13-inspector-shell/tests/test_inspector_requires_auth.py` — `GET /inspector/runs` without token/cookie → 401; `GET /inspector/login` → 200 (auth not required for the login page).
- `slices/s13-inspector-shell/tests/test_login_post_sets_cookie.py` — valid token → 302 redirect + Set-Cookie with the documented attributes; invalid token → 200 + error message in HTML.
- `slices/s13-inspector-shell/tests/test_csrf_protection.py` — POST without `csrf_token` form field → 403; mismatched cookie/form → 403; matched → pass.
- `slices/s13-inspector-shell/tests/test_runs_list_html.py` — `requires_db` — authenticated GET returns 200 + HTML containing a table row per run + pagination links + filter form.
- `slices/s13-inspector-shell/tests/test_runs_list_filter.py` — `requires_db` — `?run_type=image_pack_generation` filters; `?run_type=bogus` → 400.
- `slices/s13-inspector-shell/tests/test_run_detail_html.py` — `requires_db` — GET /inspector/runs/{id} returns HTML containing the payload, the StyleProfile, every asset row, every tool_call row, every cost.
- `slices/s13-inspector-shell/tests/test_run_detail_palette_drift_badge.py` — `requires_db` — when an asset has `metadata.palette_drift = true`, the badge appears in the HTML.
- `slices/s13-inspector-shell/tests/test_run_detail_404.py` — unknown run id → 404.
- `slices/s13-inspector-shell/tests/test_static_assets_mounted.py` — `GET /inspector/static/htmx.min.js` → 200; `GET /inspector/static/inspector.css` → 200.
- `slices/s13-inspector-shell/tests/test_cache_control_no_store.py` — every inspector HTML response sets `Cache-Control: no-store`.

## Hints

- ADR anchors: [plan/adr/0006-hmac-auth-convention.md](plan/adr/0006-hmac-auth-convention.md) §"For the inspector GUI" + §"Consequences" (CSRF requirement), [plan/CONTEXT.md](plan/CONTEXT.md) §"GUI vocabulary".
- arthor-agent doesn't have an inspector to mirror (per the intake notes — the seo-service inspector is unbuilt). This slice IS the reference implementation; future inspectors copy this shape. Document this in `app/inspector/__init__.py` module docstring.
- HTMX version: pin to the latest stable (e.g. `1.9.x`). Vendor the file at `app/inspector/static/htmx.min.js`. Add SHA-256 to a comment in `app/inspector/__init__.py` for audit.
- CSS: dark mode by default (background #0d0d0d, text #f0f0f0). Justin will style for taste later; the v1 bar is "readable, not pretty."
- Template engine: `from fastapi.templating import Jinja2Templates; templates = Jinja2Templates(directory="app/inspector/templates")`. Pass `request` to every template render (HTMX detection + URL building need it).
- Pagination query: `SELECT * FROM agent_runs WHERE run_type IN ('image_pack_generation','image_slot_regenerate','image_style_preview') [AND run_type=$1] ORDER BY started_at DESC LIMIT 25 OFFSET $2`. Use the index `idx_agent_runs_started_at` if it exists; if not, document a follow-up.
- Run-detail joins: `agent_runs LEFT JOIN external_media_assets ON external_media_assets.agent_run_id = agent_runs.id LEFT JOIN tool_calls ON tool_calls.run_id = agent_runs.id LEFT JOIN image_request_payloads ON image_request_payloads.agent_run_id = agent_runs.id`. Render in three sections; don't try to ORM-graph.
- `parallel_safe: false` because this slice extends `app/main.py`; sequences after s12.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s13-inspector-shell/tests` is fully green (DB-required tests skipped if no DATABASE_URL), no files under `paths_out_of_scope` were modified, and no test files under `slices/s13-inspector-shell/tests/` were modified.
