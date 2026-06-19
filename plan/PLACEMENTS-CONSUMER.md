# Logo placements — consumer contract

- **Audience:** arthor-ai (persist + emit), template-repo / Cursor (read slots)
- **Date:** 2026-06-13
- **Related:** [`ASSET-ANALYZE-CONSUMER.md`](ASSET-ANALYZE-CONSUMER.md), [`adr/0010-payload-contract-v1.md`](adr/0010-payload-contract-v1.md)
- **Runtime authority:** [`app/routes/placements.py`](../app/routes/placements.py)

---

## Summary

Logos use **`placement_only`** treatment — **no image generation**. Image-service (and your analyze pipeline) produces a **slot → URL map** that Cursor/template-repo uses to wire `header.logo`, `footer.logo`, etc.

---

## Canonical placement shape

```jsonc
{
  "site_id": "uuid",
  "asset_id": "logo-ingest-id",
  "treatment": "placement_only",
  "placements": {
    "header.logo": "https://cdn.example.com/logo.png",
    "footer.logo": "https://cdn.example.com/logo.png"
  }
}
```

### v1 slot keys (when `logo_candidate === true`)

| Slot key | Use |
|----------|-----|
| `header.logo` | Primary nav / header brand mark |
| `footer.logo` | Footer brand mark (same URL in v1) |

Future slots may add `favicon`, `og.logo` — coordinate via additive analyze/placement version bump.

---

## Deriving placements from analyze

When [`POST /images/assets/analyze`](ASSET-ANALYZE-CONSUMER.md) returns `capabilities.logo_candidate === true`:

```typescript
function placementsFromAnalyze(
  siteId: string,
  assetId: string,
  publicUrl: string,
  analyze: AnalyzeResponse,
): PlacementManifest {
  if (!analyze.capabilities.logo_candidate) {
    return {
      site_id: siteId,
      asset_id: assetId,
      treatment: analyze.recommended_treatment,
      placements: {},
    };
  }
  return {
    site_id: siteId,
    asset_id: assetId,
    treatment: "placement_only",
    placements: {
      "header.logo": publicUrl,
      "footer.logo": publicUrl,
    },
  };
}
```

Server reference: `placements_from_analyze()` in [`app/routes/placements.py`](../app/routes/placements.py).

---

## Where each repo stores/serves placements

### arthor-ai (source of truth for site build)

After analyze + auto or confirmed placement:

1. Persist on site / project state, e.g. `projectState.assetPlacements` or `brand.logoUrls`.
2. Pass into template-repo packet or page composition context.
3. Optionally register with image-service GET store (below) for debugging — **not required for Cursor**.

Recommended persist shape:

```jsonc
{
  "placement_version": "1.0",
  "site_id": "uuid",
  "placements": {
    "header.logo": "https://…",
    "footer.logo": "https://…"
  },
  "source_asset_id": "…",
  "updated_at": "ISO8601"
}
```

### template-repo / Cursor (read-only)

- Read **`placements` map from arthor-ai site packet** — do not call image-service in the hot build path unless explicitly wired for dev.
- Map keys are **stable layout contract** — template components bind `header.logo` to the URL string.

### image-service GET (optional / dev)

### `GET /images/placements/{site_id}`

| | |
|---|---|
| **Auth** | HMAC over **empty body** (`sign_body(secret, b"")`) |
| **Success** | `200` `{ "site_id", "placements", "treatment": "placement_only" }` |
| **Errors** | `401`, `503` |

**v1 limitation:** In-memory stub store on image-service unless populated by future registration API or shared DB. **Production: arthor-ai site state is authoritative.** GET is for operator smoke and future shared registry.

---

## Flow with analyze

```
Upload logo → ingest row + public URL
→ POST /images/assets/analyze
→ logo_candidate && !confirm_first_required
→ placementsFromAnalyze → save to site state
→ Cursor reads projectState.assetPlacements
→ No POST to image-service generate routes
```

Confirm-first path: wait for user chip selection **"Use as logo"** before writing placements.

---

## brand_visual.logo_asset_id (pack/hero)

Separate from placement map: PayloadV1 `brand_visual.logo_asset_id` references an asset id for pack/hero context. For SMS/email logos, set this after placement is confirmed so downstream pack emits include logo reference.

---

## Errors

Same HMAC rules as [`ASSET-ANALYZE-CONSUMER.md`](ASSET-ANALYZE-CONSUMER.md). GET returns empty `placements: {}` when site unknown (200) — distinguish from 404 on missing site in your registry if you add one in arthor-ai.

---

## Out of scope

- Logo generation or SVG conversion
- Multi-variant logo sizes (future)
- `POST` register endpoint (not in v1 — persist in arthor-ai)
