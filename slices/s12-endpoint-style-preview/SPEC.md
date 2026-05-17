---
id: s12-endpoint-style-preview
title: POST /images/style-profile/preview synchronous single-probe generation
depends_on: [s06-style-profile-resolver, s07-r2-uploader, s08-provider-openai]
parallel_safe: false
estimated_loc: 200
---

# s12-endpoint-style-preview — Style-profile preview (one cheap probe)

## Summary

A single-image synchronous endpoint that takes a `PayloadV1`, resolves the StyleProfile, runs ONE provider call probing the resolved style on a documented stock subject (e.g. "a representative scene matching the brand's industry"), uploads, and returns the URL + agent_run_id within the request lifecycle. Cheap, fast, no callback — Justin uses it from the GUI (s13) to sanity-check the resolved style before paying for a full 8-12-image pack. Sequenced after s10 because it extends `app/main.py` (route mount) and depends on the same shared provider/storage layers.

## Acceptance criteria

- AC-1: `app/routes/style_preview.py` exposes `POST /images/style-profile/preview` mounted on the FastAPI app via additive `app/main.py` extension. Route uses `require_hmac` (s03).
- AC-2: Accepts a full `PayloadV1` (same validator as s10); reuses idempotency lookup (`lookup_idempotency_key`) so repeated previews for the same key return the existing run.
- AC-3: First-time request: writes `agent_runs` row (`run_type="image_style_preview"`, `metadata.site_id=...`), writes `image_request_payloads`, resolves `StyleProfile`, patches `agent_runs.metadata.style_profile`.
- AC-4: Generates one probe image **synchronously** (no `asyncio.create_task`). Uses the smallest size of the chosen provider's default (e.g. 1024x1024 for OpenAI, the equivalent for Gemini); cost is ~1 image. Provider routing: `payload.pack.default_provider_hint` else `openai_image` default.
- AC-5: Constructs a probe `Slot` deterministically from `payload.business` (`subject.primary = f"a representative scene for a {payload.business.industry} in {payload.location.city or payload.location.country}"`, `subject.setting = "natural environment"`, no `copy_context`, default camera/lighting from `StyleProfile`). Documented in code; the probe slot is canonical so previews are reproducible.
- AC-6: Uploads the result to R2 via `upload_asset` (s07) with `slot_id = "style_profile_preview"` and the probe metadata; writes `external_media_assets` row; inserts one `tool_calls` row; calls `roll_up_cost`.
- AC-7: Returns 200 with `{agent_run_id, asset_id, r2_url, prompt_hash, cost_cents, latency_ms}` synchronously. Total endpoint latency budget: 30s (provider call latency dominates); timeout returns 504.
- AC-8: Errors: provider failure → 502 with `{error: "provider_error", retry: false}` (no auto-retry for the synchronous probe — Justin re-clicks if needed); validation failure → 400 with the structured ValidationReport.

## Paths in scope

- `app/routes/style_preview.py`
- `app/main.py` (additive — mount the style-preview router only)

## Paths out of scope (do not touch)

- `app/routes/asset_pack.py` (s10), `app/routes/regenerate_slot.py` (s11)
- `app/orchestration/pack_worker.py` (this slice does NOT use the pack worker — it's synchronous and short)
- `app/auth/**`, `app/payload/**`, `app/runs/**`, `app/style/**`, `app/storage/**`, `app/providers/**`, `app/quality/**`, `app/callback/**`, `app/inspector/**`, `app/jobs/**`
- `app/config.py`, `app/runtime.py`
- `db/**`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s12-endpoint-style-preview/tests/test_preview_rejects_unsigned.py` — POST without HMAC → 401.
- `slices/s12-endpoint-style-preview/tests/test_preview_rejects_invalid_payload.py` — missing required fields → 400.
- `slices/s12-endpoint-style-preview/tests/test_preview_happy_path.py` — `requires_db` — valid request returns 200 + the documented body shape; agent_runs row has `run_type="image_style_preview"`; one external_media_assets row exists with `metadata.slot_id="style_profile_preview"`.
- `slices/s12-endpoint-style-preview/tests/test_preview_idempotent.py` — `requires_db` — same `idempotency_key` returns the prior preview's `asset_id`.
- `slices/s12-endpoint-style-preview/tests/test_preview_probe_slot_canonical.py` — the resolved prompt for the probe slot is deterministic given the same payload (snapshot-style assertion).
- `slices/s12-endpoint-style-preview/tests/test_preview_provider_routing.py` — `default_provider_hint = "google_nano_banana"` routes to Gemini; absent hint defaults to OpenAI; unknown hint → 400.
- `slices/s12-endpoint-style-preview/tests/test_preview_provider_error_502.py` — fake provider raises `ProviderError` → 502.

## Hints

- ADR anchors: [plan/adr/0009-style-profile-lifecycle.md](plan/adr/0009-style-profile-lifecycle.md) (resolver reuse), [plan/adr/0007-image-provider-abstraction.md](plan/adr/0007-image-provider-abstraction.md) (provider call), packet §"style-profile preview endpoint".
- This endpoint deliberately does NOT use the pack worker. The synchronous path is short enough to keep inline; introducing a background task here adds polling complexity for what should be a snappy GUI action.
- Cost capture still goes through `insert_tool_call` + `roll_up_cost` so the cost rollup views (s15) include preview runs.
- The probe slot template is canonical and lives in this slice — do not duplicate it in s13. The GUI's "preview style" button just POSTs the same payload through this endpoint.
- `parallel_safe: false` because this slice extends `app/main.py`; sequences after s11 (which also extends main.py).

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s12-endpoint-style-preview/tests` is fully green (DB-required tests skipped if no DATABASE_URL), no files under `paths_out_of_scope` were modified, and no test files under `slices/s12-endpoint-style-preview/tests/` were modified.
