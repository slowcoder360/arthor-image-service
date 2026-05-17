---
id: s07-r2-uploader
title: aiobotocore R2 client + hybrid-key uploader + external_media_assets writer + supersession + cold-storage move
depends_on: [s02-db-pool-and-migrations-001]
parallel_safe: true
estimated_loc: 500
---

# s07-r2-uploader — R2 client + asset writer + supersession + cold-storage primitive

## Summary

The storage layer. Async R2 client built on `aiobotocore`. Hybrid-key uploader per intake decision A: object key is `arthor-image-service/<site_id>/<asset_id>.<ext>`; the run/slot relationships ride in R2 **object metadata** so per-site listings stay flat. The `external_media_assets` state-machine writer (`pending → generated → uploaded → (failed | superseded)`) per ADR-0005. A supersession helper that transitions `uploaded → superseded` and sets `metadata.replaced_by`. A cold-storage move primitive (`uploaded` or `superseded` → `cold/<key>`); the cron that drives it is s16.

## Acceptance criteria

- AC-1: `app/storage/r2.py` exports `class R2Client` with `from_settings(settings: Settings) -> R2Client` factory. Uses `aiobotocore.session.get_session().create_client("s3", endpoint_url=settings.r2_endpoint_url, aws_access_key_id=..., aws_secret_access_key=..., region_name="auto")`. Context-manager friendly (`async with R2Client.from_settings(settings) as r2: ...`).
- AC-2: `app/storage/uploader.py` exports `async def upload_asset(r2: R2Client, *, image_bytes: bytes, site_id: uuid.UUID, asset_id: uuid.UUID, ext: str, content_type: str, object_metadata: AssetObjectMetadata) -> str` returning the `r2_key`. Key = `f"arthor-image-service/{site_id}/{asset_id}.{ext}"`. Calls `put_object` with `Bucket=settings.r2_bucket`, the key, `Body=image_bytes`, `ContentType=content_type`, `Metadata={...}` populated from `object_metadata`.
- AC-3: `app/storage/uploader.py` defines `AssetObjectMetadata` dataclass with the required string fields per ADR-0005 + intake decision A: `run_id, slot_id, agent_run_id, provider, model_version, prompt_hash, seed, style_profile_id`. Renders to `dict[str, str]` (R2 metadata is string-typed); `seed=None` renders as the empty string.
- AC-4: `app/storage/uploader.py` exports `def public_url_for(settings: Settings, r2_key: str) -> str` returning `f"{settings.r2_endpoint_url}/{settings.r2_bucket}/{r2_key}"` for v1 (assumes the bucket is public; tighten when private signing is needed).
- AC-5: `app/storage/asset_writer.py` exports `async def insert_pending_asset(pool, *, agent_run_id, site_id, provider, model_version, metadata: dict) -> uuid.UUID`. Inserts an `external_media_assets` row with `status="pending"`. Validates `metadata` has the required keys per ADR-0005 §"Metadata jsonb keys" (`slot_id, slot_intent, style_profile_id, prompt_hash, seed, determinism_level, run_id`); raises `ValueError` on missing required.
- AC-6: `app/storage/asset_writer.py` exports `async def mark_asset_generated(pool, asset_id, *, width, height, bytes_len, external_id, metadata_patch: dict | None = None) -> None` and `async def mark_asset_uploaded(pool, asset_id, *, r2_key, r2_url) -> None` and `async def mark_asset_failed(pool, asset_id, *, error: str) -> None`. Each transitions per the ADR-0005 state machine and validates the source status (e.g. `mark_asset_uploaded` requires current status in `{pending, generated}`); raises `InvalidStateTransition` otherwise.
- AC-7: `app/storage/supersession.py` exports `async def supersede_asset(pool, *, old_asset_id, new_asset_id) -> None`. Validates `old` is currently `uploaded`; transitions to `superseded`; sets `metadata = metadata || jsonb_build_object('replaced_by', $new_asset_id::text)`. Atomic in a single statement.
- AC-8: `app/storage/supersession.py` exports `async def unsupersede_asset(pool, *, asset_id) -> None`. Reverses supersession: transitions `superseded → uploaded`, removes `metadata.replaced_by`. Only allowed if the replacing asset still exists (lookup via `metadata->>'replaced_by'`).
- AC-9: `app/storage/r2.py` exports `async def move_to_cold_storage(r2: R2Client, *, src_key: str) -> str` returning the new key `cold/<src_key>`. Copies the object server-side then deletes the original. Used by s16 cron.
- AC-10: `app/main.py` lifespan additively initializes `services.r2 = await R2Client.from_settings(settings).__aenter__()` when all four `r2_*` settings are set; closes via `await services.r2.__aexit__(...)` in the shutdown branch. When any setting is missing, lifespan logs a single warning and leaves `services.r2 = None`. Keep additive; do not rewrite the s01/s02 lifespan body.

## Paths in scope

- `app/storage/__init__.py`
- `app/storage/r2.py`
- `app/storage/uploader.py`
- `app/storage/asset_writer.py`
- `app/storage/supersession.py`
- `app/main.py` (additive — R2 lifespan init/teardown only)

## Paths out of scope (do not touch)

- `db/migrations/**` (s02 owns the DDL)
- `app/runs/**` (s05 owns the agent_runs/tool_calls layer; this slice only writes to `external_media_assets`)
- `app/payload/**`, `app/style/**`, `app/providers/**`, `app/routes/**`, `app/orchestration/**`, `app/inspector/**`, `app/jobs/**`
- `app/main.py`, `app/config.py`, `app/runtime.py`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s07-r2-uploader/tests/test_r2_client_factory.py` — `R2Client.from_settings(...)` returns a client when all four `r2_*` settings are set; raises `ConfigurationError` if any is None.
- `slices/s07-r2-uploader/tests/test_upload_key_layout.py` — `upload_asset` calls `put_object` with key `arthor-image-service/<site_id>/<asset_id>.<ext>`. Uses a `moto`-style mocked S3 backend or a hand-rolled `aiobotocore` stub.
- `slices/s07-r2-uploader/tests/test_upload_object_metadata.py` — `put_object` is called with `Metadata={"run_id": ..., "slot_id": ..., "agent_run_id": ..., "provider": ..., "model_version": ..., "prompt_hash": ..., "seed": ..., "style_profile_id": ...}`; `seed=None` renders as `""`.
- `slices/s07-r2-uploader/tests/test_public_url_for.py` — string composition.
- `slices/s07-r2-uploader/tests/test_insert_pending_asset_validates_metadata.py` — `requires_db` — missing required key raises `ValueError`; complete metadata writes a row with `status="pending"`.
- `slices/s07-r2-uploader/tests/test_state_machine_transitions.py` — `requires_db` — full happy path `pending → generated → uploaded`; an attempt to `mark_asset_uploaded` from `failed` raises `InvalidStateTransition`; `mark_asset_failed` valid from `pending` and from `generated` only.
- `slices/s07-r2-uploader/tests/test_supersede_asset.py` — `requires_db` — atomic transition `uploaded → superseded`; `metadata.replaced_by` set; `supersede_asset` on a non-`uploaded` row raises `InvalidStateTransition`.
- `slices/s07-r2-uploader/tests/test_unsupersede_asset.py` — `requires_db` — transitions `superseded → uploaded`; removes `metadata.replaced_by`; if the replacing asset is gone (FK cascade fired), raises `UnsupersedeUnavailable`.
- `slices/s07-r2-uploader/tests/test_move_to_cold_storage.py` — server-side copy + delete via mocked S3; returns new key `cold/<orig>`.

## Hints

- ADR anchors: [plan/adr/0005-external-media-assets-ddl.md](plan/adr/0005-external-media-assets-ddl.md) (state machine + metadata keys), intake decision A in [scratch/intake-notes.md](scratch/intake-notes.md) §7 (hybrid key + R2 object metadata fields).
- For R2 mocking in tests, prefer `moto` (`pip install moto[s3]`) over hand-rolling an `aiobotocore` stub. Decorate test functions with `@mock_aws`. Confirm `moto` is in `pyproject.toml` dev extras (s01); add if missing.
- `aiobotocore` semantics: `async with session.create_client(...) as client: await client.put_object(...)`. The `R2Client` wrapper holds the session + client and exposes `.client` for raw operations and convenience methods for the common cases.
- R2 metadata keys must be lowercase ASCII strings; values must be strings. Validate at the dataclass-render layer.
- State-machine transitions use a single SQL UPDATE with `WHERE id = $1 AND status = ANY($source_states)`. Inspect rowcount; if 0, raise `InvalidStateTransition`.
- The cold-storage **policy** (30 days old, daily sweep) lives in s16; this slice only ships the **primitive** to perform one move.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s07-r2-uploader/tests` is fully green (DB-required tests skipped if no DATABASE_URL, R2-mocked tests always run), no files under `paths_out_of_scope` were modified, and no test files under `slices/s07-r2-uploader/tests/` were modified.
