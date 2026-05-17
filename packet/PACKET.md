---
name: arthor-image-service
one_liner: FastAPI service that accepts a Cursor site-build payload and returns a contextually-consistent asset pack (8-12 generated images) per site, with cost capture and an admin GUI for prompt iteration.
owner: justin
deadline: pre-launch (no fixed date; ships when v1 quality bar passes)

goals:
  - Receive a structured image-request payload from the Cursor site-build pipeline and return an asset pack whose images share palette, lighting, register, and mood (one site = one pack feel).
  - Provide a provider abstraction over the new OpenAI image model and Google nano-banana (Gemini 2.5 Flash Image) such that swapping providers is a single config flip.
  - Capture every provider call as a `tool_calls` row tied to a parent `agent_runs` row for full cost attribution per run, per site, per provider, per slot-type.
  - Ship a FastAPI + HTMX admin GUI that lets Justin inspect runs, fork-and-rerun a single slot with a new seed or tweaked prompt, and compare slot variants side by side.
  - Author numbered SQL migrations for the shared Neon Postgres (extending `external_media_assets` per the schema-audit) without applying them to prod — coordinated with W11 unified-schema-push.
  - Enforce style consistency via a per-pack resolved StyleProfile shared across all slot prompts, plus deterministic palette-variance checks across the pack.
  - Authenticate arthor-ai inbound traffic via HMAC (mirroring the existing arthor-agent ↔ arthor-ai pattern); authenticate the GUI via `INSPECTOR_ADMIN_TOKEN`.

out_of_scope:
  - Custom model training (LoRA, fine-tunes, brand-specific style adapters).
  - Animation, video, GIFs, vector/SVG generation, in-GUI image editing or inpainting/outpainting.
  - Customer-facing image upload or selection UI; multi-tenant customer dashboards.
  - Autonomous re-generation based on quality scoring; LLM-as-judge in v1.
  - Cross-site brand-coherence enforcement across multiple sites of the same business.
  - OG image text overlay generation (handled in arthor-ai site-build pipeline).
  - Writing to any arthor-ai owned table beyond reading `sites.id`.
  - Inngest. Long-running work uses FastAPI BackgroundTasks; callbacks happen via HTTP.
  - Applying migrations to Neon prod (deferred to W11).
  - Pushing to a GitHub remote until the failing-tests phase is past (per Justin 2026-05-16).

success_criteria:
  - id: AC-1
    description: End-to-end test pass — a real Cursor site-build run (e.g. Sacramento sports PT clinic) emits a payload, the service generates 8-12 assets that visibly share palette/lighting/mood, the callback fires back to arthor-ai, and the resulting site ships with the generated images.
    measurable: true
  - id: AC-2
    description: GUI demonstrates the run — Justin opens the GUI, finds the run, sees every slot's resolved prompt + provider response + cost + duration, and can fork-and-rerun a single slot with a new seed or tweaked prompt.
    measurable: true
  - id: AC-3
    description: HMAC integration verified — a stub arthor-ai client successfully calls each authenticated endpoint with a valid signature; the same call is rejected with a bad or expired signature.
    measurable: true
  - id: AC-4
    description: Cost rollup works — `agent_runs.cost_cents` for an asset-pack run equals the sum of its child `tool_calls.cost_cents` (one per provider call). Per-site cost is queryable from the GUI.
    measurable: true
  - id: AC-5
    description: Provider abstraction verified — the service swaps between the OpenAI image driver and the Google nano-banana driver with a single config flip; the same payload routes through either and produces a valid pack.
    measurable: true
  - id: AC-6
    description: Deterministic re-run verified — re-running an existing run with the same payload + same seed reproduces (or near-reproduces, per documented provider determinism level) the prior assets; the run metadata records the level for each provider.
    measurable: true
  - id: AC-7
    description: Pack consistency demonstrated — a single run's assets pass a deterministic palette-variance check within a configured threshold; drift is surfaced in the GUI when the threshold is exceeded.
    measurable: true
  - id: AC-8
    description: Migration sequence committed but not applied — numbered SQL migrations (`db/migrations/001_*.sql`, ...) land in the repo and are coordinated with W11; nothing is pushed to Neon prod.
    measurable: true
  - id: AC-9
    description: README + `system.yaml` — README explains local run and tests; `system.yaml` exists at repo root matching the arthor-systemmap schema.
    measurable: true
  - id: AC-10
    description: Quality bar passed — Justin reviews a fresh asset pack in the GUI and verdicts "this looks like a real site's image set, not AI slop." If not, iterate prompts and style profiles until that verdict is reached.
    measurable: false

constraints:
  stack:
    - Python (FastAPI, Pydantic, asyncpg or psycopg, Jinja2 + HTMX, pytest)
    - Postgres (shared Neon; arthor-ai is schema custodian)
    - Cloudflare R2 (asset storage; same convention as existing arthor media storage)
    - Providers — OpenAI image API + Google Gemini 2.5 Flash Image
  deployment: Local dev only for v1; deployment target TBD by arthor-ai sibling pattern when arthor-seo-service ships.
  performance: One asset-pack run (8-12 images) completes in under ~120 seconds wall clock when both providers are reachable; per-image generation latency captured in `tool_calls.latency_ms`.
  deadline: Pre-launch quality workstream. Launch can ship with placeholders if W21 slips, but the quality bar suffers.

tech_context:
  repo_path: /Users/justinmendez/arthor-image-service
  primary_language: python
  key_libs:
    - fastapi
    - pydantic
    - asyncpg
    - jinja2
    - htmx
    - openai
    - google-genai
    - boto3 (or aiobotocore for R2)
    - pytest
    - pytest-asyncio
  conventions_doc: docs/builder-os-folder-contract.md

open_questions:
  - "Exact provider model identifiers at build time (OpenAI image model successor to gpt-image-1, Gemini 2.5 Flash Image exact model string). Record in `external_media_assets.model_version` and README."
  - "Payload schema versioning policy — adopt `payload_version: \"1.0\"` on every payload and document the v1.x migration path."
  - "R2 bucket key layout — `arthor-image-service/<site_id>/<run_id>/<slot_id>/<asset_id>.<ext>` vs flat by `agent_run_id`. Pick + document."
  - "Retention policy for superseded assets — v1 default 30 days then cold storage; confirm with Justin."
  - "Whether to cache identical-payload requests across sites — likely no (hit rate ~0); revisit if cost spikes."
  - "Style profile authoring UX in the GUI — read-only display vs editable form. v1 default read-only with fork-rerun for overrides."
  - "Reference-image conditioning storage — re-fetch hero bytes from R2 per call vs local cache."
  - "Whether the Cursor site-build agent needs a new `RunImagePack` skill in `seo-core/skills/` to emit the payload (out of scope here; flag for arthor-ai)."
  - "Background task strategy — start with FastAPI `BackgroundTasks`; document the trigger condition to graduate to an external queue (Celery / RQ / asyncio worker)."
  - "Failure handling for partial packs — v1 default `status=partial` + manual GUI retry vs auto-retry of the failed slot."
  - "Stale ref in packet — `~/arthor-ai/lib/inngest/functions/site-build.ts` does not exist. The real surfaces are `lib/site-build-prompts.ts`, `lib/site-build-subagent-prompt.ts`, and `__tests__/inngest/site-build-subagents.test.ts`. `research-and-plan` must pin the exact image-payload emit point."
  - "Confirm storage shape for the Cursor-emitted payload — new `image_request_payloads` table vs `agent_runs.input_payload` jsonb."
  - "Confirm `INSPECTOR_ADMIN_TOKEN` as the GUI auth env-var name (mirroring arthor-agent inspector)."

refs:
  - path: packet/SPEC.md
    note: "Verbatim original packet prose (the human-authored development packet for arthor-image-service v1). Authoritative spec. Schema fields above are a structured projection; if they disagree, SPEC.md wins and the open-question list should grow."
  - path: packet/refs/arthor-brainstorm-AGENTS.md
    note: "Ecosystem primer; §1 user rules, §6 cost telemetry, §7 Q1-Q14 decisions, §11 anti-patterns."
  - path: packet/refs/phase-plan.md
    note: "W21 framing and W11 unified-schema-push timing."
  - path: packet/refs/arthor-seo-service-packet.md
    note: "Architectural sibling whose patterns this service mirrors. Service is unbuilt — patterns inferred from arthor-agent and documented in ADRs."
  - path: packet/refs/quality-scorecard.md
    note: "`design_coherence` and `embarrassment_score` are the dimensions this service moves."
  - path: packet/refs/db-schema-audit.md
    note: "§4b `external_media_assets` row shape; §6 retention rules for `tool_calls.args`."
  - path: packet/refs/gtm-heygen-direction.md
    note: "§1 \"no synthetic AI-guru aesthetic\" — applies to image style profiles."
  - path: packet/refs/site-build-prompts.ts
    note: "Corrected pointer (the packet's `lib/inngest/functions/site-build.ts` does not exist). One of the surfaces where the new image-payload stage will slot in."
  - path: packet/refs/site-build-subagent-prompt.ts
    note: "Corrected pointer; subagent prompt for the Cursor site-build pipeline."
  - path: packet/refs/site-build-subagents.test.ts
    note: "Test harness for the site-build pipeline."
  - path: packet/refs/system.example.yaml
    note: "arthor-systemmap schema reference for the required `system.yaml`."
  - path: packet/refs/arthor-agent
    note: "Read-only sibling repo. v1 patterns (HMAC auth, FastAPI app shape, SQL migration conventions, HTMX inspector GUI) are inferred from here per ADR."
---

# arthor-image-service

This packet is a thin schema-compliant wrapper over the authoritative spec at [packet/SPEC.md](SPEC.md). All goals, scope, decisions, contracts, and acceptance criteria come from `SPEC.md`. The frontmatter above projects them into the [builder-os packet schema](../../builder-os/packet/schema.json) so the intake skill can validate.

When this wrapper and `SPEC.md` disagree, `SPEC.md` wins and `open_questions` grows. The wrapper exists only to satisfy schema validation and to give agents a single-glance map of goals, ACs, refs, and known unknowns.

## Why a separate SPEC.md

The original packet was authored as long-form prose and is too rich to compress into schema fields without losing nuance. Storing it verbatim keeps the human's words untouched (per the user rule "only change what you need to change") while still allowing schema-driven workflows.
