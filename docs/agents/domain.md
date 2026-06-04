# Domain Docs — arthor-image-service

How engineers and agent skills should consume this repo's domain documentation.

**New here?** Read this file, then [`plan/CONTEXT.md`](../../plan/CONTEXT.md), then any slice `SPEC.md` you are working on.

## Before exploring, read these (in order)

1. [`plan/CONTEXT.md`](../../plan/CONTEXT.md) — shared language (asset pack, StyleProfile, determinism vocabulary, harness terms)
2. [`plan/adr/`](../../plan/adr/) — architecture decision records
3. [`plan/plan.md`](../../plan/plan.md) — build plan and scope boundaries
4. Cross-repo platform terms — [`~/arthor-brainstorm/synthesis/ecosystem-glossary.md`](../../../arthor-brainstorm/synthesis/ecosystem-glossary.md)
5. The slice `SPEC.md` for your task under `slices/<id>/`

## Use the glossary's vocabulary

When naming runs, slots, provider calls, inspector UI copy, or metadata fields, use terms exactly as defined in `plan/CONTEXT.md`. Prefer **deterministic** vs **inference** labels consistently; do not introduce alternate names for `agent_runs` harness columns documented there.

## Flag ADR conflicts

If your output contradicts an ADR in `plan/adr/`, surface it explicitly rather than silently overriding.
