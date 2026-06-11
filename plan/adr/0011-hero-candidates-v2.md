# ADR 0011: Hero candidates v2 contract (`hero_candidates.2`)

- Status: proposed
- Date: 2026-06-11

## Context

arthor-ai's `HeroCandidateVariation` includes CTAs, nav labels, and supporting text used only in the preview frame UI. The v1 hero payload (`hero_candidates.1`) sent only `headline` and `subhead`, losing spatial signals needed for offer-tone CTA overlay geometry.

## Decision

Add optional **`hero_candidates.2`** fields on `HeroCandidatesRequest` without changing provider prompt rules:

| Field | Stored on run | In provider prompt? |
|-------|---------------|---------------------|
| `payload_version` | yes | no |
| `variants[].copy_metrics` | yes (via `hero_copy_overlay`) | no — drives geometry only |
| `variants[].copy_overlay` | yes (`agent_runs.metadata.hero_copy_overlay`) | **never** |

Provider prompts remain compiled by [`app/style/hero_prompt_compiler.py`](../app/style/hero_prompt_compiler.py). Copy strings must not appear in `metadata.hero_provider_prompts[].prompt`.

## arthor-ai Phase 1b mapping (separate PR)

Extend [`hero-candidates-types.ts`](../../../arthor-ai/lib/integrations/arthor-image/hero-candidates-types.ts) and [`build-hero-payload.ts`](../../../arthor-ai/lib/integrations/arthor-image/build-hero-payload.ts):

```typescript
variants: [{
  tone_angle, headline, subhead?,
  copy_metrics?: { headline_chars, has_subhead, has_cta, cta_chars, nav_count },
  copy_overlay?: { primary_cta?, secondary_cta?, supporting_text?, nav_labels? },
}]
payload_version?: "hero_candidates.2"
```

When `copy_metrics` is omitted, image-service derives counts from headline/subhead/copy_overlay.

## Defaults (image-service)

- `HERO_DEFAULT_PROVIDER=openai_image`
- `OPENAI_IMAGE_MODEL=gpt-image-2`, `OPENAI_IMAGE_QUALITY=medium`
- `GOOGLE_IMAGE_MODEL=gemini-2.5-flash-image` (evaluate `gemini-3.1-flash-image` via A/B lab)

## Consequences

- v1 payloads remain valid (`payload_version` defaults to `hero_candidates.1`).
- arthor-ai can ship copy overlay in a follow-up PR without blocking image-service deploy.
- Inspector A/B lab shows compiled prompts from run metadata before images finish.
