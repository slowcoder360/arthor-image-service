# RunImagePack (read-only contract stub)

> Published by arthor-image-service for arthor-ai / seo-core adoption. **Does not invoke providers from Cursor in v1** — the site-build Inngest stage calls `ArthorImageClient` instead.

## Purpose

Teach the site-build agent how asset packs fit the pipeline: PayloadV1 assembly inputs, pending-pack discipline, and placement of returned R2 URLs. Not a creative engine — style resolution lives in image-service.

## Canonical contract

- Payload shape: `~/arthor-image-service/plan/adr/0010-payload-contract-v1.md`
- Runtime models: `app/payload/models.py`
- Integration handoff: `~/arthor-brainstorm/roadmap/arthor-image-service-launch-handoff.md`

## Agent rules

1. **Do not** pick stock-photo URLs while a pack is `pending` / `running`.
2. After callback (or poll fallback), write returned `r2_url` values into component image imports and `SiteSpec.images`.
3. Payload assembly is **deterministic** — no LLM in the builder; map from `SiteSpec`, brand tokens, and sitemap slot manifest.
4. Every generate call requires `idempotency_key` (≥ 8 chars).
5. Minimum-viable payload is acceptable; read `payload_completeness_score` from the service response.

## Build-stage sequence (arthor-ai)

1. After `RunPageComposition`, emit PayloadV1 inside its own `step.run`.
2. `POST /images/asset-pack/generate` (HMAC) → `202` + `agent_run_id`.
3. `waitForEvent` for `image-pack-completed`; on timeout, poll `GET /images/asset-pack/{run_id}`.
4. Persist assets to `SiteSpec.images`; Cursor placement-only for source files.

## Out of scope

- Direct HMAC calls from Cursor to image-service in v1
- Customer-facing image upload UI
- Writing to image-service tables from arthor-ai (except `image_request_payloads` via service on inbound)
