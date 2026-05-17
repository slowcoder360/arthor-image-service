---
id: s09-provider-nano-banana
title: GoogleNanoBananaProvider (Gemini 2.5 Flash Image) + provider registry
depends_on: [s04-payload-contract, s05-agent-runs-writer, s08-provider-openai]
parallel_safe: false
estimated_loc: 400
---

# s09-provider-nano-banana — Google nano-banana provider + registry

## Summary

The second concrete `ImageProvider`. `GoogleNanoBananaProvider` (Gemini 2.5 Flash Image, internal name "nano-banana"). `supports_pack_consistent = True` — Gemini's multi-image consistency call is the highest-leverage trick for pack coherence and is the reason we pull in this provider. Determinism is `"strict"` if the chosen model honors seed (verify at implementation time per ADR-0007), else downgraded to `"best-effort"`. Reuses `with_retry` from s08. Registers both providers in `app/providers/__init__.py:PROVIDERS` so callers can route by name. Sequenced after s08 because both slices touch `app/providers/__init__.py` (the registry export).

## Acceptance criteria

- AC-1: `app/providers/google_nano_banana.py` defines `class GoogleNanoBananaProvider` with `name = "google_nano_banana"`, `supports_pack_consistent = True`, `supports_reference_image = True`, `model_version: str` (settable; default the current Gemini 2.5 Flash Image identifier at build time, documented in README). Constructor takes `client: google.genai.Client` for test injection.
- AC-2: `generate_single` calls the Gemini image generation API with the resolved prompt, dimensions, and optional reference image(s). Returns `ProviderResult` with `seed` (if honored), `determinism_level` per the seed honoring outcome, `cost_cents` from the cost table, trimmed `response_shape`.
- AC-3: `generate_pack_consistent` calls the Gemini multi-image batch endpoint with all prompts in one call, sharing the StyleProfile language and (when available) a fixed batch seed. Returns one `ProviderResult` per input prompt in input order.
- AC-4: `generate_pack_consistent` accepts `prompts: list[SlotPrompt]` (from s06) and uses the prompt text + dimensions per slot. The `StyleProfile.id` is stamped into the response_shape for cross-result correlation.
- AC-5: Reuses `app.providers.retry.with_retry` for the single-call path. For the pack-consistent path, if the batch fails wholesale, the orchestrator (s10) falls back to per-slot generation with reference conditioning — the provider raises `ProviderError` and lets the caller route.
- AC-6: `app/providers/google_nano_banana.py` defines `class GoogleCostTable` with per-model-version per-size rates (cents). Same shape as `OpenAICostTable`; `cost_for(model_version, dimensions) -> int`; raises `UnknownModelVersion` for unrecognized models.
- AC-7: `app/providers/__init__.py` exports `PROVIDERS: dict[str, type[ImageProvider]]` containing `"openai_image": OpenAIImageProvider` and `"google_nano_banana": GoogleNanoBananaProvider`. Exports `def get_provider(name: str, settings: Settings) -> ImageProvider` that constructs the provider with the appropriate SDK client.
- AC-8: SDK error translation: `google.genai.errors.APIError` (or equivalent) → `ProviderError` (defined in s08). The orchestrator depends on `ProviderError` only.

## Paths in scope

- `app/providers/google_nano_banana.py`
- `app/providers/__init__.py` (additive — extend the registry; do not rewrite s08's contributions)

## Paths out of scope (do not touch)

- `app/providers/protocol.py`, `app/providers/openai_image.py`, `app/providers/retry.py` (s08 owns; this slice consumes them)
- `app/payload/**`, `app/style/**`, `app/runs/**`, `app/storage/**`
- `app/routes/**`, `app/orchestration/**`, `app/inspector/**`
- `app/main.py`, `app/config.py`, `app/runtime.py`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`, `db/**`

## Failing tests the subagent must turn green

- `slices/s09-provider-nano-banana/tests/test_nano_banana_attributes.py` — `name == "google_nano_banana"`, `supports_pack_consistent is True`, `supports_reference_image is True`.
- `slices/s09-provider-nano-banana/tests/test_nano_banana_runtime_checkable.py` — passes `isinstance(provider, ImageProvider)`.
- `slices/s09-provider-nano-banana/tests/test_nano_banana_generate_single.py` — uses an injected fake `client` that returns a known image; `ProviderResult.determinism_level in {"strict", "best-effort"}` (depending on the fake's seed support); `latency_ms > 0`.
- `slices/s09-provider-nano-banana/tests/test_nano_banana_generate_pack_consistent.py` — N input prompts → N `ProviderResult`s in input order; same `style_profile_id` stamped on each `response_shape`.
- `slices/s09-provider-nano-banana/tests/test_nano_banana_batch_failure_raises.py` — fake client raises on batch call → `ProviderError`; the orchestrator-level fallback is s10's concern, not this slice's.
- `slices/s09-provider-nano-banana/tests/test_nano_banana_provider_error_translation.py` — SDK error class translated to `ProviderError`.
- `slices/s09-provider-nano-banana/tests/test_cost_table_known_model.py` — known model + dimensions → expected cents.
- `slices/s09-provider-nano-banana/tests/test_cost_table_unknown_model.py` — raises `UnknownModelVersion`.
- `slices/s09-provider-nano-banana/tests/test_providers_registry.py` — `PROVIDERS` dict contains both providers by name; `get_provider("openai_image", settings)` returns an `OpenAIImageProvider`; `get_provider("google_nano_banana", settings)` returns a `GoogleNanoBananaProvider`; `get_provider("unknown", settings)` raises `KeyError`.

## Hints

- ADR anchor: [plan/adr/0007-image-provider-abstraction.md](plan/adr/0007-image-provider-abstraction.md). [scratch/research/11-provider-abstraction.md](scratch/research/11-provider-abstraction.md) for the survey context.
- SDK: `google-genai` (the new official SDK). Inject the client; never make a real API call from tests.
- The Gemini batch call interface evolves; verify at implementation time and pin the version in `pyproject.toml`. Document the pinned version in README alongside the OpenAI version.
- `determinism_level = "strict"` ONLY if the chosen model documents seed honoring AND we successfully round-trip a fixed seed through the SDK. Otherwise downgrade to `"best-effort"` with a comment citing the verification step.
- `generate_pack_consistent` returns results in **input order** — the orchestrator (s10) expects to zip `prompts` and `results` directly.
- The registry export means s09 edits `app/providers/__init__.py` — keep the edit additive; do not rewrite the s08 imports or registry declaration. The user rule applies.
- `parallel_safe: false` because this slice and s08 both edit `app/providers/__init__.py`; s09 sequences after s08.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s09-provider-nano-banana/tests` is fully green, no files under `paths_out_of_scope` were modified, and no test files under `slices/s09-provider-nano-banana/tests/` were modified.
