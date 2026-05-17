# CONTEXT.md — shared language for arthor-image-service

Every term below is used identically across `plan/plan.md`, `plan/adr/*`, every `slices/<id>/SPEC.md`, every commit message, and every PR description. If a slice needs a new term, add it here first.

## Run-level concepts

| Term | Meaning |
|---|---|
| **Asset pack** | One full collection of images generated from a single image-request payload, all sharing one `StyleProfile`. 8-12 images typical. One pack = one site = one run. |
| **Slot** | One image position in the asset pack, identified by `slot_id`. Has dimensions, intent, copy context, optional provider hint. Multiple variants may exist per slot via regeneration. |
| **StyleProfile** | The resolved-once-per-pack object that contributes the same language to every slot's prompt: palette (light + dark), lighting (full sentence), camera language, composition rules, color grading, register (`photographic` / `illustrated` / `mixed`), mood adjectives, do-not list, must-include list. Persisted on `agent_runs.metadata.style_profile`. |
| **Slot prompt** | The concrete prompt sent to a provider for one slot. Built deterministically from `slot_intent + style_profile + slot.camera + slot.lighting_mood + slot.copy_context`. Its SHA-256 is `prompt_hash`. |
| **Prompt hash** | SHA-256 of the resolved slot prompt. Same hash + same provider + same seed → should produce the same (or near-same) output. Lives in `external_media_assets.metadata.prompt_hash`. |
| **Reference conditioning** | Using the already-generated hero image (or an approved earlier slot) as an input to subsequent slot generations to enforce pack consistency. Provider-dependent (Gemini Flash Image supports, OpenAI image edit supports). |
| **Pack consistency** | The pack-level property that all generated slots feel like one site. Enforced by (a) shared StyleProfile, (b) hero reference conditioning, and (c) deterministic palette-variance check after generation. |
| **Palette drift** | When a generated slot's dominant palette deviates from the pack's palette beyond a configured threshold. Surfaced in the GUI with `metadata.palette_drift = true`; does not auto-fail the run. |
| **Supersession** | When a slot is regenerated, the old `external_media_assets` row gets `status = 'superseded'` and `metadata.replaced_by = <new_id>`. Rows are never deleted. |
| **Cold-storage rotation** | After 30 days, superseded R2 objects move to a `cold/` prefix in the same bucket (daily cron). Active assets stay forever. |

## Determinism vocabulary

| Term | Meaning |
|---|---|
| **Deterministic** | Same input → same output, no LLM inference involved. Used for payload validation, prompt assembly, palette extraction, palette-variance check, supersession, etc. |
| **Inference** | LLM/provider call. Used for image generation itself, and at most one place in the style-profile resolver if the hint's `mood` field is genuinely ambiguous. |
| **Determinism level** | Per-provider tag stored on `external_media_assets.metadata.determinism_level`: `strict` (seed is honored, same prompt + seed reproduces), `best-effort` (provider does not honor seed; reproducibility is approximate), `none` (deterministic re-run not meaningful for this provider). |

## Schema vocabulary

| Term | Meaning |
|---|---|
| **`agent_runs`** | The arthor-agent harness flavor (raw SQL `phase10_arthor_harness.sql` columns: `cost_cents`, `prompt_tokens`, `completion_tokens`, `metadata jsonb`, `status` CHECK, `started_at/finished_at`, `parent_run_id`, `run_type` text). arthor-image-service writes to **this** flavor, not arthor-ai's Drizzle flavor. |
| **`tool_calls`** | Child of `agent_runs` via `run_id` (NOT `agent_run_id`!) with ON DELETE CASCADE. arthor-image-service migration **adds three columns**: `cost_cents`, `provider`, `model_version`. One row per provider call. `args` and `result` are trimmed jsonb (shape + key fields + prompt_hash, NOT full bodies) under §6 retention. |
| **`external_media_assets`** | Defined in this repo's migrations (first concrete consumer; schema audit §4b is concept-only). Full DDL in ADR-0005. |
| **`image_request_payloads`** | New table introduced by this repo; first-class record of the inbound payload with FK from `agent_runs.id`. Supports GUI's "rerun from payload" cleanly. Per intake decision F. |
| **Run type values** | This repo introduces three new `agent_runs.run_type` literals: `image_pack_generation`, `image_slot_regenerate`, `image_style_preview`. The harness column is unconstrained text, so no migration needed. arthor-ai's Drizzle enum gets these added in coordinated W11 push. |
| **prompt_hash** | See above. Lives in `external_media_assets.metadata`. Also stored as the dedupe input for the prompt-template version pin. |

## Auth vocabulary

| Term | Meaning |
|---|---|
| **`X-Arthor-Signature`** | HMAC header for arthor-ai → this service traffic. Format `sha256=<hex>`. Signs the raw JSON body. Mirrors arthor-agent convention. |
| **`FASTAPI_ARTHOR_SHARED_SECRET`** | The shared HMAC secret env-var, same name as arthor-agent. |
| **`INSPECTOR_ADMIN_TOKEN`** | Bearer token for the HTMX inspector GUI. Greenfield env-var (does not exist anywhere in the ecosystem yet). Per intake decision G. |

## GUI vocabulary

| Term | Meaning |
|---|---|
| **Inspector** | The HTMX-driven admin GUI at `/inspector/*`. Justin-only in v1. Uses Jinja2Templates, no JS framework. arthor-image-service ships the first inspector in the arthor ecosystem; the pattern is reference-implementation quality. |
| **Prompt-modifier text box** | A per-slot inline text box in the inspector. Lets Justin override `slot.intent` + `style_profile_hint` for one regeneration without forking the whole pack. Per intake decision C. |
| **Fork-rerun** | "Generate this slot again with a new seed" or "...with a new prompt modifier" — surfaces a new variant in side-by-side. The old variant becomes `superseded`; the new one becomes active. |
| **Pack consistency grid** | A single-screen view of every slot from one pack, displayed at thumbnail size in a grid, so style consistency is immediately visible. Drives Justin's quality verdict. |

## Quality vocabulary

| Term | Meaning |
|---|---|
| **Quality target band** | The 7-8 range on `quality-scorecard.md`'s calibration anchors: "Better than 80% of what small-business owners ship themselves." Anything 1-6 fails the v1 bar. |
| **AI slop** | Catch-all for the 1-2 band: "generic AI slop, off-brand, broken." Justin's verdict surface in the GUI; not auto-detected by v1. |
| **Brand-coherent** | An asset pack that feels like one site (passes pack-consistency check) and like a real brand (does not trigger AI-slop verdict). The two together = v1 done per AC-10. |

## Cross-repo coordination vocabulary

| Term | Meaning |
|---|---|
| **W11 absorb** | When arthor-ai's Drizzle (W11 unified-schema-push) pulls this service's `001_*.sql` migrations into the canonical schema. **No migrations applied to Neon prod from this repo** until that absorb completes. |
| **Site-build emit point** | The new `image_pack_generation` stage inside arthor-ai's `lib/inngest/build-flow/index.ts` `BUILD_STAGES` array, inserted between `RunDesignSystem` and `RunPageComposition` (or after `RunPageComposition` for the full asset-pack call). Wiring this is arthor-ai's work; this repo only documents the contract. |
| **`RunImagePack` skill stub** | Optional artifact this repo may publish at `docs/skills/RunImagePack/SKILL.md` so the Cursor site-build agent has a concrete skill to invoke. Stub, not active code. Per Phase 2 intake direction. |
