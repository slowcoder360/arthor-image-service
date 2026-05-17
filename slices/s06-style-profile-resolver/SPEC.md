---
id: s06-style-profile-resolver
title: Deterministic StyleProfile resolver + default do_not seed list + slot prompt builder + prompt_hash
depends_on: [s04-payload-contract]
parallel_safe: true
estimated_loc: 450
---

# s06-style-profile-resolver — StyleProfile lifecycle (resolve → persist → apply)

## Summary

The consistency unlock. One StyleProfile per pack, resolved deterministically from the payload (with one narrow LLM fallback for mood when both hint+tone are missing), persisted on `agent_runs.metadata.style_profile`, and applied identically to every slot's prompt via a single deterministic template. Computes `prompt_hash` as SHA-256 of the resolved prompt text. The LLM fallback is mockable for tests. No DB writes in this slice — `agent_runs.metadata` writing is the caller's responsibility (s10 stitches the resolver output into the `insert_pending_run` metadata via `update_run_status` patch).

## Acceptance criteria

- AC-1: `app/style/profile.py` exports a `StyleProfile` pydantic model (immutable; `frozen=True`) with fields per ADR-0009 §3: `id: UUID4`, `palette: PaletteSnapshot` (mirrors `BrandVisual.palette`), `lighting: str`, `register: Literal["photographic", "illustrated", "mixed"]`, `composition: list[str]`, `camera_language: str`, `color_grading: str`, `mood: list[str]`, `do_not: list[str]`, `must_include: list[str]`, `resolver_version: Literal["1.0"] = "1.0"`, `resolver_used_llm_fallback: bool = False`.
- AC-2: `app/style/defaults.py` exports `DEFAULT_DO_NOT: tuple[str, ...]` with the 10 entries from ADR-0009 §2 **verbatim** (order matters; tuple, not list, so it cannot be mutated). Exports `DEFAULT_LIGHTING_BY_REGISTER: dict[str, str]` per ADR-0009 §1. Exports `DEFAULT_COMPOSITION: tuple[str, ...]` per ADR-0009 §1.
- AC-3: `app/style/defaults.py` exports `INDUSTRY_DO_NOT_EXTENSIONS: dict[str, tuple[str, ...]]` keyed by industry tag (e.g. `"healthcare"`, `"legal"`, `"finance"`, `"insurance"`). YMYL keys add `"no patient faces"` and `"no medical procedures shown explicitly"` for healthcare; legal adds `"no fake court / courtroom imagery"`, `"no impersonation of judges or jurors"`; finance adds `"no fabricated charts or growth claims"`. (Set is curated; add new keys via PR with Justin's approval.)
- AC-4: `app/style/resolver.py` exports `async def resolve_style_profile(payload: PayloadV1, *, mood_llm_client: MoodLLMClient | None = None) -> StyleProfile`. Deterministic mapping per ADR-0009 §1: palette ← `payload.brand_visual.palette` verbatim; lighting ← `payload.style_profile_hint.lighting` if present else `DEFAULT_LIGHTING_BY_REGISTER[register_default]`; register ← `payload.brand_visual.register_default`; composition ← `payload.style_profile_hint.composition_rules` if non-empty else `DEFAULT_COMPOSITION`; camera_language ← hint else `"35mm environmental, shallow depth-of-field"`; color_grading ← hint else `"natural, true-to-life saturation"`; do_not ← union of `payload.brand_voice.do_not`, `payload.style_profile_hint.do_not`, `DEFAULT_DO_NOT`, `INDUSTRY_DO_NOT_EXTENSIONS[matched_industry_key]`; must_include ← hint else `[]`; mood ← documented LLM-fallback logic in AC-5.
- AC-5: LLM fallback for `mood` (single allowed inference call per ADR-0009 §1.h): triggered iff `payload.style_profile_hint.mood` missing AND `payload.brand_voice.tone` is empty/whitespace AND `len(payload.business.value_prop) < 50`. Calls `mood_llm_client.expand_mood(industry, location, value_prop)` with a 2s timeout and $0.005 budget; on success returns ≤5 adjectives; on timeout / exception / cost cap, defaults to `["approachable", "credible"]` and stamps `resolver_used_llm_fallback = True`. Tests inject a `FakeMoodLLMClient` (`tests/_fixtures/mood_llm.py` — under the slice's tests path).
- AC-6: `app/style/resolver.py` exports `def style_profile_to_metadata(profile: StyleProfile) -> dict` returning the exact dict shape ADR-0009 §3 documents.
- AC-7: `app/style/prompts.py` exports `def build_slot_prompt(profile: StyleProfile, slot: Slot) -> SlotPrompt` where `SlotPrompt` is a dataclass `(text: str, prompt_hash: str, prompt_template_version: str)`. The template matches ADR-0009 §4 exactly. `prompt_hash = sha256(text.encode()).hexdigest()`. `prompt_template_version = "1.0"`.
- AC-8: `app/style/prompts.py` exports `PROMPT_TEMPLATE_VERSION: Literal["1.0"] = "1.0"`. Bumping requires Justin's approval and a new ADR.
- AC-9: Determinism check: calling `resolve_style_profile(p)` then `build_slot_prompt(profile, slot)` twice on identical inputs returns identical text and identical hash. (LLM fallback path is gated behind the mock so non-LLM tests are fully deterministic.)

## Paths in scope

- `app/style/__init__.py`
- `app/style/profile.py`
- `app/style/defaults.py`
- `app/style/resolver.py`
- `app/style/prompts.py`

## Paths out of scope (do not touch)

- `app/payload/**` (s04 owns; the resolver consumes `PayloadV1` but does not modify it)
- `app/runs/**` (s05 owns; the resolver is pure-functional, no DB writes here)
- `app/providers/**`, `app/storage/**`, `app/routes/**`, `app/orchestration/**`, `app/inspector/**`
- `app/main.py`, `app/config.py`, `app/runtime.py`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`, `db/**`

## Failing tests the subagent must turn green

- `slices/s06-style-profile-resolver/tests/test_default_do_not_list.py` — asserts `DEFAULT_DO_NOT` is a tuple of exactly the 10 ADR-0009 strings in order.
- `slices/s06-style-profile-resolver/tests/test_resolve_palette_verbatim.py` — palette is copied byte-for-byte from `payload.brand_visual.palette`.
- `slices/s06-style-profile-resolver/tests/test_resolve_lighting_defaults.py` — table-driven over the three registers; missing hint → default lighting per register.
- `slices/s06-style-profile-resolver/tests/test_resolve_composition_defaults.py` — empty hint → `DEFAULT_COMPOSITION`.
- `slices/s06-style-profile-resolver/tests/test_resolve_do_not_union.py` — union of brand_voice.do_not + hint.do_not + defaults + industry extensions, no duplicates, order = brand-voice first then hint then defaults then industry extension.
- `slices/s06-style-profile-resolver/tests/test_industry_extensions_healthcare.py` — healthcare industry adds the two ADR-0009 YMYL strings.
- `slices/s06-style-profile-resolver/tests/test_mood_llm_fallback_skipped.py` — when hint.mood OR tone OR long value_prop present, no LLM call is made; `resolver_used_llm_fallback = False`.
- `slices/s06-style-profile-resolver/tests/test_mood_llm_fallback_used.py` — when all three triggers are met, `FakeMoodLLMClient.expand_mood` is called; returned adjectives appear in the profile; flag is True.
- `slices/s06-style-profile-resolver/tests/test_mood_llm_fallback_timeout.py` — the fake client raises `TimeoutError`; defaults `["approachable", "credible"]` used; flag is True.
- `slices/s06-style-profile-resolver/tests/test_style_profile_to_metadata.py` — output dict shape matches ADR-0009 §3 keys exactly.
- `slices/s06-style-profile-resolver/tests/test_build_slot_prompt_template.py` — given a canned profile + slot, the prompt text matches an inline expected string verbatim (snapshot-style); `prompt_hash` is the SHA-256 of the text.
- `slices/s06-style-profile-resolver/tests/test_prompt_hash_determinism.py` — two calls with identical inputs produce identical hashes; one-character change in any input field changes the hash.
- `slices/s06-style-profile-resolver/tests/test_prompt_template_version.py` — `PROMPT_TEMPLATE_VERSION == "1.0"`; surfaced on `SlotPrompt`.

## Hints

- ADR anchors: [plan/adr/0009-style-profile-lifecycle.md](plan/adr/0009-style-profile-lifecycle.md) (resolver rules + template), [plan/CONTEXT.md](plan/CONTEXT.md) §"Run-level concepts" (StyleProfile, Slot prompt, Prompt hash).
- The `MoodLLMClient` Protocol lives in `app/style/resolver.py` — single async method `expand_mood(industry, location, value_prop) -> list[str]`. The real client (OpenAI tiny call) is wired by s10/s12 callers; s06 only depends on the Protocol so tests inject a fake.
- The prompt template is intentionally fixed; do NOT vary by `slot_kind` in v1. The same template runs for hero, card, og — the StyleProfile contributes the same language to every prompt (that is the consistency unlock).
- Industry matching is string-contains lower-cased on `payload.business.industry` against the keys of `INDUSTRY_DO_NOT_EXTENSIONS`. Multi-match unions all extensions.
- Hex palette validation already happened in s04; the resolver trusts the input.
- ID generation for the StyleProfile: `uuid.uuid4()` at resolver time; round-trips through `style_profile_to_metadata` unchanged.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s06-style-profile-resolver/tests` is fully green, no files under `paths_out_of_scope` were modified, and no test files under `slices/s06-style-profile-resolver/tests/` were modified.
