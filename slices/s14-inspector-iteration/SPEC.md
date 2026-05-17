---
id: s14-inspector-iteration
title: Inspector iteration controls — prompt-modifier text box, fork-rerun, side-by-side variants, pack-consistency grid, soft-delete/unsupersede
depends_on: [s11-endpoint-regenerate-slot, s13-inspector-shell]
parallel_safe: false
estimated_loc: 600
---

# s14-inspector-iteration — Iteration controls (prompt-modifier, fork-rerun, variants, consistency grid, unsupersede)

## Summary

The quality-iteration surface of the inspector. Extends s13's `run_detail.html` and `router.py` with the per-slot prompt-modifier text box, the fork-rerun button (calls s11's regenerate-slot endpoint), the side-by-side variants view (history of generations per slot), the pack-consistency grid (all slots from one pack at thumbnail size in one screen), and the soft-delete / unsupersede control (rolls back a regeneration when the new variant is worse). All POSTs are CSRF-protected (s13 primitive) and HMAC-signed when they call the API endpoints (the inspector signs internal-network calls with the shared secret like any other arthor-ai client).

## Acceptance criteria

- AC-1: `app/inspector/templates/run_detail.html` is extended (additive — the s13 base structure remains) with a per-slot iteration panel: prompt-modifier text input, "Fork & rerun" button, "Toggle variants" button, "Soft-delete current" button.
- AC-2: `POST /inspector/slots/{asset_id}/regenerate` (added to `app/inspector/router.py`) accepts form fields `prompt_modifier: str | None`, `new_seed: int | None`, validates CSRF, then internally calls the `POST /images/regenerate-slot` endpoint (signs the request with `sign_outbound`, posts via the inspector's `httpx` client). Returns an HTMX partial that updates the slot's panel with the new pending row.
- AC-3: `GET /inspector/slots/{slot_id}/variants?run_id=<run_id>` returns an HTMX partial: a horizontal side-by-side render of every `external_media_assets` row matching `metadata.slot_id = $1 AND agent_run_id IN (run_id, its descendants via parent_run_id)`, oldest-left to newest-right. Each variant shows the prompt_hash, seed, provider, cost.
- AC-4: `GET /inspector/runs/{id}/grid` returns the pack-consistency grid: every slot's currently-`uploaded` asset rendered at 256px thumbnail in a CSS grid (`grid-template-columns: repeat(auto-fill, minmax(256px, 1fr))`). Drives Justin's quality verdict at a glance.
- AC-5: `POST /inspector/assets/{asset_id}/unsupersede` (CSRF-protected) calls `unsupersede_asset(pool, asset_id=asset_id)` (s07). 400 if the asset is not currently `superseded`; 400 if the replacement asset is gone (cascade-deleted) — surfaces `UnsupersedeUnavailable`. Returns HTMX partial that re-renders the slot's variants panel.
- AC-6: `POST /inspector/assets/{asset_id}/soft-delete` accepts `reason: str` form field, transitions the asset to `superseded` with `metadata.soft_deleted = true, soft_delete_reason = $reason`. Distinct from "supersede via regeneration" — used when no replacement exists yet. Renders HTMX partial.
- AC-7: New templates: `slot_prompt_modifier.html`, `variants_grid.html`, `pack_consistency_grid.html`, `soft_delete_form.html`. Each is an HTMX partial (no `{% extends %}`) returned by the corresponding route.
- AC-8: The inspector's outbound HTTP client (used by AC-2) is constructed via `httpx.AsyncClient(base_url=f"http://localhost:{settings.app_port}")` and signs requests via `sign_outbound` using the same shared secret. `app_port` defaults to 8000 via a new optional setting **only if not already declared in s01**; otherwise it's pulled from the existing config. (The fact that the inspector calls its own endpoint over HTTP is a deliberate choice — it exercises the same code path arthor-ai will use; documented in code comments.)
- AC-9: All forms submit `csrf_token` from the meta tag set by s13's base template.

## Paths in scope

- `app/inspector/router.py` (additive — add the new routes; do not rewrite s13's routes)
- `app/inspector/templates/run_detail.html` (additive — extend the s13 layout; do not rewrite)
- `app/inspector/templates/slot_prompt_modifier.html`
- `app/inspector/templates/variants_grid.html`
- `app/inspector/templates/pack_consistency_grid.html`
- `app/inspector/templates/soft_delete_form.html`
- `app/inspector/queries.py` (additive — add the variant-history query and the grid query)

## Paths out of scope (do not touch)

- `app/inspector/__init__.py`, `app/inspector/csrf.py`, `app/inspector/templates/base.html`, `app/inspector/templates/login.html`, `app/inspector/templates/run_list.html`, `app/inspector/static/**` (s13 owns)
- `app/inspector/cost.py`, `app/inspector/templates/cost.html` (s15 owns)
- `app/routes/regenerate_slot.py` (s11 owns)
- `app/auth/**`, `app/payload/**`, `app/runs/**`, `app/style/**`, `app/storage/**`, `app/providers/**`, `app/orchestration/**`, `app/quality/**`, `app/callback/**`, `app/jobs/**`
- `app/main.py`, `app/config.py`, `app/runtime.py`
- `db/**`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s14-inspector-iteration/tests/test_prompt_modifier_post.py` — `requires_db` — POST with valid form + CSRF → 200 + HTMX partial; the regenerate-slot endpoint was called with the modifier text and seed.
- `slices/s14-inspector-iteration/tests/test_prompt_modifier_csrf.py` — POST without csrf_token → 403.
- `slices/s14-inspector-iteration/tests/test_variants_view.py` — `requires_db` — GET returns HTML containing every variant for a slot in order; each variant card shows prompt_hash, seed, provider, cost.
- `slices/s14-inspector-iteration/tests/test_pack_consistency_grid.py` — `requires_db` — GET returns HTML with a `style="grid-template-columns: repeat(auto-fill, minmax(256px, 1fr))"` container holding all uploaded slot thumbnails.
- `slices/s14-inspector-iteration/tests/test_unsupersede_happy.py` — `requires_db` — POST unsupersedes a superseded asset; the variants panel re-renders to show the old asset as active again.
- `slices/s14-inspector-iteration/tests/test_unsupersede_not_superseded.py` — `requires_db` — POST against an `uploaded` asset → 400.
- `slices/s14-inspector-iteration/tests/test_soft_delete_with_reason.py` — `requires_db` — POST sets `metadata.soft_deleted = true, soft_delete_reason = "reason"`.
- `slices/s14-inspector-iteration/tests/test_soft_delete_requires_reason.py` — missing `reason` form field → 400.
- `slices/s14-inspector-iteration/tests/test_signed_outbound_to_regenerate.py` — internal call to `/images/regenerate-slot` carries a valid `X-Arthor-Signature` (round-trip verified via `verify_signature`).

## Hints

- ADR anchors: [plan/adr/0006-hmac-auth-convention.md](plan/adr/0006-hmac-auth-convention.md) (inspector calls API; signs like a normal client), [plan/CONTEXT.md](plan/CONTEXT.md) §"GUI vocabulary" (prompt-modifier text box, fork-rerun, pack-consistency grid).
- HTMX partials: each new route returns a small HTML fragment (no `<html>` wrapper, no `{% extends %}`). HTMX swaps it into the named `hx-target`.
- Variants query: `SELECT * FROM external_media_assets WHERE metadata->>'slot_id' = $1 AND agent_run_id IN (SELECT id FROM agent_runs WHERE id = $2 OR parent_run_id = $2) ORDER BY created_at`. Indexed via `idx_ema_metadata_slot`.
- Grid query: `SELECT * FROM external_media_assets WHERE agent_run_id = $1 AND status = 'uploaded' ORDER BY metadata->>'slot_id'`. Indexed via `idx_ema_agent_run`.
- Soft-delete vs supersession: supersession requires a replacement; soft-delete is "this slot's current best is bad and I have nothing better right now." Both transition to `superseded` status; the distinction lives in `metadata.soft_deleted`.
- The inspector self-calling pattern: yes, it's slightly weird, but it (a) reuses the HMAC + idempotency + worker code paths, and (b) means GUI actions and arthor-ai actions exercise the same route. Documented in `app/inspector/router.py` module docstring.
- `parallel_safe: false` because this slice extends `app/inspector/router.py` (which s13 also edits) and `app/inspector/templates/run_detail.html` (which s13 created); s14 follows s13.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s14-inspector-iteration/tests` is fully green (DB-required tests skipped if no DATABASE_URL), no files under `paths_out_of_scope` were modified, and no test files under `slices/s14-inspector-iteration/tests/` were modified.
