# SYNTHESIS — Hero layout-archetype layer (v1, hero-only)

> Consolidates [POD-A](POD-A-os-website-builders.md) (one-shot builders), [POD-B](POD-B-layout-archetype-taxonomy.md) (layout taxonomy), [POD-C](POD-C-design-skill-files.md) (anti-slop skill files) into one decision artifact.
> **Status:** proposal for review. No code written. Decide before slicing.

---

## The one finding all three pods agree on

**One-shot quality is a *selection* problem, not a *generation* problem.** Every credible builder (Relume, Webflow, Durable, the anti-slop skills) picks a **layout archetype from a finite catalog _before_ touching imagery**. Arthor today inverts this: it resolves a photographic scene first and assumes the layout (full-bleed photo + copy overlay) is fixed. That single assumption is what makes us fragile outside local-service.

The fix is the layer we already named: a deterministic `hero_layout_archetype` axis that resolves **before** `scene_archetype`, and decides whether the photo corpus even runs.

---

## Locked constraints (from this session)

1. **Hero-only first.** No full-page section composition in v1.
2. **Deterministic routing.** `brand_mode/vertical → hero_layout_archetype` lookup, mirroring `resolve_scene_archetype`. No LLM in the routing path.
3. **Generate the new imagery.** Abstract/gradient heroes via existing providers under new archetype-keyed prompt branches — no new provider.
4. **This doc, then decide.** Then slice.

---

## 1. Proposed `hero_layout_archetype` catalog (v1)

Mirrors the shape of `SCENE_CATALOG` in `app/style/hero_visual_strategy.py`. Each archetype declares the **imagery contract** it consumes — that contract is what this repo (image-service) acts on.

| Archetype ID | When (brand/intent) | `imagery_type` | Photo corpus runs? | Image-service action |
|---|---|---|---|---|
| `full_bleed_photo_overlay` | Local-service premium, restaurant, med-spa, real estate — emotional/atmospheric | `real_photo` | **yes** | Current pipeline (default today) |
| `split_copy_image` | Local-service, home-service, professional-service default; SaaS when product is visual | `real_photo` *or* `product_ui` | **yes** (photo case) | Current pipeline, photo framed for a side-media column |
| `centered_copy_cta` | AI platforms, consulting, abstract products — copy is the proof | `abstract_or_none` | no | New abstract prompt branch, or emit no-image |
| `abstract_gradient_3d` | AI startups, dev tools, tech agencies — modern, no people | `generative_abstract` | no | **New generated-imagery branch (primary v1 build)** |
| `typographic_no_image` | Portfolio, creative agency, editorial — type is the brand | `none` | no | Emit "no hero image" signal |
| `product_screenshot` | SaaS, fintech, B2B software — the UI is the value prop | `product_ui` | no | **Flagged — see §5** |

**Deferred to a later wave:** `bento_hero`, `illustration_hero`, `video_hero`, `input_capture`, `carousel_hero` (POD-B documents all of these).

---

## 2. Deterministic routing: `brand_mode/vertical → hero_layout_archetype`

Two-tier, exactly like today's `INDUSTRY_VISUAL_TRIAD` fallback chain. **Brand mode is the primary driver** (a dental clinic and an AI agency differ more by mode than by vertical); vertical is the override.

```yaml
# Primary: coarse brand mode → default hero layout
BRAND_MODE_DEFAULT_LAYOUT:
  local_service:        split_copy_image
  home_service:         split_copy_image
  professional_service: split_copy_image
  healthcare:           split_copy_image
  premium_local:        full_bleed_photo_overlay   # restaurant, med_spa, real_estate
  tech_saas:            product_screenshot
  ai_platform:          centered_copy_cta
  dev_tools:            abstract_gradient_3d
  agency:               split_copy_image            # copy-led + abstract right
  ecommerce:            full_bleed_photo_overlay
  creative_portfolio:   typographic_no_image

# Photo corpus only runs for these:
PHOTO_LAYOUTS: [full_bleed_photo_overlay, split_copy_image]
```

- Justin's "Arthor — AI-native marketing systems" prompt → `brand_mode: agency`/`ai_platform` → `split_copy_image` (copy-led) or `centered_copy_cta` with **abstract** right-side imagery — **never** the human-photo corpus. Exactly the call you made in the original message.
- `hero_job` (trust/outcome/experience) stays **orthogonal** — it still drives copy tone and, when photo-eligible, scene selection. POD-B and POD-C both confirm this separation.

**Open question (needs your call):** where does `brand_mode` come from? Options in §6.

---

## 3. Per-archetype imagery spec + prompt branches

| Archetype | Prompt source | Notes |
|---|---|---|
| `full_bleed_photo_overlay`, `split_copy_image` | **Existing** `variant_subject_primary` + scene catalog | Unchanged. `split` may want a tighter, side-framed composition variant. |
| `abstract_gradient_3d` | **New** prompt-template branch | Generated via current providers. Restrained palette (≤2 accents), no people, no text. This is the main net-new generation work. |
| `centered_copy_cta` | Optional subtle abstract, else none | Reuse abstract branch at low intensity, or emit no-image. |
| `typographic_no_image` | None | Emit a structured "no hero image" result so the builder composes type-only. |
| `product_screenshot` | **Flagged** — see §5 | |

---

## 4. `GLOBAL_HERO_AVOID` becomes per-archetype

Today `GLOBAL_HERO_AVOID` (`app/style/hero_archetypes.py`) globally bans *"blank left half or empty void reserved for copy"* — correct for full-bleed, **fatal for split**, where a clean copy column is *required geometry*. Avoid-lists must hang off the archetype:

| Avoid item (today, global) | Correct scope |
|---|---|
| "blank left half reserved for copy" | `full_bleed_photo_overlay` only |
| "sterile copy-zone wall with no scene continuity" | `full_bleed_photo_overlay` only |
| "stock smile staring at camera" | all photo archetypes (stays global-ish) |
| "rendered words or signage text" | all (stays global) |
| *(new)* "people / stock humans" | `abstract_gradient_3d`, `typographic_no_image` |
| *(new)* "rainbow / indigo-purple gradient" | `abstract_gradient_3d` (POD-C: #1 AI-slop tell) |

Plus the POD-C anti-slop image bans worth merging into the photo `do_not`: no generic 3-person handshake stock, no purple-gradient lighting.

---

## 5. The `product_screenshot` caveat (flagging, not deciding)

The locked decision was "generate abstract/gradient/3D/**product-screenshot**." All three pods independently warn that **generating a believable product UI is the weakest fit** for an image model — POD-B and POD-A both say product screenshots should be *real captures*, not generated (generated UI reads as fake/lorem instantly). Recommendation: in v1, treat `product_screenshot` as **client-supplied / capture**, and point the generation effort at `abstract_gradient_3d`, which generates cleanly. Happy to do it either way — just don't want to silently ship generated fake UIs.

---

## 6. Repo-boundary question (POD-C raised this; it matters for slicing)

POD-C argues the **HTML** layout belongs on the builder (arthor-ai), while image-service owns imagery. That's consistent with `CONTEXT.md`'s W11/site-build-emit boundaries. For our **hero-only / this-repo** scope, the clean split is:

- **image-service (here):** owns the `hero_layout_archetype` *decision* + the matching imagery (or a typed "no image needed" signal). It already emits `safe_area`/`slot.layout`.
- **builder (arthor-ai):** consumes the archetype + imagery to compose actual HTML.

So v1 in this repo = **resolver + imagery branch + per-archetype avoids + the archetype on run metadata** — not HTML.

---

## Open decisions before slicing

1. **`brand_mode` source** — (a) extend the existing industry keyword map with a coarse mode tag, (b) add an explicit `brand_mode` field to the payload, or (c) derive from the brand packet.
2. **`product_screenshot`** — generate (as locked) vs. client-supplied/capture (pods' recommendation, §5).
3. **Scope confirm** — does the archetype *decision* live in image-service (my §6 read) or should it be a pure builder concern with image-service only told the `imagery_type`?
4. **Anti-slop skills** — adopt POD-C's P0 vendoring (anti-slop checklist + Design Declaration) now, or defer until the full-page wave?
