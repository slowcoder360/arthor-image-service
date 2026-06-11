# ADR 0012: Hero OpenAI-only + visual strategy layer

- Status: **accepted**
- Date: 2026-06-11
- Supersedes in spirit: Google A/B for heroes (not pack-wide)

## Context

Hero A/B testing showed OpenAI `gpt-image-2` produces usable human/outcome scenes; Google (2.5 Flash and 3 Pro) hallucinates UI, renders text, and mis-handles safe zones. Compiler v2 moved from equipment-first to job-first prompts but models still default to consultation/chair scenes without a **scene archetype** layer.

Full handoff: [`plan/HANDOFF-HERO-VISUAL-STRATEGY.md`](../HANDOFF-HERO-VISUAL-STRATEGY.md).

## Decisions

### 1. Heroes: OpenAI only (for now)

- `hero_candidates_generation` runs use `openai_image` / `gpt-image-2` regardless of `default_provider_hint` from consumer (worker **forces** OpenAI; hint is not rejected with 400).
- Google provider remains registered for **asset pack** paths.
- Inspector A/B lab de-emphasizes or hides Google for hero runs.

### 2. Visual strategy before longer prompts

Insert deterministic resolver between ingress and compiler:

```
HeroCandidatesRequest
  → resolve_visual_strategy()   # lookup: icp + tone + industry → archetype + authenticity_mode
  → compile_variant_prompt()    # catalog[archetype] + layout tail + brand stack
  → OpenAI generate/edit
  → deterministic QA gates
```

No LLM in strategy or compile on the hot path.

### 3. Scene catalog (versioned)

~6 cross-industry archetypes (`shared_joy`, `confident_smile`, `threshold_invitation`, …). Industry supplies modifiers only. Catalog version pinned on run metadata.

### 4. QA gates (deterministic)

Post-generation checks flag `failure_mode` on assets; do not fail entire run unless all variants fail. See handoff table: text-in-image, safe-zone occupancy, palette drift.

Optional single auto-retry on selected modes with `seed + 1`.

### 5. References and edits

- Multi-ref with `role`, `usage_hint`, `note`, `likeness_consent` on ingress (`brand_visual.customer_reference_assets`).
- `POST /images/hero-candidates/regenerate-variant` with typed `edit_kind` (`retry`, `tweak`, `reference`, `rescene`).
- OpenAI edit API when `reference_plan.edit_enabled`; first eligible ref only today.
- No ControlNet in v1.

### 6. arthor-ai contract

v2 (`hero_candidates.2`) remains valid. Full consumer mapping: [`plan/HERO-CANDIDATES-CONSUMER.md`](../HERO-CANDIDATES-CONSUMER.md).

## Consequences

- Simpler ops: one hero provider, one prompt shape to tune.
- Compiler v3 bump breaks prompt_hash cache (intentional).
- Google hero cost table entries become reference-only in inspector.
