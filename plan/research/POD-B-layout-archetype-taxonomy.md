# POD-B: Layout Archetype & Section Taxonomy Research

**Scope:** Web research only. Informs a layout-archetype catalog that sits **above** image generation in Arthor.  
**Date:** 2026-06-25  
**Context:** Arthor today has a 6-entry **scene catalog** (people-in-a-scene photographic archetypes) resolved by industry. It has **no hero layout archetype** or **section taxonomy**. Layout choice (split vs full-bleed vs typographic) is upstream of what the image model should produce.

---

## Executive summary

Modern marketing sites converge on ~12 hero **layout** archetypes (distinct from photographic **scene** archetypes). The canonical page skeleton is an 8–9 section AIDA flow: hero → social proof → value/features → testimonials → pricing → FAQ → final CTA → footer. Section libraries (Relume, Tailwind Plus, shadcn blocks, Flowbite, Untitled UI, 21st.dev, Cruip) largely codify the same taxonomy with different licensing models.

**Key insight for Arthor:** Local service businesses (dental, HVAC) default to **split copy + real photo** or **full-bleed photo overlay** with trust signals; tech/SaaS/AI defaults to **split copy + product screenshot** or **centered copy on abstract/gradient**; e-commerce uses **full-bleed lifestyle/product** or **split + product carousel**; creative/portfolio uses **full-bleed**, **typographic**, or **bento** heroes. Each layout archetype implies a different **imagery type** for the downstream image pipeline—often **none** (product UI, gradient) rather than people-in-a-scene.

---

## 1. Hero layout archetype catalog

Sources: [Spell UI hero best practices](https://spell.sh/blog/hero-section-best-practices), [Express Jam hero layouts 2026](https://www.expressjs.org/how-to-design-a-hero-section-that-converts-layout-copy-and-cta-best-practices/), [LogRocket hero pattern comparison](https://blog.logrocket.com/ux-design/hero-section-examples-best-practices/), [Pravin Kumar bento heroes 2026](https://www.pravinkumar.co/blog/bento-box-hero-sections-webflow-design-2026), [Brainy bento grid playbook](https://brainy.ink/paper/bento-grid-design), [Coyne local-service hero anatomy](https://coynelabs.com/insights/hero-section-anatomy), [Nopio HVAC design guide](https://www.nopio.com/blog/hvac-website-design/).

| Archetype ID | When to use (industry / brand / intent) | Imagery type | Quality cues | Anti-patterns |
|---|---|---|---|---|
| `split_copy_image` | **Default for local services** (dental, HVAC, legal, home services): need trust + clarity fast. Also SaaS when product is visual but copy must lead. Intent: explain + show. | Real photo (team, workplace, service moment) **or** product screenshot (SaaS) | 50/50 or 40/60 column balance; headline ≤10 words; single primary CTA; visual has subtle shadow/border; mobile stacks copy then image | Generic stock; two equal CTAs; image pushed below fold on mobile before CTA; equipment-as-subject without people context |
| `full_bleed_photo_overlay` | **High-emotion local services**, restaurants, med-spa, real estate, creative brands with strong photography. Intent: atmosphere + immediate CTA (call/book). | Full-bleed **real photo** or lifestyle image; dark/light scrim for text contrast | Semi-transparent overlay; high-contrast type; phone/CTA visible without scroll; authentic local photography | Auto-play video with sound; unreadable text on busy backgrounds; stock “smiling contractor”; hero sliders ([Nopio](https://www.nopio.com/blog/hvac-website-design/) notes sliders hurt conversion) |
| `centered_copy_cta` | **Abstract/conceptual products** (AI platforms, dev tools, consulting) where copy is the proof. Brands like Linear/Vercel pattern ([Spell UI](https://spell.sh/blog/hero-section-best-practices)). Intent: singular message. | Abstract gradient/mesh, subtle pattern, or minimal product peek; often **no dominant photo** | Strict vertical hierarchy (H1 → sub → CTA); max-width ~720px headline; one CTA; generous whitespace | Long subhead; feature lists in hero; decorative motion competing with headline |
| `product_screenshot` | **SaaS, fintech, B2B software** where UI *is* the value prop. SMB/mid-market landing pages ([LogRocket product preview](https://blog.logrocket.com/ux-design/hero-section-examples-best-practices/)). | Product screenshot, realistic UI mock, or short looping demo (5–10s) | Real data in UI; device frame optional; screenshot grounded with shadow; social proof immediately below | Fake/lorem UI; illustration pretending to be product; mockup floating without context |
| `product_showcase_interactive` | **Large software** with demo-led sales (enterprise SaaS, design tools). Intent: “see it work.” | Video showcase, interactive embed, or animated UI segments | Pause controls; accessible motion; static fallback | Autoplay with no controls; heavy WebGL blocking LCP |
| `abstract_gradient_3d` | **Tech, AI, dev tools, startups** prioritizing modern/futuristic feel without people. Typing-effect heroes ([LogRocket](https://blog.logrocket.com/ux-design/hero-section-examples-best-practices/)). | CSS gradient, mesh, grain, subtle 3D render, shader background | Restrained palette (1–2 accents); motion subtle; type carries hierarchy | Rainbow gradients; noisy WebGL; gradient-as-substitute for weak copy |
| `video_hero` | **Automotive, sports, luxury hospitality, cinematic brands** ([LogRocket full-size video](https://blog.logrocket.com/ux-design/hero-section-examples-best-practices/)). Intent: immersion. | Looping **muted** background video; optional poster frame | Overlay + readable type; poster for LCP; no autoplay audio | Autoplay hero video ([Spell UI](https://spell.sh/blog/hero-section-best-practices) underperforms vs static); video as only message |
| `illustration_hero` | **Playful SaaS, edtech, health/wellness startups**, brands avoiding stock photos. Ultra-minimal products ([LogRocket minimalistic](https://blog.logrocket.com/ux-design/hero-section-examples-best-practices/)). | Custom illustration (flat, 3D, or line) | Consistent illustration system; supports headline don’t replace it | Generic undraw-style; illustration unrelated to offer |
| `typographic_no_image` | **Portfolio, editorial, luxury minimal, agency positioning** where typography *is* the brand. Strong copy brands. | **None** or micro-accent (line, icon) | Display type scale; tight tracking at large sizes; high contrast; one CTA | Walls of text; no visual relief on mobile; category headline (“All-in-one platform”) |
| `bento_hero` | **Multi-capability SaaS, dev tools, AI platforms** with 4–8 parallel proof points ([Brainy](https://brainy.ink/paper/bento-grid-design), [Pravin Kumar](https://www.pravinkumar.co/blog/bento-box-hero-sections-webflow-design-2026)). Intent: density without scroll. | Per-cell: UI fragment, metric, logo, icon, small photo, or chart—**mixed** | One **anchor** cell (2×2); single read path; 24–32px inner padding; one sentence per cell | Two equal columns pretending to be bento; paragraph text in small cells; no anchor hierarchy |
| `input_capture` | **PLG SaaS, newsletters, waitlists** where signup is the primary conversion ([LogRocket input-capture](https://blog.logrocket.com/ux-design/hero-section-examples-best-practices/)). | Abstract background + minimal UI chrome | Single input + one CTA; focus-visible states; privacy microcopy | Multi-field forms; input before value prop is clear |
| `carousel_hero` | **E-commerce multi-SKU**, marketplaces with many equal products ([LogRocket carousel](https://blog.logrocket.com/ux-design/hero-section-examples-best-practices/)). Use sparingly. | Rotating product/lifestyle images | Manual controls; consistent CTA across slides; pause | Auto-rotating homepage sliders on local service sites ([Coyne](https://coynelabs.com/insights/hero-section-anatomy): 20–40% conversion loss vs static) |

### Imagery type → pipeline implication

| Imagery type | Typical layout archetypes | Image pipeline action |
|---|---|---|
| Real photo (people/scene) | `split_copy_image`, `full_bleed_photo_overlay` | **Current scene catalog** applies |
| Real photo (environment, no faces) | `split_copy_image`, `full_bleed_photo_overlay`, bento cell | `environment_warmth`-like scenes or location shots |
| Product screenshot / UI | `product_screenshot`, `split_copy_image`, bento cell | **No generative photo** — capture/render UI |
| Abstract / gradient / 3D | `centered_copy_cta`, `abstract_gradient_3d`, `typographic_no_image` | **No people scene** — CSS/asset gradient or 3D render |
| Illustration | `illustration_hero`, `split_copy_image` | Illustration model or curated library — not photo scene catalog |
| Video | `video_hero`, `product_showcase_interactive` | Stock/captured video — not still image gen |
| None | `typographic_no_image`, `input_capture` | Skip hero image generation entirely |

---

## 2. Section taxonomy (marketing site)

Sources: [Better Launch SaaS anatomy](https://www.betterlaunch.co/blog/saas-landing-page), [UI Incubator section guide](https://ui-incubator.com/en/blog/saas-landing-page-sections), [Spell UI landing sections](https://spell.sh/blog/landing-page-sections), [SplitSense SaaS best practices](https://splitsense.ai/blog/guides/saas-landing-page-best-practices-14-proven-tips-2026/), [Relume library docs](https://resources.relume.io/resources/docs/how-to-use-the-relume-webflow-library), [Tailwind Plus marketing sections](https://tailwindcss.com/plus/ui-blocks/marketing).

### Canonical section order (AIDA-adapted)

| Order | Section ID | Purpose | Typical layout pattern |
|---|---|---|---|
| 0 | `nav_header` | Orientation, logo, primary nav, phone (local) | Horizontal bar; sticky on scroll |
| 1 | `hero` | Answer what / why / next in ≤5s | See §1 archetypes |
| 2 | `logo_cloud` / `social_proof_bar` | Immediate credibility | Horizontal logo strip or stat bar |
| 3 | `value_prop` | One-sentence positioning + 3 benefits | 3-up cards or single paragraph + bullets |
| 4 | `features` | How it works; benefits not features | 3-up grid, **alternating rows**, or **bento** |
| 5 | `how_it_works` | 3-step process (optional) | Numbered steps horizontal/vertical |
| 6 | `testimonials` | Proof after claims | Cards, carousel, or video testimonials |
| 7 | `pricing` | Remove ambiguity (SaaS/e-comm) | 3-tier table + toggle |
| 8 | `faq` | Objection handling + SEO | Accordion, 5–8 questions |
| 9 | `cta_band` | Repeat primary action | Full-width contrasting band |
| 10 | `footer` | Links, NAP, legal, secondary trust | Multi-column |

**Local service variant:** Often collapses `pricing` (use “Get a quote”), adds `service_areas`, `certifications`, `before_after`, and moves **phone + reviews** into `hero` or `nav_header`. [Rise Marketing CRO](https://rise.co/blog/cro-tactics-that-move-the-needle-saas-vs-d2c-vs-local-service) reports local lift from reviews + click-to-call above fold.

### Section libraries comparison

| Library | Section coverage (marketing) | Open source? | Licensing notes |
|---|---|---|---|
| [Relume](https://www.relume.io/figma-library) | 1,000+ sections: Hero Headers, Features, Testimonials, Pricing, FAQ, CTA, Footer, Bento, Comparison, Logo clouds; Marketing / e-Commerce / App UI | **No** (proprietary) | [License](https://www.relume.io/legal/licensing-agreement): use in end products; no redistribution/resale; no raw copy-paste to shared repos without modification |
| [Tailwind Plus](https://tailwindcss.com/plus/ui-blocks/marketing) (formerly Tailwind UI) | Hero, Feature, CTA, Bento Grids, Pricing, Testimonials, Logo Clouds, FAQ, Footer, Blog, Contact, Team, Stats, Newsletter | **No** | One-time purchase; [license](https://tailwindcss.com/plus/ui-blocks): OK in sites/apps, not derivative UI kits |
| [shadcn/ui blocks](https://ui.shadcn.com/blocks) | Dashboard-focused; marketing via community | **Yes** (MIT) | Copy-paste ownership model |
| [21st.dev](https://21st.dev/community/components/s/hero%2Bsection) | Heros, Features, CTA, Testimonials, Pricing, Shaders, AI chat blocks | **Registry MIT**; per-component varies | Community marketplace; install via `npx shadcn add` |
| [shadcnblocks.com](https://www.shadcnblocks.com/) | Hero, features, pricing, ecommerce heroes | **Freemium** | Pro blocks paid; distributed via shadcn registry |
| [Flowbite](https://flowbite.com/docs/getting-started/introduction/) | Components + [Blocks](https://flowbite.com/blocks/) (450+ pro) | **Core MIT**; Blocks/Pro paid | [GitHub MIT](https://github.com/themesberg/flowbite/) |
| [Untitled UI React](https://www.untitledui.com/react) | Base + free marketing sections; PRO for 5k+ | **Partial MIT** (free tier) | [MIT for OSS components](https://github.com/untitleduico/react); PRO under separate [EULA](https://www.untitledui.com/license) |
| [Cruip](https://www.tailawesome.com/resources/simple-light) | Full landing templates: hero, features, testimonials, pricing, CTA | **Mixed** | Free templates often **GPL** (Simple Light); paid templates custom commercial license |
| [Hero Patterns](https://heropatterns.com/) | SVG **background patterns** only (not full sections) | **Free** (Steve Schoger) | Patterns free; not a section library |
| HyperUI / Meraki UI / Sailboat UI | Snippet-level hero, features, pricing, footer | **Mostly MIT** | Listed in [Colorlib Tailwind templates roundup](https://colorlib.com/wp/tailwind-landing-page-templates/) |

**Best codification of full page taxonomy:** Relume and Tailwind Plus mirror the canonical marketing flow most completely. shadcn/21st.dev excel at **hero + feature + pricing** atoms but require assembly. Flowbite/Untitled UI split free components vs paid blocks.

---

## 3. Brand / industry → recommended hero layout

Sources: [Coyne local hero](https://coynelabs.com/insights/hero-section-anatomy), [Nopio HVAC](https://www.nopio.com/blog/hvac-website-design/), [Rise CRO by vertical](https://rise.co/blog/cro-tactics-that-move-the-needle-saas-vs-d2c-vs-local-service), [Spell UI](https://spell.sh/blog/hero-section-best-practices), [Digital Web Avenue SaaS vs local](https://digitalwebavenue.net/how-paramount-knoxville-inspires-smarter-saas-web-design/), [shadcnblocks ecommerce heroes](https://www.shadcnblocks.com/block/ecommerce-hero6).

| Brand / industry type | Primary hero layout | Secondary options | Trust pattern in hero | Copy tone |
|---|---|---|---|---|
| **Local service** (dental, HVAC, plumbing, legal, med-spa) | `split_copy_image` with real team/patient/customer photo | `full_bleed_photo_overlay` for premium/emotional brands | Star rating, years in business, phone, “serving {city}” | Plain declarative: what + where + next step ([Coyne](https://coynelabs.com/insights/hero-section-anatomy)) |
| **Home services / trades** (roofing, landscaping, arborist) | `split_copy_image` or `full_bleed_photo_overlay` showing **completed work** | `environment_warmth` photo in split | Certifications, guarantee, response time | Outcome + geography filter |
| **Professional services** (CPA, insurance, law) | `split_copy_image` with `desk_side_guidance` photo | `centered_copy_cta` for niche positioning | Credentials, association logos | Authority without jargon |
| **Tech / SaaS / AI / agency** | `split_copy_image` + **product screenshot** OR `centered_copy_cta` on gradient | `bento_hero` for multi-feature platforms; `abstract_gradient_3d` for AI | Logo cloud immediately below; “Start free trial” | Outcome headline; show UI not abstract metaphors ([Spell UI](https://spell.sh/blog/hero-section-best-practices)) |
| **Dev tools / infrastructure** | `bento_hero` or `centered_copy_cta` + minimal UI | `typographic_no_image` | GitHub stars, customer logos in cells | Spec-sheet clarity ([Brainy Linear example](https://brainy.ink/paper/bento-grid-design)) |
| **E-commerce / D2C** | `full_bleed_photo_overlay` lifestyle **or** `split_copy_image` + product | `carousel_hero` only for multi-collection stores | Shipping/returns microcopy, star ratings | Seasonal campaign headline; product-as-hero |
| **Restaurant / hospitality / wedding venue** | `full_bleed_photo_overlay` | `video_hero` for ambiance | Reservations CTA, location | Sensory/emotional headline |
| **Creative / portfolio / design studio** | `typographic_no_image` or `full_bleed_photo_overlay` (work sample) | `bento_hero` for case-study tiles | Client logos optional | Personality-forward; minimal CTAs |
| **Health / wellness / gym** | `split_copy_image` (people + facility) | `full_bleed_photo_overlay` | Transformation proof, trial offer | Aspirational but specific |

### Contrast summary (requested)

| Dimension | Local service (dental, HVAC) | Tech / AI / agency | E-commerce | Creative / portfolio |
|---|---|---|---|---|
| Dominant layout | Split or full-bleed **photo** | Split + **UI** or centered + **gradient** | Full-bleed **lifestyle/product** | Typographic or full-bleed **work** |
| Imagery | Real people + place; anti-stock | Product UI, abstract tech bg | Product/lifestyle photography | Portfolio piece or none |
| Hero job | Trust + call/book | Comprehension + trial | Desire + shop | Impress + contact |
| CTA | Phone / book / quote | Sign up / demo | Shop / explore collection | View work / inquire |
| Anti-pattern | Slider, stock hard hat, tagline-only | Illustration-only, vague “platform” | Cluttered carousel without CTA | Over-animation, no clear contact |

---

## 4. Proposed Arthor layout-archetype catalog

Mirrors `SCENE_CATALOG` in `app/style/hero_visual_strategy.py`: small cross-industry set with `id`, structural intent, imagery contract, and avoid list. **Layout selection happens before scene selection.** Scene catalog applies only when `imagery_type` includes people-in-environment photography.

```yaml
LAYOUT_CATALOG_VERSION: "1.0"

LayoutArchetypeId:
  - split_copy_image
  - full_bleed_photo_overlay
  - centered_copy_cta
  - product_screenshot
  - abstract_gradient_3d
  - bento_hero
  - typographic_no_image
  - illustration_hero
  # deferred / low priority for v1:
  - video_hero
  - input_capture
  - carousel_hero

LAYOUT_CATALOG:
  split_copy_image:
    structure: "Two-column: copy block (headline, sub, CTA, optional trust chip) + media column"
    imagery_type: photo_or_product_ui
    scene_catalog_eligible: true
    default_for_brand_types: [local_service, professional_services, home_services]
    quality_cues:
      - "Headline ≤10 words; single primary CTA"
      - "Media column ~40-50% width desktop"
      - "Mobile: copy → CTA → image"
    avoid:
      - "Generic stock photography"
      - "Dual primary CTAs"
      - "Equipment as sole visual without human context"

  full_bleed_photo_overlay:
    structure: "Full-viewport background media + scrim + centered or left-aligned copy stack"
    imagery_type: real_photo
    scene_catalog_eligible: true
    default_for_brand_types: [local_service_premium, restaurant, real_estate, med_spa]
    quality_cues:
      - "Overlay ensures WCAG contrast"
      - "Phone/book CTA visible without scroll on mobile"
    avoid:
      - "Hero image carousel"
      - "Autoplay video with audio"
      - "Text directly on busy imagery without scrim"

  centered_copy_cta:
    structure: "Single-column centered stack; optional subtle background"
    imagery_type: abstract_or_none
    scene_catalog_eligible: false
    default_for_brand_types: [tech_saas, ai_platform, consulting]
    quality_cues:
      - "Max-width constraints on headline/subhead"
      - "Logo cloud immediately below fold"
    avoid:
      - "Feature bullets in hero"
      - "Long subhead (>2 sentences)"

  product_screenshot:
    structure: "Copy + dominant UI mock / device frame (split or stacked)"
    imagery_type: product_ui
    scene_catalog_eligible: false
    default_for_brand_types: [saas, fintech, b2b_software]
    quality_cues:
      - "Realistic product data in screenshot"
      - "Optional 5-10s loop demo"
    avoid:
      - "Fake lorem UI"
      - "Decorative illustration replacing product"

  abstract_gradient_3d:
    structure: "Centered or split copy on mesh/gradient/shader background"
    imagery_type: generative_abstract
    scene_catalog_eligible: false
    default_for_brand_types: [ai_startup, dev_tools, tech_agency]
    quality_cues:
      - "≤2 accent colors; subtle motion only"
    avoid:
      - "Gradient masking weak value prop"

  bento_hero:
    structure: "CSS grid of 4-8 cells; one 2×2 anchor cell"
    imagery_type: mixed_per_cell
    scene_catalog_eligible: partial  # photo cells only
    default_for_brand_types: [multi_feature_saas, dev_tools, ai_platform]
    quality_cues:
      - "One anchor cell; one sentence per cell"
      - "Anchor first on mobile"
    avoid:
      - "Equal two-column masquerading as bento"
      - "Paragraphs in 1×1 cells"

  typographic_no_image:
    structure: "Display type + minimal chrome; optional rule/icon accent"
    imagery_type: none
    scene_catalog_eligible: false
    default_for_brand_types: [portfolio, creative_agency, editorial]
    quality_cues:
      - "clamp() type scale; tight display tracking"
    avoid:
      - "Category descriptions instead of value prop"

  illustration_hero:
    structure: "Split or centered with custom illustration anchor"
    imagery_type: illustration
    scene_catalog_eligible: false
    default_for_brand_types: [edtech, playful_saas, wellness_startup]
    quality_cues:
      - "Consistent illustration system matching brand"
    avoid:
      - "Generic clip-art / undraw aesthetic"

# Resolution layer (deterministic lookup — analogous to INDUSTRY_VISUAL_TRIAD)
BRAND_TYPE_DEFAULT_LAYOUT:
  local_service: split_copy_image
  home_services: split_copy_image
  professional_services: split_copy_image
  healthcare: split_copy_image
  saas: product_screenshot
  ai_platform: centered_copy_cta
  dev_tools: bento_hero
  ecommerce: full_bleed_photo_overlay
  creative_portfolio: typographic_no_image
  restaurant: full_bleed_photo_overlay

# When layout is photo-eligible, THEN resolve scene_archetype from existing SCENE_CATALOG
PHOTO_LAYOUTS: [split_copy_image, full_bleed_photo_overlay]
```

### Integration note (Arthor pipeline)

```
brand_signals + industry
    → resolve_layout_archetype()     # NEW — this research
    → if photo-eligible:
          resolve_scene_archetype()  # existing SCENE_CATALOG
          → image generation
      elif product_ui:
          skip photo gen; use UI capture pipeline
      elif abstract / none:
          skip photo gen; CSS/token background
```

Today’s `hero_job` (trust / experience / outcome) maps to **copy tone** and **scene archetype**, not layout. **`hero_job` + `layout_archetype`** are orthogonal: e.g. dental + `split_copy_image` + `threshold_invitation` vs dental + `full_bleed_photo_overlay` + `confident_smile`.

---

## References

- Hero layouts: https://spell.sh/blog/hero-section-best-practices · https://www.expressjs.org/how-to-design-a-hero-section-that-converts-layout-copy-and-cta-best-practices/ · https://blog.logrocket.com/ux-design/hero-section-examples-best-practices/
- Bento: https://www.pravinkumar.co/blog/bento-box-hero-sections-webflow-design-2026 · https://brainy.ink/paper/bento-grid-design
- Local service: https://coynelabs.com/insights/hero-section-anatomy · https://www.nopio.com/blog/hvac-website-design/ · https://rise.co/blog/cro-tactics-that-move-the-needle-saas-vs-d2c-vs-local-service
- Section anatomy: https://www.betterlaunch.co/blog/saas-landing-page · https://ui-incubator.com/en/blog/saas-landing-page-sections · https://spell.sh/blog/landing-page-sections
- Libraries: https://resources.relume.io/resources/docs/how-to-use-the-relume-webflow-library · https://tailwindcss.com/plus/ui-blocks/marketing · https://ui.shadcn.com/blocks · https://21st.dev/ · https://flowbite.com/blocks/ · https://www.untitledui.com/react · https://heropatterns.com/
- Licensing: https://www.relume.io/legal/licensing-agreement · https://tailwindcss.com/plus/ui-blocks · https://github.com/themesberg/flowbite/ · https://www.untitledui.com/license
- Arthor scene catalog (internal): `app/style/hero_visual_strategy.py` · `plan/HANDOFF-HERO-VISUAL-STRATEGY.md`
