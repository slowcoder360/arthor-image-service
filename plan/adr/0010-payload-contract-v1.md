# ADR 0010: Payload contract v1 (rich shape per Justin's redirect)

- Status: proposed
- Date: 2026-05-17

## Context

This is the highest-leverage ADR in v1, per Justin's intake redirect:

> "I want us to build out what we require the payload to include to get a high quality output."

Research subagent #12 surveyed arthor-ai's `SiteSpec` (`lib/site/spec.ts`) and found an order of magnitude more signal available than the packet's stub example. The packet's stub had `{site_id, callback_url, brand{industry, location, palette, voice, do_not}, style_profile_hint{lighting, register, mood, composition}, slots[]{slot_id, page, intent, dimensions, count}}` — too thin to drive 7-8 band quality.

Three layers of signal drive quality:
1. **Brand + business identity** (project.* fields, full brand tokens, location, seoConstraints)
2. **Slot-local narrative + layout** (route metadata, copy adjacency, composition constraints, safe-area / overlay-text flags, people policy)
3. **Pack-level rules** (resolved StyleProfile, hero-reference policy, deterministic seed)

## Options considered

- **A. Stub-and-grow** — start with the packet's stub, add fields as we discover the need. Pro: fast first iteration. Con: locks in a thin contract; every additive field requires a payload-version bump or "best-effort" parsing.
- **B. Rich contract from day one** — define the full v1 contract now per research #12. Pro: arthor-ai has a concrete target; the prompts have everything they need to land in the 7-8 band. Con: slower first iteration; some fields may turn out unused.
- **C. Pull from `sites.projectState` directly** — bypass the payload; this service reads arthor-ai's DB. Pro: minimum coordination. Con: violates "don't write to arthor-ai's tables / don't depend on their internal schema" rule. Hard no.

## Decision

**Option B: rich contract from day one**, materialized as `PayloadV1` pydantic models in slice `s04-payload-contract`.

### `payload_version: "1.0"` + JSON shape

```jsonc
{
  "payload_version": "1.0",
  "idempotency_key": "string (min 8 chars)",
  "site_id": "uuid",
  "agent_run_id": "uuid (echo from arthor-ai if it pre-created the run; else this service generates)",
  "callback_url": "https url",

  "business": {
    "site_name": "string",
    "industry": "string",
    "icp_summary": "string",      // copy of project.audience
    "value_prop": "string",       // project.offer + project.differentiation compressed
    "proof_points": ["string"],
    "forbidden_subjects": ["string"],  // merge seoConstraints.forbiddenTopics + extras
    "priority_services": ["string"]    // seoConstraints.priorityServiceLines
  },

  "location": {
    "mode": "local|regional|national",
    "city": "string?",
    "region": "string?",
    "country": "string (ISO 3166-1 alpha-2)",
    "service_areas": ["string"]
  },

  "brand_voice": {
    "tone": "string",
    "notes": ["string"],
    "style_direction": "string",        // project.styleDirection
    "reference_likes": ["string"],      // project.referenceLikes
    "do_not": ["string"]                // merged into style_profile.do_not
  },

  "brand_visual": {
    "palette": {
      "light": { "primary": "#hex", "secondary": "#hex", "background": "#hex", "foreground": "#hex", "muted": "#hex" },
      "dark":  { "primary": "#hex", "secondary": "#hex", "background": "#hex", "foreground": "#hex", "muted": "#hex" }
    },
    "typography": { "sans": "string", "heading": "string" },
    "register_default": "photographic|illustrated|mixed",
    "logo_asset_id": "string?",
    "customer_reference_assets": [
      { "asset_id": "string", "role": "interior|team|product|logo|ambient", "url": "https url", "palette_hex": ["#hex"] }
    ]
  },

  "style_profile_hint": {
    "lighting": "string (full sentence preferred)",
    "camera_language": "string",
    "composition_rules": ["string"],
    "color_grading": "string",
    "texture": "string",
    "era_mood": "string?",
    "do_not": ["string"],
    "must_include": ["string"]
  },

  "pack": {
    "pack_id": "string",
    "base_seed": "int",
    "slot_order": ["slot_id", ...],   // determines hero-first ordering
    "reference_policy": {
      "hero_slot_id": "string",
      "condition_non_hero_slots_on_hero": true,
      "allow_user_reference_conditioning": true
    },
    "default_provider_hint": "openai_image|google_nano_banana|null"
  },

  "slots": [
    {
      "slot_id": "string",
      "ordinal": 0,
      "page": "string (route path, e.g. '/')",
      "route": { "name": "string?", "template": "string?", "target_keyword": "string?" },
      "section": { "section_type": "hero|services|testimonials|...", "section_instance_id": "string?" },
      "slot_kind": "hero|section_accent|card|og|portrait|background",
      "intent": "string (≥8 chars)",
      "copy_context": {
        "page_h1": "string?",
        "section_heading": "string?",
        "body_excerpt": "string?",
        "cta_label": "string?"
      },
      "subject": {
        "primary": "string",
        "setting": "string",
        "props": ["string"],
        "people_policy": { "faces_allowed": false, "notes": "string?" }
      },
      "camera": { "framing": "wide|medium|close|aerial", "angle": "eye-level|low|high", "lens_feel": "24mm|35mm|50mm|85mm|unspecified" },
      "lighting_mood": { "mood_tokens": ["string"], "contrast": "low|medium|high" },
      "layout": {
        "aspect_ratio": "string (e.g. '16:9')",
        "dimensions": { "w": 1920, "h": 1080 },
        "safe_area": { "mode": "start|center|end|all", "inset_pct": 10 },
        "overlay_text_risk": true
      },
      "count": 1,
      "provider_hint": "openai_image|google_nano_banana|null",
      "condition_on_slot_id": "string|null"
    }
  ]
}
```

### Minimum-viable payload (fallback validation)

If arthor-ai's first cut doesn't fill everything, the strict MVP that still validates:

- `payload_version`, `site_id`, `callback_url`, `idempotency_key`
- `business.{industry, icp_summary, value_prop}`
- `location.{mode, country}`
- `brand_voice.tone`
- `brand_visual.{palette.light.{primary, secondary, background, foreground}, register_default}`
- `style_profile_hint.{lighting, do_not}`
- `slots[]`: `slot_id`, `page`, `slot_kind`, `intent`, `layout.dimensions`, `count`

All other fields default per the resolver (ADR-0009). The validator surfaces a `payload_completeness_score` in the response so arthor-ai can see how much was missing.

### `image_request_payloads` table (per intake decision F)

Migration `002_image_request_payloads.sql`:

```sql
CREATE TABLE IF NOT EXISTS image_request_payloads (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_run_id    uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  payload_version text NOT NULL,
  payload         jsonb NOT NULL,
  payload_hash    text NOT NULL,   -- SHA-256 of canonical-JSON-encoded payload
  idempotency_key text NOT NULL,
  source          text NOT NULL DEFAULT 'arthor-ai',
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT image_request_payloads_idem_unique UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_irp_agent_run    ON image_request_payloads (agent_run_id);
CREATE INDEX IF NOT EXISTS idx_irp_payload_hash ON image_request_payloads (payload_hash);
```

### Versioning policy

- `payload_version: "1.0"` is the binding contract.
- Additive non-breaking changes ship as `1.1`, `1.2`, etc. The validator accepts any `1.x` and warns on unknown fields.
- Breaking changes ship as `2.0` with side-by-side `app/payload/models_v1.py` + `app/payload/models_v2.py`. The router dispatches based on `payload_version`.

### Idempotency

`idempotency_key` is required; service rejects requests missing it with 400. If the key was seen, return the existing `agent_run_id` + status (idempotent re-fetch, no re-run). UNIQUE constraint on `image_request_payloads.idempotency_key` enforces this at the DB.

### Authoritative source

The pydantic models in `app/payload/models.py` are the runtime authority. A `docs/payload-schema.v1.json` (JSON Schema 2020-12) artifact is generated from the pydantic models on every build; arthor-ai can use it for its emitter's compile-time validation.

## Consequences

What gets easier:
- arthor-ai has a concrete contract to target.
- Quality bar is achievable because the prompts have rich context.
- "Rerun from payload" is one DB query in the GUI.

What gets harder:
- arthor-ai has more emit work to do up front. Justin can stage by starting with the MVP fields and growing into the rich shape.
- 13+ pydantic models to maintain. Mitigation: generate JSON Schema from them; treat the JSON Schema as the cross-service interface.
- Schema evolution requires discipline. Versioning policy above handles it.
