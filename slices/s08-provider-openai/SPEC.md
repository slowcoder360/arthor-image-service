---
id: s08-provider-openai
title: ImageProvider Protocol + OpenAIImageProvider + retry helper + cost calculation
depends_on: [s04-payload-contract, s05-agent-runs-writer]
parallel_safe: true
estimated_loc: 450
---

# s08-provider-openai — OpenAI image provider + the shared Protocol

## Summary

The first concrete `ImageProvider` plus the Protocol that s09 also implements. `ImageProvider` is a PEP 544 `Protocol` (per ADR-0007) with `generate_single` and `generate_pack_consistent`; `ProviderResult` is the shared dataclass return type. `OpenAIImageProvider.supports_pack_consistent = False` (falls back to N parallel `generate_single` with reference conditioning). Determinism level is `"best-effort"` (OpenAI image API does not honor a user seed in current public docs). A retry helper auto-retries each failed call once with a new seed per intake decision E. Cost calculation per the documented OpenAI per-image pricing at build time; the rate table lives in code and is one-line updateable.

## Acceptance criteria

- AC-1: `app/providers/protocol.py` defines `ProviderResult` dataclass per ADR-0007 §"Decision": `image_bytes, width, height, seed, provider, model_version, cost_cents, latency_ms, external_id, response_shape, determinism_level`. Field types per the ADR.
- AC-2: `app/providers/protocol.py` defines `ImageProvider` as `@runtime_checkable typing.Protocol` with class attributes `name: str`, `supports_pack_consistent: bool`, `supports_reference_image: bool`, and async methods `generate_single(*, prompt, dimensions, seed, style_profile, reference_images=None) -> ProviderResult` and `generate_pack_consistent(*, prompts, style_profile, seed) -> list[ProviderResult]`.
- AC-3: `app/providers/openai_image.py` defines `class OpenAIImageProvider` with `name = "openai_image"`, `supports_pack_consistent = False`, `supports_reference_image = True`, `model_version: str` (settable; default the current stable model identifier at build time, documented in README). Constructor takes `client: openai.AsyncOpenAI` for test injection.
- AC-4: `generate_single` calls `client.images.generate(model=..., prompt=..., size=f"{w}x{h}")` (or the edit-with-reference variant if `reference_images` provided), times the call, builds `ProviderResult` with `determinism_level="best-effort"`, `seed=None` (the API does not expose seed), `cost_cents` computed from the rate table.
- AC-5: `generate_pack_consistent` raises `NotImplementedError("OpenAI image API does not support native pack-consistent generation; the orchestrator falls back to per-slot calls with reference conditioning")`. Documented in the docstring as expected behavior — callers route based on `supports_pack_consistent`.
- AC-6: `app/providers/retry.py` exports `async def with_retry(fn: Callable[[int | None], Awaitable[T]], *, max_retries: int = 1, base_seed: int | None, new_seed_fn: Callable[[int], int] = lambda s: s + 1) -> T`. Calls `fn(base_seed)`; on `ProviderError` or `asyncio.TimeoutError` retries once with `new_seed_fn(base_seed)`; on second failure raises the original exception wrapped in `RetryExhausted`.
- AC-7: `app/providers/openai_image.py` defines `class OpenAICostTable` with per-model-version per-size rates in cents. Lookup function `cost_for(model_version: str, dimensions: tuple[int, int]) -> int`; raises `UnknownModelVersion` for unrecognized models (forces an explicit table update rather than silently zeroing costs).
- AC-8: `app/providers/openai_image.py` defines `class ProviderError(Exception)` and uses it to wrap underlying SDK errors (rate-limit, auth, server-side); `OpenAIImageProvider` translates `openai.APIError` family into `ProviderError` so callers depend on the abstraction only.

## Paths in scope

- `app/providers/__init__.py`
- `app/providers/protocol.py`
- `app/providers/openai_image.py`
- `app/providers/retry.py`

## Paths out of scope (do not touch)

- `app/providers/google_nano_banana.py` (s09 owns)
- `app/payload/**` (s04 owns), `app/style/**` (s06 owns), `app/runs/**` (s05 owns), `app/storage/**` (s07 owns)
- `app/routes/**`, `app/orchestration/**`, `app/inspector/**`
- `app/main.py`, `app/config.py`, `app/runtime.py`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`, `db/**`

## Failing tests the subagent must turn green

- `slices/s08-provider-openai/tests/test_provider_result_shape.py` — asserts `ProviderResult` has the 11 documented fields with the right types.
- `slices/s08-provider-openai/tests/test_protocol_runtime_checkable.py` — `OpenAIImageProvider` instance passes `isinstance(provider, ImageProvider)` and an obvious non-provider object fails the check.
- `slices/s08-provider-openai/tests/test_openai_provider_attributes.py` — `name == "openai_image"`, `supports_pack_consistent is False`, `supports_reference_image is True`.
- `slices/s08-provider-openai/tests/test_openai_generate_single_happy_path.py` — uses an injected fake `client.images.generate` that returns a known-good base64; `ProviderResult.image_bytes` decoded; `latency_ms > 0`; `determinism_level == "best-effort"`; `seed is None`.
- `slices/s08-provider-openai/tests/test_openai_generate_pack_consistent_raises.py` — `generate_pack_consistent` raises `NotImplementedError` with the documented message.
- `slices/s08-provider-openai/tests/test_with_retry_happy_first.py` — `fn` succeeds on first call; `with_retry` returns the result; only one call observed.
- `slices/s08-provider-openai/tests/test_with_retry_retries_once.py` — `fn` raises `ProviderError` on first call (seed=42), succeeds on second (seed=43); `with_retry` returns the second result; `new_seed_fn` was called once.
- `slices/s08-provider-openai/tests/test_with_retry_exhausted.py` — both calls fail; raises `RetryExhausted` wrapping the original exception.
- `slices/s08-provider-openai/tests/test_cost_table_known_model.py` — known model + known dimensions → expected cents.
- `slices/s08-provider-openai/tests/test_cost_table_unknown_model.py` — raises `UnknownModelVersion`.
- `slices/s08-provider-openai/tests/test_provider_error_translation.py` — fake client raises `openai.APIError`; provider raises `ProviderError`.

## Hints

- ADR anchor: [plan/adr/0007-image-provider-abstraction.md](plan/adr/0007-image-provider-abstraction.md).
- For tests, never make a real OpenAI call. Inject `client: openai.AsyncOpenAI`-shaped stub via the provider constructor. Tests should fake `client.images.generate` and `client.images.edit` only.
- The exact model identifier (e.g. `gpt-image-1` or its successor) is a build-time decision per ADR-0007 §"What gets harder". The README should document the pinned identifier; the cost table maps it to cents. Do not hard-code "gpt-image-1" in tests; pull from `provider.model_version`.
- Reference-conditioning path (when `reference_images` is non-empty): use `client.images.edit` with the first reference image as the source. Validate that only one reference is passed in v1 (OpenAI edit accepts one image); if multiple are passed, use the first and warn in the response_shape.
- `response_shape` (trimmed) per ADR-0007 §"Cost-tracking pattern": include `{model: ..., created: ..., size: ..., n: ..., b64_present: True}` — never the bytes themselves.
- `with_retry` is provider-agnostic; s09 reuses it.
- The cost table is intentionally Pythonic-not-DB so that updating a rate is a one-line PR. Document in README how to bump rates.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s08-provider-openai/tests` is fully green, no files under `paths_out_of_scope` were modified, and no test files under `slices/s08-provider-openai/tests/` were modified.
