# Hero candidates — consumer contract (arthor-ai)

- **Audience:** arthor-ai builder integration (`HeroTriad`, `HeroPreviewFrame`)
- **Date:** 2026-06-11
- **Branch:** `pod/w21-h-hero-candidates`
- **Related ADRs:** [`0011`](adr/0011-hero-candidates-v2.md) (copy overlay v2), [`0012`](adr/0012-hero-openai-only-and-visual-strategy.md) (OpenAI-only + visual strategy)

---

## Summary

Image-service generates **exactly 3 homepage hero images** (search / story / offer tones) from a narrow builder payload. Flow:

1. `POST /images/hero-candidates/generate` → `202` + `agent_run_id`
2. Poll `GET /images/hero-candidates/{run_id}` until `status` is terminal
3. Optional: `POST /images/hero-candidates/regenerate-variant` to edit one variant; poll the **new** `agent_run_id`

**Auth:** HMAC body signature on every request (`X-Arthor-Signature`). Shared secret: `FASTAPI_ARTHOR_SHARED_SECRET`.

**Provider:** Heroes always use **OpenAI** (`openai_image` / `gpt-image-2`). `default_provider_hint` is accepted on ingress but **forced to `openai_image`** in the worker.

**Ingress ≠ provider prompt:** Headlines, subheads, CTAs, and nav labels are **never** sent verbatim to the image provider. They drive preview-frame geometry and run metadata only. Provider text is compiled server-side (`metadata.hero_provider_prompts[]`).

---

## Endpoints

### `POST /images/hero-candidates/generate`

| | |
|---|---|
| **Auth** | HMAC over raw JSON body |
| **Success** | `202` `{ "agent_run_id": "<uuid>", "status": "accepted" }` |
| **Idempotent replay** | `200` `{ "agent_run_id": "<uuid>", "status": "<poll status>", "idempotent_replay": true }` — same body + `idempotency_key` |
| **Errors** | `400` validation, `401` bad/missing signature, `503` database unavailable |

### `GET /images/hero-candidates/{run_id}`

| | |
|---|---|
| **Auth** | HMAC over empty body (`sign_body(secret, b"")`) |
| **Success** | `200` poll body (below) |
| **Errors** | `401`, `404` run not found, `503` |

Poll reflects **database asset state only** — not live OpenAI/Google job status.

#### Poll response

```jsonc
{
  "agent_run_id": "uuid",
  "status": "pending | running | complete | partial | failed",
  "urls": [
    {
      "variant_index": 0,
      "url": "https://…",           // browser-facing URL
      "tone_angle": "search",       // when present on asset metadata
      "headline": "…",              // echo from request — preview only
      "subhead": "…",
      "failure_mode": "palette_drift",  // optional QA / provider flag
      "scene_archetype": "threshold_invitation",  // optional — U9 index-driven scene
      "style_profile_fragment": { "lighting": "…", "color_grading": "…" },  // optional — corpus pick export
      "corpus_backed": true         // optional — true when served from taste corpus
    }
  ],
  "error": "…"                      // only when status === "failed"
}
```

**Status mapping**

| `status` | Meaning |
|----------|---------|
| `pending` | Run started; no uploaded assets yet |
| `running` | At least one asset in progress; not all 3 uploaded |
| `complete` | All 3 variants uploaded |
| `partial` | Run finished (`ok`) but fewer than 3 uploaded |
| `failed` | Run failed or zero uploads |

`urls` includes **uploaded** assets only, sorted by `variant_index`. Images with QA flags are still returned — check `failure_mode` per URL.

Optional query on poll: `GET …/{run_id}?picked_variant_index=0` adds top-level `picked_variant` (same shape as one `urls[]` entry) for style export after builder pick.

**Regenerate-variant** always uses **live** OpenAI — no corpus path (user rejected corpus options).

### `POST /images/hero-candidates/regenerate-variant`

Regenerate **one** triad variant; supersedes the source asset on success.

| | |
|---|---|
| **Auth** | HMAC over raw JSON body |
| **Success** | `202` `{ "agent_run_id": "<uuid>", "new_asset_id": "<uuid>", "status": "accepted" }` |
| **Poll** | `GET /images/hero-candidates/{agent_run_id}` (same shape; expect one URL) |

#### Request body

```jsonc
{
  "asset_id": "uuid",                    // uploaded hero_candidate asset
  "edit_kind": "retry | tweak | reference | rescene",
  "new_seed": 42,                        // optional; default original_seed + 1
  "prompt_modifier": "warmer lighting",  // required for tweak
  "scene_archetype": "shared_joy",       // required for rescene (catalog id)
  "customer_reference_assets": [ … ]     // required for reference (same shape as ingress)
}
```

| `edit_kind` | Behavior |
|-------------|----------|
| `retry` | Same compiled prompt; seed bumped (`new_seed` or `original_seed + 1`) |
| `tweak` | Append `prompt_modifier` to compiled brief |
| `reference` | Replace ingress refs with `customer_reference_assets`; rebuild `reference_plan`; OpenAI edit when eligible |
| `rescene` | Override scene archetype for one variant; recompile |

**Errors:** `400` (`asset_must_be_uploaded`, `asset_not_hero_candidate`, `tweak_requires_prompt_modifier`, `reference_requires_customer_reference_assets`, `rescene_requires_scene_archetype`, …), `404` unknown asset, `401`, `503`.

---

## Request: `HeroCandidatesRequest`

Pydantic model: [`app/payload/hero_models.py`](../app/payload/hero_models.py). `extra: forbid` — unknown keys → `400`.

### Top-level fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `site_id` | uuid | yes | |
| `idempotency_key` | string (≥8) | yes | Stable per triad generation attempt |
| `business` | object | yes | See below |
| `location` | object | yes | See below |
| `brand_voice` | object | yes | See below |
| `brand_visual` | object | yes | Includes optional `customer_reference_assets` |
| `style_profile_hint` | object | yes | Drives resolved style profile |
| `variants` | array[3] | yes | Exactly 3 entries |
| `base_seed` | int | no | Default `42`; variant seeds = `base_seed + index` |
| `default_provider_hint` | `"openai_image"` \| `"google_nano_banana"` | no | **Ignored for generation** — worker forces OpenAI |
| `payload_version` | `"hero_candidates.1"` \| `"hero_candidates.2"` | no | Default `"hero_candidates.1"` |
| `hero_viewport` | `"desktop"` \| `"mobile"` | no | Default `"desktop"`; affects dimensions + safe zones |
| `generation_mode` | `"corpus"` \| `"live"` | no | Default **`"corpus"`** — builder style pick uses curated plates (no OpenAI). Use `"live"` for escape hatch / build-time gen. |
| `corpus_version` | string | no | Default `"1.0"` — pins corpus snapshot under `data/hero_taste_corpus/v1/` |
| `corpus_fallback` | `"live"` | no | When corpus missing for industry: default **400** (`corpus_not_available_for_industry`). Set `"live"` to fall back to OpenAI worker. |

### `business`

| Field | Type | Required |
|-------|------|----------|
| `site_name` | string | yes |
| `industry` | string | yes |
| `icp_summary` | string | yes |
| `value_prop` | string | yes |
| `proof_points` | string[] | no |
| `forbidden_subjects` | string[] | no |
| `priority_services` | string[] | no |

### `location`

| Field | Type | Required |
|-------|------|----------|
| `mode` | `"local"` \| `"regional"` \| `"national"` | yes |
| `country` | string (ISO 3166-1 alpha-2) | yes |
| `city` | string | no |
| `region` | string | no |
| `service_areas` | string[] | no |

### `brand_voice`

| Field | Type | Required |
|-------|------|----------|
| `tone` | string | yes |
| `notes` | string[] | no |
| `style_direction` | string | no |
| `reference_likes` | string[] | no |
| `do_not` | string[] | no |

### `brand_visual`

| Field | Type | Required |
|-------|------|----------|
| `palette` | `{ light: PaletteTone, dark: PaletteTone }` | yes |
| `typography` | `{ sans, heading }` | yes |
| `register_default` | `"photographic"` \| `"illustrated"` \| `"mixed"` | yes |
| `logo_asset_id` | string | no |
| `customer_reference_assets` | `CustomerReferenceAsset[]` | no |

**`PaletteTone`:** `primary`, `secondary`, `background`, `foreground`, `muted` (hex colors).

### `customer_reference_assets[]` (ingress)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `asset_id` | string | yes | Stable builder id |
| `role` | `"interior"` \| `"team"` \| `"product"` \| `"logo"` \| `"ambient"` | yes | Drives authenticity mode |
| `url` | https URL | yes | Fetched at generation time when edit-eligible |
| `palette_hex` | hex[] | no | |
| `usage_hint` | string | no | e.g. `match_lighting`, `preserve_likeness` |
| `note` | string | no | Operator note; not in provider prompt |
| `likeness_consent` | bool | no | Default `false`; **`team` refs require `true` for edit path** |

When refs are present, run metadata includes `reference_plan` (see below). Only the **first eligible** ref is passed to OpenAI edit today (`provider_uses_first_ref_only: true`).

### `style_profile_hint`

| Field | Type | Required |
|-------|------|----------|
| `lighting` | string | yes |
| `camera_language` | string | no |
| `composition_rules` | string[] | no |
| `color_grading` | string | no |
| `texture` | string | no |
| `era_mood` | string | no |
| `do_not` | string[] | no |
| `must_include` | string[] | no |

### `variants[]` (length 3)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `tone_angle` | `"search"` \| `"story"` \| `"offer"` | one of* | Preferred |
| `intent` | string (≥8) | one of* | Alternative to `tone_angle` |
| `headline` | string | yes | Preview + metadata; **not** in provider prompt |
| `subhead` | string | no | Same |
| `copy_metrics` | object | no | Derived when omitted (v2) |
| `copy_overlay` | object | no | v2 preview-frame copy |

\* Each variant requires **`tone_angle` or `intent`**.

**`copy_metrics`** (optional; never sent to provider):

| Field | Type | Default when derived |
|-------|------|----------------------|
| `headline_chars` | int | `len(headline)` |
| `has_subhead` | bool | subhead non-empty |
| `has_cta` | bool | `copy_overlay.primary_cta` present |
| `cta_chars` | int | length of primary CTA |
| `nav_count` | int | `len(copy_overlay.nav_labels)` |

**`copy_overlay`** (optional; stored on run as `hero_copy_overlay`; never in provider prompt):

| Field | Type |
|-------|------|
| `primary_cta` | string |
| `secondary_cta` | string |
| `supporting_text` | string |
| `nav_labels` | string[] |

---

## Server-side metadata (debug / inspector)

Not returned on poll unless noted. Useful for support and A/B lab.

### `hero_visual_strategy` (on generate run)

Resolved deterministically from `business`, `location`, `variants`, and reference roles — **no client override on generate**.

```jsonc
{
  "strategy_version": "1.0",
  "scene_catalog_version": "1.0",
  "authenticity_mode": "stylized | space_anchored | likeness_anchored",
  "industry_label": "dental",
  "variants": [
    {
      "variant_index": 0,
      "tone_angle": "search",
      "scene_archetype": "shared_joy",
      "authenticity_mode": "space_anchored"
    }
  ]
}
```

**Scene archetypes:** `shared_joy`, `confident_smile`, `threshold_invitation`, `threshold_relief`, `desk_side_guidance`, `environment_warmth`.

**Authenticity modes:** derived from reference roles — no refs → `stylized`; `interior`/`ambient` → `space_anchored`; `team` (+ consent) → `likeness_anchored`.

### `reference_plan` (when `customer_reference_assets` non-empty)

```jsonc
{
  "reference_plan_version": "1.0",
  "authenticity_mode": "space_anchored",
  "edit_enabled": true,
  "edit_asset_id": "ref-interior-1",
  "edit_path": "openai_edit",
  "provider_uses_first_ref_only": true,
  "assets": [
    {
      "asset_id": "…",
      "role": "interior",
      "url": "https://…",
      "usage_hint": "match_lighting",
      "note": "…",
      "likeness_consent": false,
      "edit_eligible": true
    }
  ],
  "warnings": []
}
```

After fetch, worker may patch `resolved`, `byte_len`, or disable edit on failure.

### `hero_provider_prompts[]`

Per-variant compiled provider text (`compiler_version` currently **3.0**):

`variant_index`, `tone_angle`, `hero_job`, `hero_viewport`, `scene_archetype`, `prompt`, `prompt_hash`, `seed_prompt_hash`, `compiler_version`, `industry_label`.

---

## `failure_mode` (poll `urls[]`)

Primary QA or provider label per uploaded asset. Omitted when checks pass.

| Value | Source |
|-------|--------|
| `rendered_ui` | Post-check: high edge density in top band |
| `rendered_text` | Post-check: text-like edges in left safe zone |
| `safe_zone_violation` | Post-check: safe zone too busy vs center |
| `palette_drift` | Brand palette variance check |
| `moderation_blocked` | Provider content policy |
| `provider_timeout` | Provider timeout |
| `provider_error` | Other provider failure |
| `stale_orphaned_run` | Worker orphan detection |
| `wrong_industry` | Reserved in enum |
| `posed_faces_violation` | Reserved in enum |
| `unknown` | Unclassified error |

**Auto-retry (internal):** On `rendered_text` or `safe_zone_violation`, worker retries once with `seed + 1` before finalizing. Poll still returns the last image; `failure_mode` reflects final QA.

Images with `failure_mode` are **still uploaded and returned** — builder may offer regenerate.

---

## arthor-ai mapping notes

| arthor-ai concern | image-service field |
|-------------------|---------------------|
| Triad tones | `variants[].tone_angle` |
| Preview headlines | `variants[].headline`, `subhead` |
| CTA / nav overlay | `variants[].copy_overlay` (+ derived `copy_metrics`) |
| Contract version | `payload_version: "hero_candidates.2"` |
| User-uploaded refs | `brand_visual.customer_reference_assets[]` |
| Single-variant retry | `POST …/regenerate-variant` with `edit_kind` |
| Mobile hero crop | `hero_viewport: "mobile"` |

**Do not send** raw provider prompts from arthor-ai. **Do not expect** headlines in compiled prompts (verify via inspector `/inspector/hero-ab` or run metadata).

### Builder vs build-time (seo-service boundary)

| Step | Mode | Owner |
|------|------|-------|
| **Builder hero triad (style pick)** | `generation_mode: "corpus"` (default) | image-service taste corpus — zero provider cost |
| **User rejects corpus / regenerate-variant** | live OpenAI | image-service worker |
| **Full site build asset pack** | live OpenAI | seo-service `asset_pack_plan` → arthor-ai merges → PayloadV1 on asset-pack routes |

Builder hero triad uses corpus mode. Full-site images at build use seo-service `asset_pack_plan` + arthor-ai merge → PayloadV1 live gen. **image-service does NOT read `asset_pack_plan`**; it receives merged PayloadV1 only on asset-pack routes.

After pick, merge poll `urls[].style_profile_fragment` into PayloadV1 `style_profile_hint` at asset-pack submit (arthor-ai responsibility — lighting / color_grading / composition_rules keys only).

---

## Example: minimal generate body

```json
{
  "site_id": "550e8400-e29b-41d4-a716-446655440000",
  "idempotency_key": "hero:550e8400:variant-set-abc",
  "payload_version": "hero_candidates.2",
  "hero_viewport": "desktop",
  "business": {
    "site_name": "Acme Dental",
    "industry": "dental",
    "icp_summary": "local families seeking preventive care",
    "value_prop": "gentle, modern dentistry",
    "proof_points": [],
    "forbidden_subjects": [],
    "priority_services": []
  },
  "location": { "mode": "local", "country": "US", "city": "Austin", "region": "TX", "service_areas": [] },
  "brand_voice": { "tone": "warm and reassuring", "notes": [], "style_direction": "", "reference_likes": [], "do_not": [] },
  "brand_visual": {
    "palette": {
      "light": { "primary": "#0A4B6F", "secondary": "#F4A261", "background": "#FFFFFF", "foreground": "#111111", "muted": "#999999" },
      "dark": { "primary": "#0A4B6F", "secondary": "#F4A261", "background": "#0A0A0A", "foreground": "#FAFAFA", "muted": "#666666" }
    },
    "typography": { "sans": "Inter", "heading": "Inter" },
    "register_default": "photographic",
    "customer_reference_assets": []
  },
  "style_profile_hint": {
    "lighting": "soft natural window light",
    "do_not": ["stock photo smiles"]
  },
  "variants": [
    {
      "tone_angle": "search",
      "headline": "Find a dentist you trust",
      "subhead": "Same-week appointments",
      "copy_overlay": { "primary_cta": "Book now", "nav_labels": ["Services", "About", "Contact"] }
    },
    { "tone_angle": "story", "headline": "Care that feels personal", "subhead": "A calm office" },
    { "tone_angle": "offer", "headline": "New patient exam", "subhead": "Transparent pricing" }
  ],
  "base_seed": 77
}
```

---

## Version history

| Version | Change |
|---------|--------|
| U10 corpus | Default `generation_mode: "corpus"`; optional poll fields `scene_archetype`, `style_profile_fragment`, `corpus_backed`; `picked_variant_index` query |
| U9 visual triad | Scene selection by `variant_index` (0–2), not `tone_angle`; compiler **3.4** |
| `hero_candidates.1` | Headline/subhead only |
| `hero_candidates.2` | `copy_metrics`, `copy_overlay` for preview-frame geometry |

Compiler **3.0** + visual strategy layer shipped on image-service; arthor-ai v2 payload remains backward compatible.
