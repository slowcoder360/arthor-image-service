# Development packet — `arthor-image-service` v1

> **Status: drafted 2026-05-16. Ready for an implementing agent to pick up.** Scope-and-contract packet, not implementation spec. Implementing agent decides file structure, library choices, exact code, and migration sequencing. This packet specifies *what* must exist and *why*, not *how* to build it.

## Required reading before starting

In order:

1. `~/arthor-brainstorm/AGENTS.md` — ecosystem primer. Especially §1 (user rules), §6 (verified facts about arthor-ai cost telemetry gaps and `external_media_assets` schema concept), §7 (Q1-Q14 decisions), §11 (anti-patterns).
2. `~/arthor-brainstorm/roadmap/phase-plan.md` — workstream W21 context.
3. `~/arthor-brainstorm/roadmap/arthor-seo-service-packet.md` — the architectural sibling. arthor-image-service mirrors its patterns (FastAPI, GUI for prompt iteration, HMAC auth with arthor-ai, shared Neon, cost capture into `agent_runs` + `tool_calls`, accept-then-callback). When this packet is silent on infrastructure shape, copy the arthor-seo-service answer.
4. `~/arthor-brainstorm/synthesis/db-schema-audit.md` §4b — the `external_media_assets` schema concept (originally scoped for HeyGen/ElevenLabs). v1 extends it to cover generated site images. No new top-level tables expected.
5. `~/arthor-brainstorm/synthesis/gtm-heygen-direction.md` — adjacent media-generation context. Note §1's "no synthetic AI-guru aesthetic" rule applies here too; image style should feel like a real brand, not generic AI art.
6. `~/arthor-ai/lib/inngest/functions/site-build.ts` (especially `BUILD_STAGES`) — where the Cursor site-build pipeline lives today. The image-request payload emits from a new stage here. Do not modify; just understand the surface.

If anything in this packet contradicts the synthesis docs, the synthesis docs win — flag the contradiction in the PR rather than silently improvising.

---

## Why this service exists

The Cursor site-build agent today produces sites with stock-photo aesthetic or placeholder imagery. The output ships, but it's a visible quality gap (see [`roadmap/quality-scorecard.md`](quality-scorecard.md) — `design_coherence` and `embarrassment_score` are the dimensions most directly hit).

Justin's framing: *"The Cursor website-building agent could build an image request payload so we can generate an asset pack for a client website that contextually fits and looks good."*

arthor-image-service is the FastAPI replacement for "the Cursor agent just picks a stock photo URL." It owns:

- Receiving a structured payload from the Cursor site-build agent describing slot requirements + brand + style profile.
- Generating contextual asset packs with shared style across slots (the pack feels like one site).
- Cost capture per generation.
- A debugging GUI for prompt iteration and quality review.

It does NOT own: model training, animation, video, vector/SVG, customer-facing image uploads, multi-tenant request batching.

---

## v1 scope

### In scope

| Module | Responsibility |
|---|---|
| **Payload contract** | Accept the Cursor-emitted JSON payload: site identity (industry, location, brand colors, voice), per-slot requirements (slot_id, dimensions, intent, mood, count), style profile (palette, lighting, illustration vs photographic, mood modifiers), explicit do-not list, callback URL. Validate strictly. |
| **Style profile resolution** | Take the payload's brand + voice + first slot's intent. Resolve into a concrete style profile (palette hex codes, lighting language, illustration register, composition rules) shared across all slots in this pack. Style profile is per-pack, not per-slot — that's the consistency unlock. |
| **Asset pack generation** | For each slot, build the per-slot prompt (style profile + slot intent + slot mood + dimensions). Call provider. Receive image. Validate (dimensions, file integrity, optional NSFW filter). Upload to R2. Write `external_media_assets` row. Repeat for all slots. |
| **Provider abstraction** | Common interface across the new OpenAI image model + Google nano-banana (Gemini 2.5 Flash Image). Provider-specific quirks (multi-image consistency calls, IP-adapter, conditioning) hidden behind the abstraction. |
| **Cost capture** | Every provider call writes a `tool_calls` row tied to the parent `agent_runs.id` for the asset-pack run, with `prompt_tokens` (where applicable), `cost_cents`, `latency_ms`, `provider`, `model_version`. Roll up to `agent_runs.cost_cents` on completion. |
| **Accept-then-callback integration** | arthor-ai calls `POST /images/asset-pack/generate`; service returns 202 + `agent_run_id`; service does the work async; on completion, service POSTs callback to arthor-ai with `{agent_run_id, status, assets[]}`. Same pattern as arthor-seo-service. |
| **Single-slot regenerate** | Slot quality is iterative. `POST /images/regenerate-slot` accepts a previous `slot_id` + optional new prompt override + optional new seed; generates one replacement; updates the `external_media_assets` row. |
| **Debugging GUI** | FastAPI-hosted (HTMX). Runs list, run detail with full payload + every generated asset + cost, prompt-modifier editor, fork-and-rerun per slot, side-by-side comparison of slot variants, regenerate-with-new-seed. Same shape as arthor-seo-service's GUI. |
| **Deterministic re-run** | Every generation stores `seed`, `provider`, `model_version`, and `prompt_hash`. Re-running with identical inputs reproduces (or near-reproduces, depending on provider determinism) the same output. Stored in `external_media_assets.metadata`. |

### Explicitly out of scope for v1

- **Custom model training** (LoRA, fine-tunes, brand-specific style adapters). Out forever per AGENTS.md §1 "no in-house avatar/voice infra" — same principle extends to image gen.
- **Animation, video, GIFs.** Static raster only.
- **Vector / SVG generation.** Use existing icon libraries for vector needs.
- **Customer-direct image gen requests.** Only the Cursor site-build agent (or, post-launch, the arthor-content Phase 2 pipeline) invokes this service. No customer-facing upload UI.
- **Multi-tenant customer-facing dashboard.** GUI is admin-only for Justin (and future hires).
- **Cross-site brand-coherence enforcement** (treating multiple sites for the same business as one brand). One run = one site = one pack. Cross-site consistency is post-launch.
- **Autonomous re-generation** (the service noticing an asset looks bad and replacing it). Quality bar is Justin's eye in v1; GUI provides the iteration surface.
- **Image editing / inpainting / outpainting** (alterations to existing images). Generate-from-scratch only in v1.
- **OG image text overlay generation** as a separate path. v1 generates the base image; if text overlay is needed, that happens in the site-build pipeline via existing tooling, not here.
- **Background removal, alpha compositing, layering.** Provider outputs ship as-is.

---

## Architecture decisions already made

These are not the implementing agent's call — they're decided. Override only with explicit Justin sign-off.

| Decision | Source |
|---|---|
| Separate FastAPI repo `arthor-image-service` | Justin chat 2026-05-16 (this question explicitly answered) |
| Shared Neon Postgres (same DB as arthor-ai / arthor-agent / arthor-seo-service) | Q2 (arthor-ai stays custodian); follow arthor-seo-service pattern |
| arthor-ai is the schema custodian — this service writes raw SQL migrations to the shared DB; arthor-ai's Drizzle gets mirror definitions later in the unified push (W11) | Q2, Q5 |
| GUI hosted by this service (FastAPI templates / HTMX), not in arthor-ai | Match arthor-seo-service pattern |
| Auth between arthor-ai and arthor-image-service: HMAC-signed requests, same pattern as arthor-agent ↔ arthor-ai (`FASTAPI_ARTHOR_SHARED_SECRET`) | Match existing convention |
| v1 providers: new OpenAI image model + Google nano-banana (Gemini 2.5 Flash Image). Implementing agent picks current stable model name at build time | Justin chat 2026-05-16 |
| R2 for asset storage. URLs stored in `external_media_assets` | Match existing media storage convention |
| Deterministic gates over LLM inference wherever possible | Q7 + project-wide principle |
| Cost capture rolls up through existing `agent_runs` + `tool_calls` substrate | Same as arthor-seo-service |
| No in-house image model training | AGENTS.md §1 |
| Accept-then-callback for long-running generation; sync only for trivial single-image cases | Match arthor-seo-service async pattern |

---

## Database contracts

Authoritative concept: `external_media_assets` per `synthesis/db-schema-audit.md` §4b. Originally scoped for HeyGen/ElevenLabs; v1 of arthor-image-service is the first concrete consumer.

### `external_media_assets` row shape (consumed by this service)

| Field | Notes |
|---|---|
| `id` | uuid PK |
| `provider` | `openai_image | google_imagen | google_nano_banana` (text — text-with-allow-list per project convention) |
| `external_id` | provider's run/asset ID for reproducibility |
| `model_version` | model identifier at the time of generation |
| `status` | `pending | generated | uploaded | failed | superseded` |
| `expiration` | nullable; for providers that expire signed URLs |
| `r2_key` | path in our R2 bucket |
| `r2_url` | public URL (or signed URL for private buckets) |
| `width`, `height` | dimensions, integer |
| `bytes` | file size |
| `metadata` | jsonb — holds `{seed, prompt_hash, slot_id, slot_intent, style_profile_id, run_id, replaced_by, original_run_id}` |
| `agent_run_id` | FK → `agent_runs.id` (so cost rolls up) |
| `site_id` | FK → `sites.id` (so per-site asset inventory is queryable) |
| `created_at`, `updated_at` | timestamptz |

### Optional new table

`image_request_payloads` — captures the Cursor-emitted JSON payload as a first-class record, FK from `agent_runs`. Useful for the GUI's "rerun from payload" capability. Implementing agent can decide: store in `agent_runs.input_payload` jsonb vs. dedicated table. Flag in PR with recommendation.

### Schema migration sequencing

Write migrations in numbered files (`001_*.sql`, `002_*.sql`, ...) so the unified-schema-push agent (W11) can absorb them later. Don't apply migrations to Neon prod yet — coordinate with W11. For local dev, the implementing agent runs them against a dev branch.

### Required behavior at the table level

- **Soft supersession, not deletion.** When a slot is regenerated, the old `external_media_assets` row gets `status='superseded'` + `metadata.replaced_by=<new_id>`. Never DELETE — assets are evidence trail for cost + quality iteration.
- **R2 retention.** Superseded assets retain their R2 file for 30 days, then a daily cron moves them to a cold-storage prefix. Active assets retain forever.
- **`metadata.prompt_hash`** is a deterministic SHA-256 of the resolved prompt (style profile + slot intent + slot mood + dimensions). Same hash = same prompt = should re-generate similar output given same seed.

---

## API contract

For v1, the **minimum endpoints** that must work end-to-end:

```
POST   /images/asset-pack/generate          # accept payload, return 202 + agent_run_id
GET    /images/asset-pack/{run_id}          # status + assets[]
POST   /images/regenerate-slot              # single-slot rerun
GET    /images/runs                         # paginated list (admin GUI)
GET    /images/runs/{run_id}                # run detail (admin GUI)
GET    /images/assets/{asset_id}            # single asset metadata
POST   /images/style-profile/preview        # generate a single style-probe image to validate a style profile before pack generation
```

### Required for every endpoint

- HMAC auth header verification on requests from arthor-ai. Reject unsigned or expired requests. GUI uses a separate admin token (suggested: `INSPECTOR_ADMIN_TOKEN` — match arthor-agent inspector pattern).
- All POST routes write one `agent_runs` row per high-level operation, run_type ∈ `image_pack_generation | image_slot_regenerate | image_style_preview`. Child `tool_calls` per provider call.
- Cost capture: every provider call writes a `tool_calls` row with `cost_cents`, `latency_ms`, `provider`, `model_version`. Roll up to `agent_runs.cost_cents` on completion.
- Deterministic 4xx vs 5xx error model. 4xx for caller errors (bad payload, missing site, invalid dimensions). 5xx for service or provider failures.
- Idempotency: `/asset-pack/generate` accepts an idempotency key and does not re-run if the key has been seen (return the existing run).

### Output shape conventions

- Every endpoint that creates a record returns the full record, not just the ID.
- Every endpoint that returns a list paginates by default.
- Every response includes `agent_run_id` so callers can fetch the run + cost + tool calls.

---

## Integration contract with arthor-ai

arthor-ai (specifically, the Cursor site-build pipeline) calls into this service. This service does not call into arthor-ai except for the completion callback.

### The image-request payload (Cursor → arthor-image-service)

The Cursor site-build agent emits this payload during a new build stage (between page composition and final verification). Suggested JSON shape (implementing agent finalizes):

```json
{
  "site_id": "<uuid>",
  "callback_url": "<arthor-ai callback endpoint>",
  "brand": {
    "industry": "physical therapy",
    "location": "Sacramento, CA",
    "palette": { "primary": "#0A4B6F", "secondary": "#E8B83B", "neutral": "#F4F0E8" },
    "voice": "warm, professional, locally-rooted",
    "do_not": ["stock-photo aesthetic", "AI-uncanny faces", "generic gym imagery"]
  },
  "style_profile_hint": {
    "lighting": "warm natural light, golden hour",
    "register": "photographic",
    "mood": "approachable, expert, calm",
    "composition": "rule-of-thirds, mid-distance, shallow depth-of-field"
  },
  "slots": [
    {
      "slot_id": "home_hero",
      "page": "/",
      "intent": "hero — establish trust and warmth, no faces, focus on hands-on care environment",
      "dimensions": { "w": 1920, "h": 1080 },
      "count": 1
    },
    {
      "slot_id": "services_card_sports",
      "page": "/services/sports-physical-therapy",
      "intent": "card — illustrate sports rehab in a way that matches the hero's mood",
      "dimensions": { "w": 800, "h": 600 },
      "count": 1
    }
  ]
}
```

### What this service sends back (callback)

```json
{
  "agent_run_id": "<uuid>",
  "site_id": "<uuid>",
  "status": "complete | partial | failed",
  "assets": [
    {
      "slot_id": "home_hero",
      "asset_id": "<uuid>",
      "r2_url": "https://...",
      "width": 1920,
      "height": 1080,
      "provider": "google_nano_banana",
      "model_version": "<at-build-time>",
      "seed": 42,
      "cost_cents": 8
    }
  ],
  "total_cost_cents": 64,
  "duration_seconds": 47
}
```

### What this service does NOT do

- Does not write to `sites.projectState`. arthor-ai owns that.
- Does not directly modify customer GitHub repos. arthor-ai's site-build pipeline writes the image URLs into the source files.
- Does not send email, SMS, or anything human-facing.
- Does not invoke Cursor agents. Receives payloads, doesn't initiate them.

---

## GUI requirements

FastAPI-hosted, admin-only, secured behind a simple shared secret or basic auth (Justin only — multi-user is post-v1). Matches arthor-seo-service GUI pattern.

### Must support

| Capability | Why |
|---|---|
| List recent asset-pack runs across all sites | "What's the service done lately?" |
| Run detail page: full payload, resolved style profile, every slot's prompt, every generated asset, every provider response, every cost, every duration | Justin needs full visibility to debug quality issues |
| Per-slot prompt editor (override style profile / slot intent / mood for re-generation) | Iterate on slot quality without re-running the full pack |
| Fork-and-rerun per slot (with new seed or new prompt) | Quality iteration loop |
| Side-by-side comparison of slot variants (the slot's history of generations) | See whether changes improved things |
| "What did the model see" view: full prompt rendered + style profile + reference inputs (if any) | Catch prompt drift |
| Cost rollup: per-run, per-day, per-site, per-provider, per-slot-type | Cost visibility |
| Provider response inspector with raw API payloads | Failure modes often live at the provider interpretation layer |
| Pack consistency view: all slots from one run displayed in a grid so style consistency is immediately visible | Catch consistency drift before shipping |
| Soft-delete / unsupersede control | If a regeneration is worse, roll back to the previous slot |

### Nice-to-have for v1 but not blocking

- A/B prompt experiments (run same payload through two prompt-strategy versions, side-by-side).
- Notes / annotations per run for Justin's own review.
- Export run as JSON for sharing with another agent.
- Bulk re-generate (all slots of one type across recent runs, e.g. "regenerate all hero images with this new style profile").

### Explicitly out of v1

- Multi-user accounts.
- Customer-facing dashboards.
- Real-time websocket updates (poll-based refresh is fine).
- Anything that requires a JS framework. HTMX + server-side rendering is the bar.
- In-GUI image editing (cropping, color-correcting, retouching).

---

## Provider strategy

v1 prototypes against two providers:

1. **New OpenAI image model** (current stable at build time — likely `gpt-image-1` successor; verify model name when implementing). Strong text-in-image rendering, good for OG images and feature cards. Higher cost per image.
2. **Google nano-banana** (Gemini 2.5 Flash Image). Strong at multi-image consistency within a pack (matches our pack-level use case). Lower cost.

The implementing agent picks the current model names at build time and stores them in `external_media_assets.model_version`. Models will evolve; the abstraction lets v1 swap without ripping the architecture.

### Provider abstraction

A common interface:

```python
class ImageProvider(Protocol):
    name: str  # 'openai_image' | 'google_nano_banana' | ...

    async def generate_single(
        self,
        prompt: str,
        dimensions: tuple[int, int],
        seed: int | None,
        style_profile: StyleProfile,
        reference_images: list[bytes] | None = None,
    ) -> ProviderResult: ...

    async def generate_pack_consistent(
        self,
        prompts: list[SlotPrompt],
        style_profile: StyleProfile,
        seed: int | None,
    ) -> list[ProviderResult]: ...
```

`generate_pack_consistent` exists because providers like Gemini Flash Image support multi-image consistency natively in a single call — that's the whole point of using it. If a provider doesn't support pack-consistent generation, the abstraction falls back to N calls of `generate_single` with shared style-profile prompts + reference-image conditioning.

### Default provider selection

For v1, the implementing agent picks the default per slot-type based on what each provider is best at. Suggested default:

- **Hero + section accent slots**: Gemini nano-banana (consistency matters most here).
- **OG / social images** (if scoped): new OpenAI image model (text-in-image strength).
- **Card / feature illustration slots**: Gemini nano-banana.

Per-run override available via the payload (a slot can specify `provider_hint`).

---

## Style consistency strategy

The whole point of "asset pack" is that 8-12 images for one site feel like one site. The architecture must enforce this, not hope for it.

### Style profile lifecycle

1. **Resolve.** Take the payload's brand + style_profile_hint + first slot's intent. Resolve into a concrete `StyleProfile` object: palette hex codes, lighting language (full sentences, not keywords), illustration register (photographic / illustrated / mixed), composition rules, mood adjectives, do-not list.
2. **Persist.** Store the resolved `StyleProfile` on the `agent_runs.metadata` (or in a small `style_profiles` table — implementing agent's call).
3. **Apply.** Every per-slot prompt is built from `slot_intent + style_profile`. The style profile contributes the same language to every prompt. No slot invents its own style.
4. **Validate.** After generation, an optional deterministic check: extract dominant palette from generated image, compare against `style_profile.palette`. If divergence exceeds threshold, mark the slot as `palette_drift` in the run metadata and surface in the GUI. (Note: this is deterministic — no LLM check.)

### Reference-image conditioning

For providers that support it (Gemini Flash Image, OpenAI image edit, etc.), once the hero is generated and approved, subsequent slots in the pack can be conditioned on the hero as a reference image. This is the single highest-leverage trick for pack consistency. Implementing agent verifies provider support at build time.

### Style-profile preview endpoint

`POST /images/style-profile/preview` generates one cheap image probing the resolved style profile, before the full pack runs. Helps Justin sanity-check the style profile via the GUI before committing to 8-12 generations. Costs ~1 image, returns within seconds.

---

## Deterministic-first enforcement

| Step | Determinism level |
|---|---|
| Payload validation (required fields, dimension limits, do-not list match) | Deterministic |
| Style profile resolution from brand + hint | Deterministic (lookup table + rules; LLM only for the open-ended `mood` field if hint is ambiguous) |
| Slot prompt assembly (style profile + slot intent) | Deterministic (template) |
| Provider selection per slot | Deterministic (rules per slot-type with payload override) |
| Image generation itself | Inference (provider-side) — by definition |
| Output validation (dimensions, file integrity, file size limits, palette extraction) | Deterministic |
| NSFW / do-not match against generated image | Deterministic (palette extraction + provider's safety classifier) |
| Quality scoring ("is this image actually good?") | Human review via GUI (no LLM-as-judge in v1) |
| Pack consistency check (palette extraction across slots, variance score) | Deterministic |
| Soft supersession on slot regeneration | Deterministic |

If the implementing agent finds a place where LLM inference is being used for what could be deterministic, flag in PR and propose the deterministic alternative.

---

## What "v1 done" looks like

Acceptance criteria, in order:

1. **End-to-end test pass.** Take a real test site build (e.g. the Sacramento sports physical therapy clinic used in the W4 / arthor-seo-service quality testing). The Cursor site-build pipeline emits the payload mid-build. arthor-image-service receives it, generates 8-12 contextually-fitting assets across hero / section / card slots. Assets feel like one site (shared palette, shared lighting, shared mood). Cursor pipeline receives callback and writes asset URLs into the source files. Site ships with the generated images.
2. **GUI demonstrates the run.** Justin opens the GUI, finds the run, walks through every slot, sees prompts + provider responses + costs + decisions. Can fork-and-rerun a single slot with a tweaked prompt or new seed.
3. **HMAC integration verified.** A separate test from a stub arthor-ai client successfully calls each endpoint with a valid signature; rejected with bad signature.
4. **Cost rollup works.** `agent_runs.cost_cents` for the full asset-pack reflects the sum of child `tool_calls.cost_cents` (one per provider call). Per-site cost queryable from the GUI.
5. **Provider abstraction verified.** Service can swap between OpenAI image model and Google nano-banana with a single config flip. Same payload routes to either provider and produces a valid pack.
6. **Deterministic re-run verified.** Re-running an existing run with same payload + same seed produces the same (or near-same, depending on provider determinism) assets. Documented per-provider determinism level in the run metadata.
7. **Pack consistency demonstrated.** For a single run, all generated assets pass a deterministic palette-variance check (within threshold). If they don't, the GUI surfaces the drift and Justin can rerun.
8. **Migration sequence committed but NOT yet applied to prod.** Migrations land in numbered files in the repo. Production application coordinated with W11 (unified schema push).
9. **README + `system.yaml`.** README explains how to run the service locally + tests. `system.yaml` exists at repo root for arthor-systemmap to pick up.
10. **Quality bar passed.** Justin reviews a fresh test build's asset pack in the GUI. Verdict is "this looks like a real site's image set, not AI slop." If verdict is "AI slop," iterate on prompts and style profiles before declaring v1 complete.

---

## Things to NOT do

- Don't train custom models (LoRA, fine-tunes, brand-specific adapters). Use providers as-is.
- Don't build animation, video, GIFs, or vector/SVG generation.
- Don't build a customer-facing image upload or selection UI. v1 GUI is for Justin.
- Don't store full prompt bodies in `tool_calls.args` (per `synthesis/db-schema-audit.md` §6 retention rules). Store input shape + prompt_hash. Reproduce on demand from prompt-template version + payload.
- Don't store raw provider API responses indefinitely. Trim before persisting; 90-day retention on the trimmed payload.
- Don't apply migrations to Neon prod. Coordinate with W11.
- Don't write to arthor-ai's tables. Read `sites.id` only; everything else is your own.
- Don't add a JS frontend. HTMX or equivalent server-rendered.
- Don't introduce in-GUI image editing (crop, color, retouch). Generate-from-scratch only.
- Don't auto-publish images to social / external surfaces. Distribution is arthor-ai's job (or arthor-content's, post-launch).
- Don't build for multi-tenant scaling in v1. Justin-only admin GUI.
- Don't introduce LLM-as-judge for quality scoring. Human review in v1; revisit post-launch if it becomes a bottleneck.
- Don't build pack-level brand-coherence enforcement across multiple sites of the same business. One run = one site = one pack.
- Don't store generated images that are never used. The site-build pipeline writes the final URL into source; if a slot is replaced before site-build completes, the prior generation gets `status='superseded'` and rotates out per retention rules.
- Don't introduce a synthetic-AI-guru aesthetic (per `synthesis/gtm-heygen-direction.md` §1). Style profiles must feel like real brands.

---

## Repo conventions to match

- **`system.yaml` at repo root** matching the arthor-systemmap schema (see `~/arthor-systemmap/schema/system.example.yaml`). Required for arthor-systemmap to track this service.
- **`AGENTS.md` at repo root** describing the service for future agents (one paragraph + module list).
- **Match `arthor-seo-service` patterns** for project structure (`app/`, `db/migrations/`, `tests/`, etc.). Don't reinvent unless there's a reason.
- **Skills directory** if the service introduces reusable patterns: `skills/` at repo root, `SKILL.md` per skill. Style-profile resolution is a likely candidate skill.
- **No Inngest here.** Long-running work uses FastAPI background tasks or a simple worker queue. Callbacks to arthor-ai's Inngest happen via HTTP from this service.

---

## Open questions for the implementing agent to flag

Don't decide alone — flag in PR:

1. **Exact model names at build time.** Both providers' image models evolve fast. Pick current stable, record in `external_media_assets.model_version`, document in README.
2. **Payload schema versioning.** v1 schema will evolve. Suggest `payload_version: "1.0"` on every payload + a migration path for v1.1 changes.
3. **R2 bucket layout.** `arthor-image-service/<site_id>/<run_id>/<slot_id>/<asset_id>.<ext>`? Or flat by `agent_run_id`? Implementing agent picks; document.
4. **Retention policy for superseded assets.** v1 default is 30 days then cold storage. Justin may want longer for evidence trail.
5. **Whether to cache identical-payload requests across sites.** Probably not — each site's brand is unique, and the cache hit rate would be ~0. But if a cost-spike happens, this becomes the first lever.
6. **Style profile authoring UX.** Edit via the GUI form, or just stored from the resolved version? v1 default: read-only display in GUI; manual override via "fork run with edited style profile."
7. **Reference-image conditioning storage.** Once a hero is the "reference," it gets read repeatedly during pack generation. Cache the bytes locally or re-fetch from R2 each time? Performance call.
8. **Whether the Cursor site-build agent needs new tooling to emit the payload.** Probably yes — a new `RunImagePack` skill in `seo-core/skills/` that the Cursor agent invokes. Out of scope for this packet but worth flagging so arthor-ai gets the skill added in parallel.
9. **Background task strategy.** FastAPI `BackgroundTasks` vs. external worker queue (Celery? RQ? simple asyncio?). Pros/cons + recommendation. Suggest starting with `BackgroundTasks` and only adding a queue if concurrency limits bite.
10. **Failure handling for partial packs.** If 9 of 10 slots succeed and 1 fails, does the callback say `status=partial`? Or retry the failed slot automatically? v1 default: `status=partial`, surface in GUI, Justin manually retries the failed slot.

---

## How to know you're done

Run a real test build end-to-end. The Cursor site-build pipeline emits a payload. arthor-image-service generates the pack. The site ships with the generated images. Justin opens the site in a browser and the images look like a real brand's image set — not generic stock, not AI slop, not inconsistent across pages.

Then open the GUI. Show the run. Show every slot's prompt, every provider response, every cost. Fork-and-rerun one slot with a new seed; see the new variant; promote it. Cost rolls up correctly.

If that loop works end-to-end and the output is something Justin would proudly hand to a paying customer, v1 is done.

---

## Update log

- **2026-05-16 (initial)** — Drafted as W21 in `roadmap/phase-plan.md`. v1 = contextual asset-pack generation from Cursor-emitted payload. Providers: new OpenAI image model + Google nano-banana (Gemini 2.5 Flash Image). Separate FastAPI repo `arthor-image-service` mirroring arthor-seo-service pattern. Pre-launch quality workstream; launch can ship with placeholders if W21 slips, but quality bar suffers.
