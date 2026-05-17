---
id: s11-endpoint-regenerate-slot
title: POST /images/regenerate-slot single-slot rerun + supersession transition
depends_on: [s10-endpoint-asset-pack]
parallel_safe: false
estimated_loc: 250
---

# s11-endpoint-regenerate-slot — Single-slot rerun

## Summary

The quality-iteration endpoint. Takes a previously-generated `asset_id`, optional `new_seed`, and optional `new_prompt_modifier`; runs one fresh generation through the same pack worker (single-slot mode); supersedes the old asset; returns the new asset_id. Reuses `pack_worker` machinery from s10 in single-slot mode rather than duplicating the lifecycle. Writes an `agent_runs` row with `run_type = "image_slot_regenerate"` and `parent_run_id` linking to the original pack run.

## Acceptance criteria

- AC-1: `app/routes/regenerate_slot.py` exposes `POST /images/regenerate-slot` mounted on the FastAPI app via additive `app/main.py` extension. Route uses `require_hmac` (s03).
- AC-2: Request body: `{asset_id: UUID4, new_seed: int | None, new_prompt_modifier: str | None}`. `asset_id` is the previously-`uploaded` external_media_assets row.
- AC-3: Validation: 404 if `asset_id` is unknown; 400 if the asset's current `status` is not `uploaded` (cannot regenerate from `failed` or `superseded`); 400 if both `new_seed` and `new_prompt_modifier` are None (no-op).
- AC-4: Fetches the original `image_request_payloads` row via `agent_runs.id → external_media_assets.agent_run_id → image_request_payloads.agent_run_id` join; pulls the slot definition by `metadata.slot_id`. Resolves the StyleProfile from the original `agent_runs.metadata.style_profile` (re-uses; does not re-resolve).
- AC-5: Optionally overlays `new_prompt_modifier` on `slot.intent` (concatenates with a separator) before calling `build_slot_prompt`. New seed = `new_seed` if provided else `original_seed + 1`.
- AC-6: Creates a NEW `agent_runs` row with `run_type = "image_slot_regenerate"`, `parent_run_id = original_run_id`, `metadata.original_asset_id = <asset_id>`. Returns 202 + `{agent_run_id: new_run_id, new_asset_id: <pending_uuid>, status: "accepted"}`.
- AC-7: Background work fires via `pack_worker.run_single_slot_in_background(services, *, new_run_id, slot, style_profile, seed, prompt_modifier_text)`. On success: `supersede_asset(pool, old_asset_id=asset_id, new_asset_id=new_asset_id)` (s07); on failure: new asset row marked `failed`, old asset stays `uploaded` (no supersession on failure).
- AC-8: `app/orchestration/pack_worker.py` gets a new `run_single_slot_in_background` function (added to the existing module; not a new file). Mirrors `run_in_background` semantics for one slot only: no pack-consistent path, no hero ordering — just `insert_pending_asset → generate_single → mark_asset_generated → upload → mark_asset_uploaded → insert_tool_call → roll_up_cost`. No callback fires for slot regenerations (the GUI polls; arthor-ai doesn't get notified).
- AC-9: Idempotency on regenerate is **not** supported in v1 (each click is a fresh attempt). Documented in the docstring.

## Paths in scope

- `app/routes/regenerate_slot.py`
- `app/orchestration/pack_worker.py` (additive — add `run_single_slot_in_background`; do not rewrite `run_in_background`)
- `app/main.py` (additive — mount the regenerate-slot router)

## Paths out of scope (do not touch)

- `app/routes/asset_pack.py` (s10 owns)
- `app/auth/**`, `app/payload/**`, `app/runs/**`, `app/style/**`, `app/storage/**`, `app/providers/**`, `app/quality/**`, `app/callback/**`, `app/inspector/**`, `app/jobs/**`
- `app/config.py`, `app/runtime.py`
- `db/**`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s11-endpoint-regenerate-slot/tests/test_regenerate_rejects_unsigned.py` — POST without HMAC → 401.
- `slices/s11-endpoint-regenerate-slot/tests/test_regenerate_unknown_asset.py` — unknown `asset_id` → 404.
- `slices/s11-endpoint-regenerate-slot/tests/test_regenerate_invalid_status.py` — `requires_db` — asset already `superseded` or `failed` → 400.
- `slices/s11-endpoint-regenerate-slot/tests/test_regenerate_no_op.py` — both `new_seed` and `new_prompt_modifier` missing → 400.
- `slices/s11-endpoint-regenerate-slot/tests/test_regenerate_happy_path.py` — `requires_db` — valid request returns 202 + new run_id + new asset_id; after the background task finishes, the old asset is `superseded` with `metadata.replaced_by = new_asset_id`; the new asset is `uploaded`.
- `slices/s11-endpoint-regenerate-slot/tests/test_regenerate_new_run_lineage.py` — `requires_db` — new agent_runs row has `run_type="image_slot_regenerate"`, `parent_run_id=original_run_id`, `metadata.original_asset_id=old_asset_id`.
- `slices/s11-endpoint-regenerate-slot/tests/test_regenerate_failure_leaves_old.py` — `requires_db` — fake provider fails both attempts; new asset is `failed`; old asset stays `uploaded` (no supersession on failure).
- `slices/s11-endpoint-regenerate-slot/tests/test_regenerate_prompt_modifier_overlay.py` — `new_prompt_modifier="…with neon accents"` shows up in the resolved prompt text; new `prompt_hash` differs from old.
- `slices/s11-endpoint-regenerate-slot/tests/test_regenerate_seed_increment_default.py` — when `new_seed` is omitted, new seed = original_seed + 1.

## Hints

- ADR anchors: [plan/adr/0007-image-provider-abstraction.md](plan/adr/0007-image-provider-abstraction.md) (retry policy carries over), [plan/CONTEXT.md](plan/CONTEXT.md) §"Run-level concepts" (Supersession).
- Reuse, do not rewrite. The `run_single_slot_in_background` is a tighter version of `run_in_background` that skips the hero-ordering + callback steps.
- Lookup chain to get the slot definition: `agent_runs → image_request_payloads (via agent_run_id) → payload jsonb → slots[] filtered by metadata.slot_id`. Pull from `external_media_assets.metadata.slot_id`.
- Prompt modifier overlay: append to `slot.intent` with separator ` — Adjust: <modifier>`. Document this convention in code so the inspector form (s14) renders consistent placeholder text.
- `parallel_safe: false` because this slice extends both `app/main.py` (route mount) and `app/orchestration/pack_worker.py`; sequences after s10.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s11-endpoint-regenerate-slot/tests` is fully green (DB-required tests skipped if no DATABASE_URL), no files under `paths_out_of_scope` were modified, and no test files under `slices/s11-endpoint-regenerate-slot/tests/` were modified.
