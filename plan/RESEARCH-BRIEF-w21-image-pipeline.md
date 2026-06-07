# W21 Image Pipeline — Research Brief (External DR #4)

> **Audience:** External deep-research team with **no repo access**.  
> **Attach to:** DR Prompt #4 — *Production patterns for cohesive AI image packs across multi-page SMB sites*.  
> **Status:** Snapshot as of 2026-06-07. Service built on branch `pod/w21-track-a`; arthor-ai emitter + callback-or-poll wired on main (T2/T3 landed).

---

## 1. What Arthor is building

Arthor is an AI-native website builder for SMB local-service businesses (15–30 pages). During the automated site-build pipeline, **arthor-ai** calls **arthor-image-service** to generate a **cohesive image pack** — 8–12 contextual photos/graphics that share one resolved visual style (palette, lighting, register) across the homepage hero, section accents, service cards, and Open Graph image.

The service does **not** touch customer repos or send customer-facing messages. It:

1. Accepts a signed `PayloadV1` JSON body.
2. Generates images hero-first, conditioning later slots on the hero where the provider supports reference images.
3. Uploads to Cloudflare R2.
4. Writes rows to shared Postgres (`agent_runs`, `external_media_assets`, `tool_calls`, `image_request_payloads`).
5. POSTs an HMAC-signed completion callback to arthor-ai.
6. Exposes an operator inspector GUI for pack review, slot fork-rerun, and cost rollup.

**Quality bar:** Pack must look like one art-directed shoot, not stock-photo collage. Justin's inspector verdict is the v1 acceptance signal; automated palette-variance check tags drift but does not block callback.

---

## 2. PayloadV1 — MVP field list

`payload_version: "1.0"` is the binding contract. Pydantic models in the service are runtime authority; arthor-ai emits JSON matching this shape.

### Required for validation (strict MVP)

If arthor-ai's first emitter cut cannot fill the rich contract, these fields **must** be present or the service returns `400`:

| Group | Required fields |
|-------|-----------------|
| Top-level | `payload_version`, `site_id`, `callback_url`, `idempotency_key` (≥ 8 chars) |
| `business` | `industry`, `icp_summary`, `value_prop` |
| `location` | `mode` (`local` \| `regional` \| `national`), `country` (ISO 3166-1 alpha-2) |
| `brand_voice` | `tone` |
| `brand_visual` | `palette.light.{primary, secondary, background, foreground}`, `register_default` (`photographic` \| `illustrated` \| `mixed`) |
| `style_profile_hint` | `lighting`, `do_not` (non-empty list) |
| Each `slots[]` item | `slot_id`, `page`, `slot_kind`, `intent` (≥ 8 chars), `layout.dimensions.{w, h}`, `count` |

All other fields default via the deterministic style-profile resolver. The service returns `payload_completeness_score` (0.0–1.0) on acceptance and in `agent_runs.metadata` so the emitter can see how thin the payload was.

**Completeness score (plain English):** Weighted blend of "structural presence" checks (required MVP fields populated) and "discriminating richness" checks (proof points, service areas, copy context on slots, hero conditioning, provider hints, etc.). Score ≈ 0.35–0.45 for bare MVP; ≈ 0.75+ for a fully populated pack.

### Inline JSON example — 10-slot MVP+ pack

Typical local-service site (e.g. HVAC contractor). Shows all four primary slot kinds. Non-MVP fields included where they improve quality but are not strictly required.

```json
{
  "payload_version": "1.0",
  "idempotency_key": "build-2026-hvac-austin-01",
  "site_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "agent_run_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "callback_url": "https://app.arthor.example/api/integrations/arthor/image-pack-completed",

  "business": {
    "site_name": "Summit Comfort HVAC",
    "industry": "hvac-local-service",
    "icp_summary": "homeowners in Austin metro needing fast, trustworthy AC and heating repair",
    "value_prop": "same-day emergency service with transparent flat-rate pricing",
    "proof_points": ["licensed since 2008", "4.9 Google rating"],
    "forbidden_subjects": ["competitor logos", "medical claims"],
    "priority_services": ["AC repair", "furnace install", "duct cleaning"]
  },

  "location": {
    "mode": "local",
    "city": "Austin",
    "region": "TX",
    "country": "US",
    "service_areas": ["Austin", "Round Rock", "Cedar Park"]
  },

  "brand_voice": {
    "tone": "calm, competent, neighborly",
    "notes": ["avoid fear-based copy"],
    "style_direction": "clean trades professionalism",
    "reference_likes": [],
    "do_not": ["no stock handshakes", "no clip art"]
  },

  "brand_visual": {
    "palette": {
      "light": {
        "primary": "#0B3D5C",
        "secondary": "#E8A838",
        "background": "#FFFFFF",
        "foreground": "#1A1A1A",
        "muted": "#6B7280"
      },
      "dark": {
        "primary": "#3B82C4",
        "secondary": "#E8A838",
        "background": "#0F172A",
        "foreground": "#F8FAFC",
        "muted": "#94A3B8"
      }
    },
    "typography": { "sans": "Inter", "heading": "Inter" },
    "register_default": "photographic",
    "logo_asset_id": null,
    "customer_reference_assets": []
  },

  "style_profile_hint": {
    "lighting": "soft Texas morning light through windows, not harsh noon sun",
    "camera_language": "35mm documentary feel, shallow depth of field on details",
    "composition_rules": ["leave negative space on left third for headline overlay"],
    "color_grading": "slightly warm, muted saturation",
    "texture": "clean, low noise",
    "era_mood": null,
    "do_not": ["no neon", "no overlay text baked into image", "no watermarks"],
    "must_include": ["realistic residential interiors or equipment close-ups"]
  },

  "pack": {
    "pack_id": "summit-comfort-launch-v1",
    "base_seed": 42001,
    "slot_order": [
      "home_hero",
      "home_services_accent",
      "home_trust_accent",
      "services_hero",
      "about_accent",
      "card_ac_repair",
      "card_furnace",
      "card_duct",
      "og_default",
      "contact_accent"
    ],
    "reference_policy": {
      "hero_slot_id": "home_hero",
      "condition_non_hero_slots_on_hero": true,
      "allow_user_reference_conditioning": false
    },
    "default_provider_hint": "google_nano_banana"
  },

  "slots": [
    {
      "slot_id": "home_hero",
      "ordinal": 0,
      "page": "/",
      "route": { "name": "home", "template": "home", "target_keyword": "hvac repair austin" },
      "section": { "section_type": "hero", "section_instance_id": "home-hero-1" },
      "slot_kind": "hero",
      "intent": "establish trust and calm competence at first scroll on homepage",
      "copy_context": {
        "page_h1": "Austin's Trusted HVAC Team",
        "section_heading": null,
        "body_excerpt": "Same-day AC repair with flat-rate pricing.",
        "cta_label": "Schedule Service"
      },
      "subject": {
        "primary": "technician inspecting residential AC unit, professional uniform",
        "setting": "suburban home utility area",
        "props": ["tool bag", "digital gauge"],
        "people_policy": { "faces_allowed": false, "notes": "show hands/back only if people present" }
      },
      "camera": { "framing": "wide", "angle": "eye-level", "lens_feel": "35mm" },
      "lighting_mood": { "mood_tokens": ["trustworthy", "warm"], "contrast": "medium" },
      "layout": {
        "aspect_ratio": "16:9",
        "dimensions": { "w": 1920, "h": 1080 },
        "safe_area": { "mode": "start", "inset_pct": 12 },
        "overlay_text_risk": true
      },
      "count": 1,
      "provider_hint": "google_nano_banana",
      "condition_on_slot_id": null
    },
    {
      "slot_id": "home_services_accent",
      "ordinal": 1,
      "page": "/",
      "route": { "name": "home", "template": "home", "target_keyword": null },
      "section": { "section_type": "services", "section_instance_id": "home-svc-grid" },
      "slot_kind": "section_accent",
      "intent": "visual bridge into the three core service lines without repeating hero",
      "copy_context": { "page_h1": null, "section_heading": "Our Services", "body_excerpt": null, "cta_label": null },
      "subject": { "primary": "abstract warm gradient with subtle equipment silhouette", "setting": "studio", "props": [], "people_policy": { "faces_allowed": false, "notes": null } },
      "camera": { "framing": "medium", "angle": "eye-level", "lens_feel": "50mm" },
      "lighting_mood": { "mood_tokens": ["calm"], "contrast": "low" },
      "layout": { "aspect_ratio": "4:3", "dimensions": { "w": 1200, "h": 900 }, "safe_area": { "mode": "all", "inset_pct": 8 }, "overlay_text_risk": false },
      "count": 1,
      "provider_hint": "google_nano_banana",
      "condition_on_slot_id": "home_hero"
    },
    {
      "slot_id": "home_trust_accent",
      "ordinal": 2,
      "page": "/",
      "route": { "name": null, "template": "home", "target_keyword": null },
      "section": { "section_type": "testimonials", "section_instance_id": "home-trust" },
      "slot_kind": "section_accent",
      "intent": "support social proof section with approachable residential context",
      "copy_context": { "page_h1": null, "section_heading": "Neighbors Recommend Us", "body_excerpt": null, "cta_label": null },
      "subject": { "primary": "well-maintained Austin suburban street, house exterior", "setting": "residential neighborhood", "props": ["shade trees"], "people_policy": { "faces_allowed": false, "notes": null } },
      "camera": { "framing": "wide", "angle": "eye-level", "lens_feel": "35mm" },
      "lighting_mood": { "mood_tokens": ["neighborly"], "contrast": "medium" },
      "layout": { "aspect_ratio": "16:9", "dimensions": { "w": 1600, "h": 900 }, "safe_area": { "mode": "center", "inset_pct": 10 }, "overlay_text_risk": false },
      "count": 1,
      "provider_hint": null,
      "condition_on_slot_id": "home_hero"
    },
    {
      "slot_id": "services_hero",
      "ordinal": 3,
      "page": "/services",
      "route": { "name": "services", "template": "service_index", "target_keyword": "hvac services austin" },
      "section": { "section_type": "hero", "section_instance_id": "svc-hero" },
      "slot_kind": "hero",
      "intent": "anchor the services index with equipment detail photography",
      "copy_context": { "page_h1": "HVAC Services", "section_heading": null, "body_excerpt": null, "cta_label": "Get a Quote" },
      "subject": { "primary": "close-up of clean condenser coils and fins", "setting": "outdoor unit pad", "props": [], "people_policy": { "faces_allowed": false, "notes": null } },
      "camera": { "framing": "close", "angle": "low", "lens_feel": "85mm" },
      "lighting_mood": { "mood_tokens": ["precise"], "contrast": "high" },
      "layout": { "aspect_ratio": "16:9", "dimensions": { "w": 1920, "h": 1080 }, "safe_area": { "mode": "end", "inset_pct": 15 }, "overlay_text_risk": true },
      "count": 1,
      "provider_hint": null,
      "condition_on_slot_id": "home_hero"
    },
    {
      "slot_id": "about_accent",
      "ordinal": 4,
      "page": "/about",
      "route": { "name": "about", "template": "about", "target_keyword": null },
      "section": { "section_type": "story", "section_instance_id": "about-intro" },
      "slot_kind": "section_accent",
      "intent": "humanize the company story with workshop/van context, no faces",
      "copy_context": { "page_h1": "About Summit Comfort", "section_heading": null, "body_excerpt": "Family-owned since 2008.", "cta_label": null },
      "subject": { "primary": "branded service van in driveway, logo area blurred", "setting": "residential driveway", "props": ["ladder rack"], "people_policy": { "faces_allowed": false, "notes": null } },
      "camera": { "framing": "medium", "angle": "eye-level", "lens_feel": "35mm" },
      "lighting_mood": { "mood_tokens": ["authentic"], "contrast": "medium" },
      "layout": { "aspect_ratio": "4:3", "dimensions": { "w": 1200, "h": 900 }, "safe_area": { "mode": "all", "inset_pct": 8 }, "overlay_text_risk": false },
      "count": 1,
      "provider_hint": null,
      "condition_on_slot_id": "home_hero"
    },
    {
      "slot_id": "card_ac_repair",
      "ordinal": 5,
      "page": "/services/ac-repair",
      "route": { "name": "ac-repair", "template": "service_detail", "target_keyword": "ac repair austin" },
      "section": { "section_type": "card", "section_instance_id": "svc-card-1" },
      "slot_kind": "card",
      "intent": "thumbnail for AC repair service card in grids and links",
      "copy_context": { "page_h1": "AC Repair", "section_heading": null, "body_excerpt": null, "cta_label": "Book Now" },
      "subject": { "primary": "thermostat on wall beside vent grille", "setting": "living room", "props": [], "people_policy": { "faces_allowed": false, "notes": null } },
      "camera": { "framing": "close", "angle": "eye-level", "lens_feel": "50mm" },
      "lighting_mood": { "mood_tokens": ["comfort"], "contrast": "low" },
      "layout": { "aspect_ratio": "1:1", "dimensions": { "w": 800, "h": 800 }, "safe_area": { "mode": "all", "inset_pct": 5 }, "overlay_text_risk": false },
      "count": 1,
      "provider_hint": null,
      "condition_on_slot_id": "home_hero"
    },
    {
      "slot_id": "card_furnace",
      "ordinal": 6,
      "page": "/services/furnace-install",
      "route": { "name": "furnace-install", "template": "service_detail", "target_keyword": "furnace installation austin" },
      "section": { "section_type": "card", "section_instance_id": "svc-card-2" },
      "slot_kind": "card",
      "intent": "thumbnail for furnace install card consistent with pack palette",
      "copy_context": { "page_h1": "Furnace Installation", "section_heading": null, "body_excerpt": null, "cta_label": null },
      "subject": { "primary": "modern furnace unit in basement utility room", "setting": "basement", "props": ["ductwork"], "people_policy": { "faces_allowed": false, "notes": null } },
      "camera": { "framing": "medium", "angle": "eye-level", "lens_feel": "35mm" },
      "lighting_mood": { "mood_tokens": ["warm"], "contrast": "medium" },
      "layout": { "aspect_ratio": "1:1", "dimensions": { "w": 800, "h": 800 }, "safe_area": { "mode": "all", "inset_pct": 5 }, "overlay_text_risk": false },
      "count": 1,
      "provider_hint": null,
      "condition_on_slot_id": "home_hero"
    },
    {
      "slot_id": "card_duct",
      "ordinal": 7,
      "page": "/services/duct-cleaning",
      "route": { "name": "duct-cleaning", "template": "service_detail", "target_keyword": "duct cleaning austin" },
      "section": { "section_type": "card", "section_instance_id": "svc-card-3" },
      "slot_kind": "card",
      "intent": "thumbnail for duct cleaning service card",
      "copy_context": { "page_h1": "Duct Cleaning", "section_heading": null, "body_excerpt": null, "cta_label": null },
      "subject": { "primary": "ceiling vent with soft airflow implication", "setting": "interior hallway", "props": [], "people_policy": { "faces_allowed": false, "notes": null } },
      "camera": { "framing": "close", "angle": "low", "lens_feel": "50mm" },
      "lighting_mood": { "mood_tokens": ["fresh"], "contrast": "low" },
      "layout": { "aspect_ratio": "1:1", "dimensions": { "w": 800, "h": 800 }, "safe_area": { "mode": "all", "inset_pct": 5 }, "overlay_text_risk": false },
      "count": 1,
      "provider_hint": null,
      "condition_on_slot_id": "home_hero"
    },
    {
      "slot_id": "og_default",
      "ordinal": 8,
      "page": "/",
      "route": { "name": "home", "template": "home", "target_keyword": null },
      "section": { "section_type": "meta", "section_instance_id": "og-image" },
      "slot_kind": "og",
      "intent": "social share preview with readable brand presence at small sizes",
      "copy_context": { "page_h1": "Summit Comfort HVAC", "section_heading": null, "body_excerpt": "Same-day AC repair in Austin.", "cta_label": null },
      "subject": { "primary": "simplified hero composition, bold negative space center", "setting": "abstract brand environment", "props": [], "people_policy": { "faces_allowed": false, "notes": null } },
      "camera": { "framing": "wide", "angle": "eye-level", "lens_feel": "unspecified" },
      "lighting_mood": { "mood_tokens": ["bold"], "contrast": "medium" },
      "layout": { "aspect_ratio": "1.91:1", "dimensions": { "w": 1200, "h": 630 }, "safe_area": { "mode": "center", "inset_pct": 15 }, "overlay_text_risk": true },
      "count": 1,
      "provider_hint": "openai_image",
      "condition_on_slot_id": "home_hero"
    },
    {
      "slot_id": "contact_accent",
      "ordinal": 9,
      "page": "/contact",
      "route": { "name": "contact", "template": "contact", "target_keyword": null },
      "section": { "section_type": "cta", "section_instance_id": "contact-banner" },
      "slot_kind": "section_accent",
      "intent": "reassuring visual for contact CTA band",
      "copy_context": { "page_h1": "Contact Us", "section_heading": "We're here today", "body_excerpt": null, "cta_label": "Call Now" },
      "subject": { "primary": "dispatcher headset on desk beside schedule clipboard", "setting": "office desk", "props": ["pen", "calendar"], "people_policy": { "faces_allowed": false, "notes": "hands only" } },
      "camera": { "framing": "medium", "angle": "high", "lens_feel": "50mm" },
      "lighting_mood": { "mood_tokens": ["responsive"], "contrast": "medium" },
      "layout": { "aspect_ratio": "16:9", "dimensions": { "w": 1600, "h": 900 }, "safe_area": { "mode": "start", "inset_pct": 10 }, "overlay_text_risk": true },
      "count": 1,
      "provider_hint": null,
      "condition_on_slot_id": "home_hero"
    }
  ]
}
```

---

## 3. Slot types (v1)

Four primary kinds drive the SMB pack. The contract also allows `portrait` and `background` for future use; v1 packs use the four below.

| `slot_kind` | Role | Typical count per site | Typical dimensions | Notes |
|-------------|------|------------------------|-------------------|-------|
| **`hero`** | Full-bleed page headers; sets pack visual anchor | 1–2 (home + key landing) | 16:9 @ 1920×1080 | Generated **first**; other slots may condition on hero bytes |
| **`section_accent`** | Section backgrounds, trust bands, story blocks | 3–5 | 16:9 or 4:3 | Often `condition_on_slot_id` → hero; `overlay_text_risk: true` when headline sits on image |
| **`card`** | Service grid thumbnails, link cards | 2–4 | 1:1 @ 800×800 | Smaller crop; must stay palette-consistent with hero |
| **`og`** | Open Graph / social preview | 1 | 1.91:1 @ 1200×630 | Often routed to OpenAI for text-heavy clarity; still conditioned on hero palette |

**Slot ID convention (arthor-ai emitter):**

- Home hero: `home_hero`
- Per-route accents: `page_{ordinal}_accent` (ordinal 0-based on sitemap order)
- Cards: derived from service routes (e.g. `card_ac_repair`)
- OG: `og_default`

**Cap:** RunImagePack skill caps at **10 sitemap-derived slots** minimum; full packs target **8–12** including cards and OG.

**People policy:** Default `faces_allowed: false` for YMYL/trades; `people_policy` is required per slot. Style-profile resolver merges `do_not` from brand + hint + forbidden subjects.

---

## 4. v1 image providers

Two concrete providers implement a shared `ImageProvider` protocol (`generate_single`, optional reference-image conditioning).

| Provider key | Product name | Pinned `model_version` | Strengths in pack | Weaknesses |
|--------------|--------------|------------------------|-------------------|------------|
| `google_nano_banana` | **Gemini 2.5 Flash Image** | `gemini-2.5-flash-image` | Pack coherence, photographic SMB scenes, reference conditioning from hero | Model ID churn; text-in-image less reliable |
| `openai_image` | **OpenAI Images (GPT Image)** | `gpt-image-1` | OG/social crops, text-adjacent clarity | Seed is best-effort only (`determinism: "best-effort"`); weaker cross-slot consistency vs Gemini |

**Default routing policy:**

- Pack default: `google_nano_banana` for hero + section + card slots (consistency-sensitive).
- Per-slot `provider_hint` override (e.g. `og` → `openai_image`).
- One auto-retry per failed slot with a new seed before marking slot failed.
- Marginal API cost table (pinned at build): ~**4–8 USD cents** per image depending on output dimensions (1024² → 4¢; 1536² → 8¢).

**Not in v1 scope:** FLUX.2 multi-reference, Midjourney, self-hosted SD, video generation. DR should compare these two v1 choices against FLUX.2 for **pack coherence per dollar**.

---

## 5. Pack size: 8–12 slots

| Composition | Slots | When used |
|-------------|-------|-----------|
| **Minimum viable** | 6–8 | Single-location microsite: `home_hero` + 2 section accents + 2 cards + `og_default` + 1 contact accent |
| **Standard launch pack** | 9–10 | 15–30 page SMB site (example JSON above) |
| **Full pack** | 11–12 | Multi-service depth: extra route heroes, additional cards, second OG variant |

**Hero-first ordering:** `pack.slot_order` lists slot IDs; hero ID in `pack.reference_policy.hero_slot_id` is always processed first. Non-hero slots with `condition_on_slot_id` receive hero bytes as reference input when the provider supports it (`supports_reference_image`).

**Deterministic QA before callback (already implemented):**

- Palette-variance check: dominant colors vs resolved `StyleProfile.palette` → tags drift in metadata, does not block ship.
- Per-slot aspect/dimension enforcement at generation time.
- Provider safety filters pass through (no separate NSFW model in v1).

**DR should research additional gates:** inter-slot embedding similarity thresholds, rejection/resample policy, minimum slot set that still reads "cohesive" to SMB buyers.

---

## 6. Callback-or-poll flow (plain English)

This is an **async generate-then-notify** pattern. The HTTP request returns immediately; work happens in a background task.

### Step-by-step

1. **Emit.** During site build (after page composition, before verify), arthor-ai assembles `PayloadV1` with a stable `idempotency_key` (e.g. hash of `site_id` + build attempt).

2. **Submit.** arthor-ai `POST`s the JSON to `https://<image-service>/images/asset-pack/generate` with HMAC header `X-Arthor-Signature: sha256=<hex>` over the raw body.

3. **Accept.** Image-service validates payload, checks idempotency:
   - **New key** → `202 Accepted` + `{ "agent_run_id": "<uuid>", "status": "accepted" }`
   - **Duplicate key** → `200 OK` + existing `agent_run_id` (no duplicate generation)

4. **Wait (arthor-ai).** Build pipeline calls Inngest `step.waitForEvent` for `image-pack-completed`, with a timeout (tens of minutes).

5. **Generate (background).** Image-service worker:
   - Resolves one `StyleProfile` from brand + hint + first-slot intent
   - Generates hero → uploads to R2 → writes `external_media_assets` + `tool_calls`
   - Generates remaining slots (conditioned on hero where supported)
   - Rolls up `total_cost_cents` on `agent_runs`

6. **Callback (fast path).** On completion, image-service `POST`s to the payload's `callback_url` (default: arthor-ai `/api/integrations/arthor/image-pack-completed`) with HMAC-signed body:

```json
{
  "agent_run_id": "<uuid>",
  "site_id": "<uuid>",
  "status": "complete",
  "assets": [
    {
      "slot_id": "home_hero",
      "asset_id": "<uuid>",
      "r2_url": "https://cdn.example/arthor-image-service/<site_id>/<asset_id>.webp",
      "width": 1920,
      "height": 1080,
      "provider": "google_nano_banana",
      "model_version": "gemini-2.5-flash-image",
      "seed": 42001,
      "cost_cents": 6
    }
  ],
  "total_cost_cents": 58,
  "duration_seconds": 47
}
```

`status` may be `complete` (all slots OK), `partial` (some slots failed after retry), or `failed`.

7. **Persist (arthor-ai).** Callback route verifies HMAC, writes URLs into `SiteSpec.images`, emits the Inngest event to unblock the build.

8. **Place (Cursor agent).** `RunImagePack` skill maps `slot_id` → `r2_url` into components via `data-image-slot` markers. No stock-photo backfill while pending or after partial failure.

### Poll fallback (callback lost)

`siteBuildPipeline` uses `retries: 0` — a dropped callback would otherwise fail a build whose images already generated and were billed.

**Mitigation — callback-or-poll:**

- Callback remains the **fast path**.
- If `waitForEvent` times out, arthor-ai polls `GET /images/asset-pack/{agent_run_id}` (HMAC-authenticated) until status is terminal (`complete` \| `partial` \| `failed`) or a poll budget expires.
- Poll response mirrors callback asset list; same persistence path.
- Re-submitting `POST /images/asset-pack/generate` with the same `idempotency_key` returns the existing run — safe to retry emit without double-billing generation.

**Do not** replace this with a shared DB queue or cross-service polling of Postgres from arthor-ai — callback + status endpoint is the chosen boundary.

---

## 7. COGS context — $150–250/site/year

Arthor's **total annual COGS target per customer site** is **$150–250/year** (decided R8/R16). That envelope covers **all** metered categories: LLM inference, Cursor build runs, DataForSEO, **image packs**, future ads API, crawl/storage — for a typical **15–30 page site + ~1 optimization action/day + edits**.

### Image line item (context for DR deliverable #5)

Image generation must fit **inside** that envelope, not consume it alone.

| Event | Slots | Est. API cost (v1 rates) |
|-------|-------|--------------------------|
| Initial site-build pack | 8–12 | ~$0.40–$0.96 (4–8¢ × 10 slots) |
| Auto-retry (~10% slots fail once) | +1–2 | ~$0.04–$0.16 |
| Operator fork-rerun (inspector) | 1–3 slots/year | ~$0.04–$0.24 |
| Annual refresh pack (optional) | 6–8 partial | ~$0.24–$0.64 |

**Rough annual image API spend:** ~**$1–3/site/year** at current provider list prices, assuming one full pack at build + light regeneration. Even aggressive refresh (quarterly 10-slot packs) stays under **~$15/site/year** API marginal cost.

**Implication for DR:** The $150–250 constraint is dominated by LLM + data + build compute, not raw image API cents. Research should still answer:

- **Minimum viable pack** (6–8 slots) vs **full pack** (11–12) for perceived cohesion on SMB sites.
- Whether fewer slots + higher regen rate beats full pack at build.
- Provider $/accepted-pack (including retry waste) at standard and MVP sizes.

Budget **gates** (R16, separate DR #5) will meter overflow with user warnings; image cost rolls up via `tool_calls.cost_cents` → `agent_runs.cost_cents`.

---

## 8. Metadata ledger (per asset)

Each generated image becomes one `external_media_assets` row plus one `tool_calls` row.

**`external_media_assets` (per asset):**

| Field | Purpose |
|-------|---------|
| `id` | UUID primary key |
| `site_id` | Tenant scope |
| `agent_run_id` | FK to pack run |
| `slot_id` | Matches payload slot |
| `status` | `pending` → `generated` → `uploaded` (or `failed`) |
| `r2_key` / public URL | `arthor-image-service/<site_id>/<asset_id>.<ext>` |
| `width`, `height` | Output dimensions |
| `provider` | `openai_image` \| `google_nano_banana` |
| `model_version` | Pinned string at build time |
| `seed` | Integer used for attempt |
| `prompt_hash` | Hash of resolved slot prompt (not raw prompt in v1 customer path) |
| `metadata` jsonb | Style tags, palette drift flags, determinism level |
| `superseded_by` | FK when slot regenerated |

**`tool_calls` (per provider invocation):**

| Field | Purpose |
|-------|---------|
| `cost_cents` | Marginal USD cents |
| `provider`, `model_version` | Rollup dimensions |
| `latency_ms`, `status` | SLO / failure tracking |

**`image_request_payloads`:** Full canonical payload JSON + `payload_hash` + `idempotency_key` for replay/rerun from inspector.

---

## 9. Style profile (pack-level coherence)

Before any slot generates, a deterministic resolver (with optional single LLM fallback) produces one **`StyleProfile`** per pack:

- Merges `brand_visual.palette`, `brand_voice.do_not`, `style_profile_hint`, `business.forbidden_subjects`
- Persisted on `agent_runs.metadata.style_profile`
- Every slot prompt is built from the same profile + slot-local `intent`, `subject`, `copy_context`, `camera`, `lighting_mood`, `layout.safe_area`

**DR deliverable #1** maps directly to this contract: brand tokens + reference hero → shared palette/lighting/mood across 8–12 slots.

---

## 10. What DR #4 should produce (checklist)

1. **Style-profile / brand-token contract** — validate or extend the resolver inputs in §9 for 8–12 slot SMB packs.
2. **Deterministic QA gates** — palette match, inter-image similarity, aspect/resolution, safety; recommend thresholds and pass/fail vs tag-only.
3. **Provider comparison** — OpenAI `gpt-image-1` + Gemini `gemini-2.5-flash-image` vs FLUX.2 multi-reference; **$/accepted-pack** at 8-slot and 12-slot sizes including ~10% retry waste.
4. **Metadata ledger** — confirm §8 fields sufficient for audit, regen, and cost rollup.
5. **MVP pack size** — recommend minimum slot set vs full generation that preserves cohesion within the **$150–250/site/yr total COGS** envelope (images ≈ $1–15/yr API marginal at v1 cadence).

**Non-goals:** Self-hosted GPU clusters, Midjourney bot integration, video/avatar generation.

---

## 11. Key references (for Arthor operators, not DR)

| Artifact | Location |
|----------|----------|
| Payload ADR | `plan/adr/0010-payload-contract-v1.md` |
| Architecture plan | `plan/plan.md` |
| Dev E2E ledger | `agent-control/dev-launch-ledger.md` |
| RunImagePack skill | `seo-core/skills/RunImagePack/SKILL.md` |
| Launch handoff | `arthor-brainstorm/roadmap/arthor-image-service-launch-handoff.md` |
