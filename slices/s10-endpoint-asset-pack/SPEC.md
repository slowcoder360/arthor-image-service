---
id: s10-endpoint-asset-pack
title: POST /images/asset-pack/generate end-to-end (validation, accept-then-callback, hero-first, reference conditioning, palette-variance, HMAC callback)
depends_on: [s06-style-profile-resolver, s07-r2-uploader, s08-provider-openai, s09-provider-nano-banana]
parallel_safe: false
estimated_loc: 950
---

# s10-endpoint-asset-pack — Asset-pack endpoint + background worker (the spine)

## Summary

The first end-to-end behavior: accept a `PayloadV1` via `POST /images/asset-pack/generate`, return 202 + `agent_run_id`, then run the pack in a background `asyncio.create_task` per ADR-0008. The worker generates the hero first (per `pack.slot_order` and `pack.reference_policy.hero_slot_id`), conditions non-hero slots on the hero bytes (when the provider supports it), runs the deterministic palette-variance check against the resolved `StyleProfile.palette` per ADR-0009 §5, auto-retries each failed slot once with a new seed per intake decision E, supersedes assets when regenerating, and POSTs an HMAC-signed callback to `payload.callback_url` per ADR-0006. The single largest slice in the build — but every component it consumes was built by s04–s09 so this slice is wiring + ordering + error model only.

## Acceptance criteria

- AC-1: `app/routes/asset_pack.py` exposes `POST /images/asset-pack/generate` mounted on the FastAPI app via additive `app/main.py` extension. Route uses `await require_hmac(request)` (s03) to verify the inbound signature before parsing the body.
- AC-2: After HMAC verify, the handler runs `validate_payload(raw_body)`; on errors returns 400 with the structured `ValidationReport`; on success looks up `lookup_idempotency_key(pool, payload.idempotency_key)` (s04).
- AC-3: Idempotent re-fetch: if the key has been seen, returns 200 with `{agent_run_id, status: "<current status>", idempotent_replay: true}` and does NOT enqueue a new background task.
- AC-4: First-time request: writes `agent_runs` row (`insert_pending_run(run_type="image_pack_generation", site_id=payload.site_id, metadata={"site_id": str(payload.site_id), "payload_completeness_score": ...})`), writes `image_request_payloads` row (`insert_payload_record(...)`), resolves StyleProfile (`resolve_style_profile`), patches `agent_runs.metadata.style_profile` via `update_run_status(..., metadata_patch={"style_profile": to_metadata(profile)})`. Returns 202 + `{agent_run_id, status: "accepted"}` and fires `asyncio.create_task(pack_worker.run_in_background(...))`.
- AC-5: `app/orchestration/pack_worker.py:run_in_background(services, *, run_id, payload, style_profile)` acquires `services.asset_pack_semaphore` (cap 4 per ADR-0008), wraps the full body in `try/except/finally`, sets `agent_runs.status = "failed"` with the error message on unhandled exceptions, releases the semaphore in `finally`.
- AC-6: Slot ordering: hero first per `payload.pack.slot_order` and `payload.pack.reference_policy.hero_slot_id`. The hero is generated via `generate_single` (no reference image). On success, the hero's bytes become the reference image for non-hero slots that have `condition_on_slot_id == hero_slot_id` AND the chosen provider's `supports_reference_image is True`.
- AC-7: Provider routing per ADR-0007: `payload.pack.default_provider_hint` → fall back to per-slot `slot.provider_hint` → fall back to the slot-kind default (hero / section_accent / card → `google_nano_banana`; og → `openai_image`). Uses `get_provider(name, services.settings)` (s09).
- AC-8: Pack-consistent path: if all non-hero slots use a provider with `supports_pack_consistent is True` (Gemini nano-banana), the worker calls `generate_pack_consistent` for the non-hero batch. On `ProviderError`, falls back to per-slot `generate_single` with reference conditioning.
- AC-9: Per-slot lifecycle: `insert_pending_asset` (s07) → call provider (wrapped in `with_retry(max_retries=1, base_seed=payload.pack.base_seed + ordinal)`) → `mark_asset_generated` → `upload_asset` to R2 → `mark_asset_uploaded` → `insert_tool_call` (s05) with the timing + cost from `ProviderResult`. On terminal failure: `mark_asset_failed` + `insert_tool_call(status="error")`.
- AC-10: Palette-variance check per ADR-0009 §5: `app/quality/palette_variance.py:check_palette_drift(image_bytes, style_palette, threshold) -> tuple[bool, list[str]]` extracts the dominant palette via Pillow `Image.quantize(colors=8)` + counting, computes the average CIE76 ΔE in LAB color space against `style_palette`, returns `(drift_detected, extracted_hex_palette)`. On drift, patches `external_media_assets.metadata` with `palette_drift = true` and `palette_extracted = [hex_array]`. **Does NOT fail the run** — surfaces in the GUI.
- AC-11: Retry/partial: each `generate_single` call is wrapped in `with_retry(max_retries=1, ...)`. If both attempts fail, the slot's asset row is `failed`; the run completes with `status = "ok"` but the callback body includes the slot's `asset_id` with `status = "failed"`. Pack-level `status` is `"partial"` if any slot failed, else `"complete"`.
- AC-12: Cost rollup: at the end of `run_in_background`, `roll_up_cost(pool, run_id)` (s05) is called; `update_run_status(..., status="ok", finished=True)` is called.
- AC-13: HMAC-signed callback: `app/callback/client.py:send_completion_callback(callback_url, body)` builds the documented body (`{agent_run_id, site_id, status, assets[], total_cost_cents, duration_seconds}`), signs via `sign_outbound(secret, json.dumps(body, sort_keys=True).encode())` (s03), POSTs via `httpx.AsyncClient`. Logs on non-2xx but does not retry in v1.

## Paths in scope

- `app/routes/__init__.py`
- `app/routes/asset_pack.py`
- `app/orchestration/__init__.py`
- `app/orchestration/pack_worker.py`
- `app/quality/__init__.py`
- `app/quality/palette_variance.py`
- `app/callback/__init__.py`
- `app/callback/client.py`
- `app/main.py` (additive only — mount the asset-pack router; initialize `services.asset_pack_semaphore = asyncio.Semaphore(settings.max_concurrent_packs)` in the lifespan)
- `app/runtime.py` (additive only — `asset_pack_semaphore` field already declared optional from s01; this slice populates it in the lifespan extension)

## Paths out of scope (do not touch)

- `app/auth/**` (s03), `app/payload/**` (s04), `app/runs/**` (s05), `app/style/**` (s06), `app/storage/**` (s07), `app/providers/**` (s08, s09)
- `app/routes/regenerate_slot.py` (s11), `app/routes/style_preview.py` (s12), `app/inspector/**` (s13)
- `app/jobs/**` (s16)
- `app/config.py` (the settings keys are already declared in s01)
- `db/**`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s10-endpoint-asset-pack/tests/test_endpoint_rejects_unsigned.py` — POST without `X-Arthor-Signature` returns 401.
- `slices/s10-endpoint-asset-pack/tests/test_endpoint_rejects_invalid_payload.py` — valid HMAC sig but missing required fields → 400 with structured `ValidationReport`.
- `slices/s10-endpoint-asset-pack/tests/test_endpoint_accepts_valid_payload.py` — full valid request → 202 + `{agent_run_id, status: "accepted"}`; an `agent_runs` row + `image_request_payloads` row exist in the DB. `requires_db`.
- `slices/s10-endpoint-asset-pack/tests/test_endpoint_idempotent_replay.py` — same idempotency_key second time → 200 + `idempotent_replay: true`. `requires_db`.
- `slices/s10-endpoint-asset-pack/tests/test_worker_hero_first.py` — fake providers + 3 slots; assert hero is generated first (by recording call order in the fake provider).
- `slices/s10-endpoint-asset-pack/tests/test_worker_reference_conditioning.py` — non-hero slots receive `reference_images=[hero_bytes]` when provider `supports_reference_image is True` and `condition_on_slot_id == hero_slot_id`.
- `slices/s10-endpoint-asset-pack/tests/test_worker_pack_consistent_path.py` — when all non-hero slots use a `supports_pack_consistent is True` provider, the worker calls `generate_pack_consistent` for the non-hero batch (fake provider records the batch call).
- `slices/s10-endpoint-asset-pack/tests/test_worker_pack_consistent_fallback.py` — if `generate_pack_consistent` raises `ProviderError`, the worker falls back to per-slot `generate_single` with reference conditioning.
- `slices/s10-endpoint-asset-pack/tests/test_worker_retry_once.py` — fake provider raises on first call, succeeds on second; the slot's asset is `uploaded`; one `tool_calls` row with `status="ok"` (the retry's tool_call replaces the first).
- `slices/s10-endpoint-asset-pack/tests/test_worker_partial_pack.py` — fake provider fails both attempts for one slot; that slot's asset is `failed`; the pack callback body has `status="partial"`; other slots succeed.
- `slices/s10-endpoint-asset-pack/tests/test_palette_variance_under_threshold.py` — synthetic image with palette close to StyleProfile → `drift_detected is False`; metadata not patched.
- `slices/s10-endpoint-asset-pack/tests/test_palette_variance_over_threshold.py` — synthetic image with very different palette → `drift_detected is True`; `metadata.palette_drift = true`; `metadata.palette_extracted` populated; run still succeeds.
- `slices/s10-endpoint-asset-pack/tests/test_cost_rollup_invoked.py` — at run completion, `agent_runs.cost_cents == SUM(tool_calls.cost_cents)`. `requires_db`.
- `slices/s10-endpoint-asset-pack/tests/test_callback_signed_and_posted.py` — fake `httpx` records the POST; `X-Arthor-Signature` header present; body shape matches the documented schema.
- `slices/s10-endpoint-asset-pack/tests/test_callback_status_complete_vs_partial.py` — all-success → `status="complete"`; any-failure → `status="partial"`; all-failure → `status="failed"`.
- `slices/s10-endpoint-asset-pack/tests/test_semaphore_limit.py` — `max_concurrent_packs=2`; spawn 5 concurrent runs against fake providers that block; asserts only 2 are in-flight at any time.

## Hints

- ADR anchors: [plan/adr/0006-hmac-auth-convention.md](plan/adr/0006-hmac-auth-convention.md), [plan/adr/0007-image-provider-abstraction.md](plan/adr/0007-image-provider-abstraction.md), [plan/adr/0008-background-task-strategy.md](plan/adr/0008-background-task-strategy.md), [plan/adr/0009-style-profile-lifecycle.md](plan/adr/0009-style-profile-lifecycle.md) §5 (palette-variance), [plan/adr/0010-payload-contract-v1.md](plan/adr/0010-payload-contract-v1.md) (reference_policy).
- The lifespan extension in `app/main.py` initializes `services.asset_pack_semaphore = asyncio.Semaphore(services.settings.max_concurrent_packs)`. Keep it additive; the s01 lifespan body remains.
- Background-task error handling per ADR-0008: every `asyncio.create_task` body is `try/except/finally`; unhandled exceptions become `agent_runs.status = "failed"` with the message; the event loop never crashes.
- `tool_calls.run_id` (NOT `agent_run_id`). Reiterating ADR-0004 critical drift one more time because this slice writes the bulk of the tool_calls.
- Palette extraction: prefer Pillow `Image.convert("RGB").quantize(colors=8, method=Image.MEDIANCUT)` + `getpalette()` + occurrence-counting. CIE76 ΔE in LAB via `colormath` (add to dev deps) or hand-rolled (RGB→XYZ→LAB is ~30 lines). Document the choice in code comments.
- Reference conditioning: pass hero bytes as `reference_images=[hero_bytes]` to non-hero `generate_single` calls. The provider abstraction routes via `supports_reference_image`.
- Pack-consistent vs per-slot: prefer `generate_pack_consistent` when EVERY non-hero slot's provider supports it. Mixed providers across slots → per-slot path.
- Cost rollup happens once at the end (not after each provider call). Callback fires after rollup so `total_cost_cents` is accurate.
- `parallel_safe: false` because this slice extends `app/main.py` (the lifespan), and downstream slices s11/s12/s13 may also extend it; sequence them after s10.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s10-endpoint-asset-pack/tests` is fully green (DB-required tests skipped if no DATABASE_URL, R2 mocked, providers faked), no files under `paths_out_of_scope` were modified, and no test files under `slices/s10-endpoint-asset-pack/tests/` were modified.
