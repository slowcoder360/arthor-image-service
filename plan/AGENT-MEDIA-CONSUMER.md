# Agent media ingest — consumer contract (arthor-agent)

- **Audience:** arthor-agent W22/W23 SMS/email ingest, chat confirm, preview links
- **Date:** 2026-06-13
- **Related:** [`ASSET-ANALYZE-CONSUMER.md`](ASSET-ANALYZE-CONSUMER.md), [`PLACEMENTS-CONSUMER.md`](PLACEMENTS-CONSUMER.md), [`HANDOFF-VERTICAL-PROMPTS-AND-USER-ASSETS.md`](HANDOFF-VERTICAL-PROMPTS-AND-USER-ASSETS.md)
- **Image-service scope:** analyze API only — **this repo does not implement SMS, chat, or preview URLs**

---

## Summary

When a user sends a photo (SendBlue, email attachment) or completes web upload via arthor-ai:

1. **Ingest** → store bytes + `user_media_assets` row (your schema)
2. **Analyze** → `POST /images/assets/analyze` (HMAC from agent or via arthor-ai proxy)
3. **Route** → auto vs confirm-first from analyze fields
4. **Treat** → placement / enhance / reference (call image-service or update payloads for pack/hero)
5. **Preview** → site preview link for publish gate (**your UX**, not image-service)

---

## Ingest row (minimum)

Persist before analyze:

| Field | Notes |
|-------|-------|
| `id` / `asset_id` | Stable uuid — sent as analyze `asset_id` |
| `site_id` | Owning site |
| `source_channel` | `sendblue` \| `email_attachment` \| `web` |
| `url` or `r2_key` | Location image-service can fetch |
| `mime`, `bytes` metadata | Optional; analyze returns authoritative mime/dims |

After analyze, merge into `metadata`:

```jsonc
{
  "analyze_snapshot": { /* full analyze 200 */ },
  "recommended_treatment": "enhance_headshot",
  "confidence": 0.86,
  "confirm_first_required": false
}
```

---

## Auto vs confirm-first (locked product rules)

| Condition | UX |
|-----------|-----|
| `confidence >= 0.75` && `!confirm_first_required` | **Auto** — apply treatment; message: *"Got it — placing this on your site. I'll send a preview before anything goes live."* |
| `confirm_first_required` | **Confirm** — ≤3 chips, e.g. "Use as logo", "Enhance for team page", "Use as reference only", "Skip" |
| Face + headshot + hero intent (future) | Force confirm even if confidence high (likeness risk) |

Optional user setting (store on profile/site in **arthor-agent or arthor-ai**):

```typescript
media_confirmation_mode: "auto" | "confirm_first"  // default "auto"
```

When `confirm_first`, always show chips even if analyze would auto.

---

## Treatment actions (agent responsibilities)

| `recommended_treatment` | Agent / ai action |
|-------------------------|-------------------|
| `placement_only` | Write [`PLACEMENTS-CONSUMER.md`](PLACEMENTS-CONSUMER.md) map to site state; no generate call |
| `enhance_headshot` | Trigger hero `regenerate-variant` with `edit_kind: enhance_headshot` **or** queue pack slot regen when wired; requires uploaded asset id |
| `reference_only` | Append to `customer_reference_assets` on next hero/pack payload from arthor-ai |

Image-service **never** sends SMS or renders chips.

---

## Calling analyze from agent

**Option A — direct (preferred when agent has HMAC secret):**

```
POST https://<image-service>/images/assets/analyze
X-Arthor-Signature: sha256=…
{ asset_id, url, source_channel: "sendblue" | "email_attachment" }
```

**Option B — proxy via arthor-ai:** internal API that forwards signed request (same body/response).

Use `source_channel` matching ingest path for analytics.

---

## Preview and publish gate

Unchanged from existing site-build flow:

- Auto-treatment still requires **site preview approval** before publish
- Preview link generation = arthor-agent / arthor-ai responsibility
- Analyze does not replace publish gate

---

## Email / MMS attachment path

1. Receive attachment → upload to R2 → public/signed URL
2. Create `user_media_assets` row
3. Analyze with `source_channel: "email_attachment"`
4. Continue auto or confirm flow

---

## Error handling (user-facing)

| Analyze failure | User message (example) |
|-----------------|------------------------|
| 502 fetch failed | "We couldn't read that photo — try sending again?" |
| Low confidence + confirm | Show chips; don't blame user |
| Not a logo when user said "logo" | Chip: "Use anyway" / "Send a different file" |

Log `analyze_snapshot.warnings` for support.

---

## Coordination with arthor-ai

| Concern | Owner |
|---------|-------|
| `user_media_assets` DDL | W11 / shared schema |
| Analyze call | agent or ai |
| `customer_reference_assets` on pack | arthor-ai emitter |
| Site preview URL | arthor-ai + agent |
| `media_confirmation_mode` storage | agent or ai (not image-service) |

---

## Out of scope (explicit)

- SMS copy templates (marketing)
- SendBlue webhook implementation
- Image generation from agent process (delegate to image-service routes documented elsewhere)

See [`CROSS-REPO-HANDOFF-INDEX.md`](CROSS-REPO-HANDOFF-INDEX.md) for full API list.
