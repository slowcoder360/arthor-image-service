# Asset analyze — consumer contract

- **Audience:** arthor-ai (web upload), arthor-agent (SMS/email W22/W23 ingest)
- **Date:** 2026-06-13
- **Related:** [`HANDOFF-IMAGE-SERVICE-COMPLETION.md`](HANDOFF-IMAGE-SERVICE-COMPLETION.md), [`AGENT-MEDIA-CONSUMER.md`](AGENT-MEDIA-CONSUMER.md), [`adr/0006-hmac-auth-convention.md`](adr/0006-hmac-auth-convention.md)
- **Runtime authority:** [`app/routes/asset_analyze.py`](../app/routes/asset_analyze.py), [`app/quality/asset_analyze.py`](../app/quality/asset_analyze.py)

---

## Summary

Deterministic image analysis (no LLM). Call after ingest when bytes are reachable at a URL or R2 key. Response drives **what to do next** (`recommended_treatment`, roles, confidence, confirm gate).

**Image-service does not:** send SMS, show chips, or store analyze results in Neon for you. **You** persist `analyze_snapshot` on `user_media_assets.metadata` (or equivalent) and implement confirm/auto UX.

---

## Endpoint

### `POST /images/assets/analyze`

| | |
|---|---|
| **Auth** | HMAC over raw JSON body |
| **Success** | `200` analyze response (below) |
| **Errors** | `400` invalid body / missing url+r2_key, `401` signature, `502` asset fetch failed, `503` hmac secret or r2 unavailable, `404` asset not found |

---

## Request

```jsonc
{
  "asset_id": "uuid-or-stable-id",       // echo back; your ingest id
  "url": "https://...",                  // one of url | r2_key required
  "r2_key": "uploads/site/abc.png",      // fetched via service R2 client when url omitted
  "source_channel": "web",               // "web" | "sendblue" | "email_attachment"
  "declared_purpose": "optional string"  // NEVER trusted alone for routing
}
```

| Field | Notes |
|-------|--------|
| `asset_id` | Stable id from your ingest row |
| `url` | Public or signed URL image-service can GET (30s timeout) |
| `r2_key` | Same bucket as image-service R2 config |
| `source_channel` | Audit only in v1; does not change analyze logic |
| `declared_purpose` | Logged/ignored for classification in v1 |

---

## Response

```jsonc
{
  "analyze_version": "1.0",
  "asset_id": "...",
  "mime": "image/jpeg",
  "width": 1200,
  "height": 1600,
  "capabilities": {
    "logo_candidate": false,
    "headshot_eligible": true,
    "enhance_recommended": true,
    "reference_eligible": true,
    "hero_background_candidate": false
  },
  "recommended_roles": ["team"],
  "recommended_treatment": "enhance_headshot",
  "confidence": 0.86,
  "confirm_first_required": false,
  "warnings": []
}
```

### `capabilities` (deterministic)

| Field | Meaning |
|-------|---------|
| `logo_candidate` | Alpha + compact opaque region; square/landscape logo heuristic |
| `headshot_eligible` | Portrait aspect, min dimension, skin-tone or sharpness heuristic |
| `enhance_recommended` | Headshot eligible (v1: all eligible headshots) |
| `reference_eligible` | Min 320px edge; not classified as logo |
| `hero_background_candidate` | Landscape, not headshot, sufficient sharpness |

Face detection is **Pillow-only heuristics** in v1 (no opencv/mediapipe). Do not assume bbox/face_count until a future analyze version adds them.

### `recommended_treatment` values

| Value | Typical upstream action |
|-------|-------------------------|
| `placement_only` | Logo → layout slots ([`PLACEMENTS-CONSUMER.md`](PLACEMENTS-CONSUMER.md)); no generation |
| `enhance_headshot` | OpenAI edit/enhance path ([`HERO-CANDIDATES-CONSUMER.md`](HERO-CANDIDATES-CONSUMER.md) `edit_kind: enhance_headshot` or future pack hook) |
| `reference_only` | Add to `customer_reference_assets` on next pack/hero request |

### `recommended_roles`

Hints for slot/role assignment: `"logo"`, `"team"`, `"interior"`, `"ambient"`, etc.

### `confidence` and `confirm_first_required`

| Rule | Behavior |
|------|----------|
| `confidence >= 0.75` and `confirm_first_required === false` | **Auto path** — apply `recommended_treatment`, then site preview for publish gate |
| `confirm_first_required === true` | **Confirm path** — max 3 chips (agent/ai UX); do not auto-enhance or auto-place in hero |
| Likeness / skin-tone on headshot | May set `confirm_first_required` even when confidence is high |

**Mirror logic** (optional client-side duplicate of [`app/routing/treatment_router.py`](../app/routing/treatment_router.py)):

```
auto_apply = confidence >= 0.75 && !confirm_first_required
```

Image-service does not expose `TreatmentPlan` over HTTP; derive from analyze fields above.

### `warnings`

Non-fatal signals, e.g. `low_sharpness`, `ambiguous_aspect`. Surface in operator UI; do not block auto path unless you choose to.

---

## Persistence contract (your DB)

After a successful analyze, persist on the ingest row (e.g. `user_media_assets.metadata`):

```jsonc
{
  "analyze_snapshot": { /* full 200 response */ },
  "recommended_treatment": "enhance_headshot",
  "confidence": 0.86,
  "confirm_first_required": false,
  "analyze_version": "1.0",
  "analyzed_at": "2026-06-13T…"
}
```

Use the same field names so inspector and cross-repo debugging align.

---

## End-to-end flows

### Auto (default)

```
ingest → POST analyze → confidence OK → apply treatment
  → placement_only: write placements map (see PLACEMENTS doc)
  → enhance_headshot: queue edit/generate → preview link
  → reference_only: append to customer_reference_assets for next pack/hero
→ user approves site preview (publish gate unchanged)
```

### Confirm-first (exception)

```
ingest → POST analyze → confirm_first_required
→ chat/SMS: ≤3 chips (e.g. "Use as logo", "Enhance for team page", "Skip")
→ on choice, call treatment-specific APIs
```

See [`AGENT-MEDIA-CONSUMER.md`](AGENT-MEDIA-CONSUMER.md) for copy and `media_confirmation_mode`.

---

## TypeScript sketch (arthor-ai)

```typescript
type SourceChannel = "web" | "sendblue" | "email_attachment";

type AnalyzeRequest = {
  asset_id: string;
  url?: string;
  r2_key?: string;
  source_channel: SourceChannel;
  declared_purpose?: string;
};

type AnalyzeResponse = {
  analyze_version: "1.0";
  asset_id: string;
  mime: string;
  width: number;
  height: number;
  capabilities: {
    logo_candidate: boolean;
    headshot_eligible: boolean;
    enhance_recommended: boolean;
    reference_eligible: boolean;
    hero_background_candidate: boolean;
  };
  recommended_roles: string[];
  recommended_treatment: "placement_only" | "enhance_headshot" | "reference_only";
  confidence: number;
  confirm_first_required: boolean;
  warnings: string[];
};
```

Sign with the same HMAC helper used for hero-candidates and asset-pack.

---

## Errors (implement handlers)

| HTTP | `detail` | Action |
|------|----------|--------|
| 400 | `url_or_r2_key_required` | Fix request |
| 400 | `invalid_request` | Pydantic validation |
| 401 | `invalid_signature` | Fix secret/signing |
| 404 | `asset_not_found` | Bad url/r2_key |
| 502 | `asset_fetch_failed` | Retry or fix URL |
| 503 | `r2_unavailable` / `hmac_secret_unset` | Ops |

---

## Out of scope (this doc)

- Pack/hero generation payloads — see other consumer docs
- Vertical industry prompt tuning — Justin operator lane
- Analyze callback/webhook — v1 is sync POST only
