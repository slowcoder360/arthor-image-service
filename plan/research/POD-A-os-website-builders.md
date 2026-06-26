# POD-A: One-Shot Website Builder Research

**Date:** 2025-06-25  
**Scope:** Web research only. Applicable to Arthor's hero taste corpus + layout-archetype gap.  
**Question:** How do leading systems decide what a hero/section looks like, and what should Arthor steal?

---

## Executive Summary

The best one-shot builders **do not freeform-generate full pages**. They run a **pipeline**: brief → page/section plan → **layout archetype selection from a curated library** → content fill → imagery slot → assembly. Taste comes from **human-designed component catalogs**, **design tokens**, and **constrained schemas**—not from the LLM inventing layout from scratch.

Arthor's blind spot is real: a photographic hero corpus keyed on industry + scene archetype assumes **one layout primitive** (full-bleed human photo + overlaid copy). Competitors explicitly model **layout as a first-class axis** (split, centered, gradient, product-screenshot, typographic) *before* imagery selection.

**Strongest open-source taxonomies to learn from:** [craigdanielk/web-builder](https://github.com/craigdanielk/web-builder) (25 section archetypes, 99+ variants), [buildingopen/openpage](https://github.com/buildingopen/openpage) (19 block types × 42 layout variants, MIT), [opensite-ai/opensite-ui](https://github.com/opensite-ai/opensite-ui) (semantic block registry, Apache-2.0). **Strongest commercial reference:** [Relume](https://www.relume.io/) (1,500+ human-designed sections; AI picks from library via section-level prompts).

---

## Per-System Analysis

### v0 (Vercel)

| | |
|---|---|
| **What it does** | Prompt → production React/Next.js + Tailwind + shadcn/ui components. Composite model with RAG over docs, curated code examples, autofixers. |
| **Layout decision** | **Freeform code generation**, but heavily steered by **shadcn/ui primitives** and retrieved UI patterns. No explicit "pick hero variant #7" step—intent parsing maps prompt → component tree. Users prompt layout explicitly ("two-column hero, image right"). |
| **Taste source** | Fine-tuned on UI patterns; shadcn/ui + Radix defaults; dynamic system prompt; example filesystem for SDK patterns. |
| **Open source** | shadcn/ui: **MIT** ([github.com/shadcn-ui/ui](https://github.com/shadcn-ui/ui)). v0 itself: closed. |
| **Layout/content/imagery split** | **Weak explicit split.** Single generation pass produces layout + copy + placeholder images together. Quality = component library + prompting discipline. |

**URLs:** [How we made v0 an effective coding agent](https://vercel.com/blog/how-we-made-v0-an-effective-coding-agent), [v0 composite model family](https://vercel.com/blog/v0-composite-model-family), [shadcn/ui docs](https://ui.shadcn.com/docs)

---

### Lovable

| | |
|---|---|
| **What it does** | AI agent builds full-stack React/Tailwind apps from chat. Plan mode + Build mode. |
| **Layout decision** | **Section-by-section prompting**, not whole-page generation. Docs explicitly recommend building "hero → proof → features → CTA" as separate blocks. Layout via structural language: "two-column, left image, right text block with CTA." |
| **Taste source** | User "Custom knowledge" blueprint; global component consistency (nav, cards, buttons); Builder.io Figma import for visual reference. |
| **Open source** | Closed. Output is standard React/Tailwind (exportable via GitHub). |
| **Layout/content/imagery split** | **Moderate.** User separates concerns by prompting one section at a time with explicit layout + real copy. Images attached to chat for inspiration. |

**URLs:** [Prompting best practices](https://docs.lovable.dev/prompting/prompting-one), [Quick start](https://docs.lovable.dev/introduction/getting-started), [UI tactics guide](https://lovable-cheat-sheet.lovable.app/)

---

### Bolt.new (StackBlitz)

| | |
|---|---|
| **What it does** | Browser-based full-stack app builder (WebContainers). Prompt-first; optional starter templates (Astro blog, shadcn scaffold, Expo, etc.). |
| **Layout decision** | **Mostly freeform** from natural-language spec. Optional **Design System** picker injects real component library before first prompt. Figma import for structure. |
| **Taste source** | Pre-loaded design systems; user's own design system upload; shadcn when scaffolded. Max agent for design-system fidelity. |
| **Open source** | WebContainers/open tooling partially open; Bolt product closed. |
| **Layout/content/imagery split** | **Weak by default; strong when design system attached.** Design system mode forces component-by-name selection ("Add PrimaryButton in header"). |

**URLs:** [Intro to Bolt](https://stackblitz.mintlify.app/building/intro-bolt), [Use your design system](https://stackblitz.mintlify.app/building/design-system/use-design-system)

---

### Framer AI / Wireframer / Agents

| | |
|---|---|
| **What it does** | Visual site builder. Wireframer (W) generates layout skeletons; Framer Agents build/edit on canvas; Workshop for components. |
| **Layout decision** | **Prompt-specified sections** on canvas stacks. Wireframer: "structure, not style"—nav, hero, feature cards, footer as editable Framer layers. Agents accept layout commands ("change hero to vertical stack", "horizontal stack with bigger images"). Preset layout types (Landing, About, Blog). |
| **Taste source** | Framer's design system (site colors/fonts inherit); human-editable canvas; `/` skills for focused actions. |
| **Open source** | Closed. |
| **Layout/content/imagery split** | **Moderate.** Wireframer generates structure + placeholder copy; user swaps images/colors on canvas. Layout and content co-generated but independently editable. |

**URLs:** [Framer AI](https://www.framer.com/ai/), [Wireframer update](https://www.framer.com/updates/wireframer), [Wireframer Academy](https://www.framer.com/academy/lessons/generating-layouts-with-ai-using-wireframer), [Framer Agents help](https://www.framer.com/help/articles/how-to-build-a-website-from-scratch-with-framer-agents/)

---

### Webflow AI Site Builder + AI Assistant

| | |
|---|---|
| **What it does** | Two-phase: (1) AI site builder → multi-page structure + design system; (2) AI Assistant → section generation in Designer. |
| **Layout decision** | **Explicit two-step:** First, **page → section list** (hero, features, gallery, testimonials…). User can add/remove/reorder sections and **swap section layouts** before "Generate design." In Designer, drag Section → AI icon → pick from generated layout options. |
| **Taste source** | Generated **foundational design system** (classes, variables, theme). New sections inherit existing styles. |
| **Open source** | Closed. |
| **Layout/content/imagery split** | **Strong for structure, weak for images.** IA (pages/sections) separated from visual design generation. AI Assistant explicitly excludes components, images, dynamic data from first draft. |

**URLs:** [AI site builder help](https://help.webflow.com/hc/en-us/articles/38840145286035-Build-a-site-with-Webflow-s-AI-site-builder), [AI Assistant for sections](https://help.webflow.com/hc/en-us/articles/34205154436243-Modify-page-designs-with-the-Webflow-AI-Assistant), [AI site builder evolved](https://webflow.com/updates/ai-site-builder-evolved)

---

### Durable

| | |
|---|---|
| **What it does** | 30-second SMB website from 3 questions (industry, name, location). All-in-one (CRM, invoicing, AI copy). |
| **Layout decision** | **Industry → template + section catalog.** Pre-built templates mapped to business type. Modular **section types**: Banner, CTA, Feature, Pricing, FAQ, Contact, Embed, Text, etc. "Change Template" remaps content to new layout; "Regenerate" rebuilds site. |
| **Taste source** | Conversion-optimized templates; industry-specific defaults; limited customization (colors, fonts, section order). |
| **Open source** | Closed. |
| **Layout/content/imagery split** | **Moderate.** Template = layout skeleton; AI fills industry copy + stock images. Sections regeneratable independently. |

**URLs:** [AI website builder](https://durable.com/ai-website-builder), [Working with sections](https://help.durable.com/en/collections/18410094-working-with-sections)

---

### Relume AI Site Builder + Library

| | |
|---|---|
| **What it does** | AI sitemap → wireframes → style guide → export to Figma/Webflow/React. **Not a finished site builder**—a planning/wireframing accelerator. |
| **Layout decision** | **Best-in-class explicit selection.** Three-stage: (1) AI proposes pages + sections from company prompt; (2) **Section title + description = section-level prompt** → AI picks component from 1,000+ library; (3) Manual swap/variant pick in wireframe view. Filters: column count, content type, interactions. |
| **Taste source** | **1,500+ human-designed components** (Marketing / E-commerce / Application UI). Client-First CSS naming. Hero Header alone: **127+ variants**. Naming: `Category-Style-Number` (e.g., Hero-Split-01). |
| **Open source** | Library: **proprietary** (paid). React export available to subscribers. Site Builder AI: closed. |
| **Layout/content/imagery split** | **Strongest commercial example.** Sitemap (IA) → component (layout) → copy (content) are linked but independently editable. Wireframes use real components, unstyled, with AI copy. Images are placeholders until export. |

**Section taxonomy (top level):**
- **Marketing:** Hero Header, Feature, Navbar, Footer, CTA, Testimonial, Pricing, FAQ, Contact, Team, Stats, Logo, Blog, Gallery, Content, Timeline, etc.
- **E-commerce:** Product lists, category previews, checkout-adjacent blocks
- **Application UI:** Dashboards, settings, auth (for web-app prototypes)

**Hero sub-styles (from library + filters):** centered, split (image left/right), full-bleed/video background, product-screenshot, off-grid/asymmetric, minimal text, animated.

**URLs:** [Relume homepage](https://www.relume.io/), [Building a sitemap with AI](https://www.relume.io/resources/docs/building-a-sitemap-with-ai), [Wireframe editing](https://www.relume.io/resources/docs/how-to-create-and-edit-wireframes-in-the-relume-site-builder), [Hero Header library](https://www.relume.io/categories/hero-header-sections), [Webflow integration](https://webflow.com/integrations/relume)

---

### Replit Agent / Design Mode / Canvas

| | |
|---|---|
| **What it does** | Natural-language full-stack app builder. Design Mode for marketing sites; Canvas for visual mockup iteration before code commit. |
| **Layout decision** | **Freeform prompt** with conversational refinement. Canvas adds mockup frames separate from live app. Edit mode for element-level changes. |
| **Taste source** | Agent defaults to "sensible, professional" layouts; custom instructions/skills for brand rules; Figma import. |
| **Open source** | Replit platform closed; generated code is user's. |
| **Layout/content/imagery split** | **Moderate via Canvas.** Mockups experiment with layout before applying to app. Otherwise single-pass generation. |

**URLs:** [AI website builder use case](https://replit.com/usecases/ai-website-builder), [Design Canvas docs](https://docs.replit.com/learn/design/canvas)

---

### shadcn/ui + Blocks Registry

| | |
|---|---|
| **What it does** | Copy-paste component distribution platform. **Blocks** = full page sections (dashboards, sidebars, login pages). v0/Magic MCP consume registry. |
| **Layout decision** | **Pre-built blocks, not AI-selected.** Registry items tagged by `categories` (e.g., `hero`, `sidebar`, `dashboard`). CLI: `npx shadcn add [block]`. AI tools retrieve matching blocks via RAG/registry search. |
| **Taste source** | Radix primitives + Tailwind + "beautiful defaults." Open code for LLM consumption. |
| **Open source** | **MIT** — full registry, blocks, CLI. |
| **Layout/content/imagery split** | **Blocks = layout templates.** Content is inline mock data; user/AI replaces text. Images are placeholders. |

**Block types observed:** `registry:block` for page sections; categories filter in `getAllBlocks()`. Community registries (e.g., shadcnspace) extend with hero-01, hero-02, pricing-01, etc.

**URLs:** [shadcn blocks](https://ui.shadcn.com/blocks), [Registry schema](https://ui.shadcn.com/docs/registry/registry-json), [GitHub shadcn-ui/ui](https://github.com/shadcn-ui/ui)

---

### Tailwind Plus (formerly Tailwind UI)

| | |
|---|---|
| **What it does** | 500+ professionally designed HTML/React/Vue components + site templates (Salient, Radiant, etc.) + Catalyst UI kit. |
| **Layout decision** | **Pure catalog—no AI.** Developers pick from named layout variants per section type. |
| **Taste source** | Tailwind Labs design team. Gold standard for marketing layout naming. |
| **Open source** | **Proprietary.** One-time license (~$299 personal). Cannot redistribute or build competing UI libraries/page builders. |
| **Layout/content/imagery split** | **Fully separated by design.** Components are layout+styling; content is placeholder lorem; images are separate assets. |

**Marketing section taxonomy:**
- Hero Sections, Feature Sections, CTA, Bento Grids, Pricing, Header, Newsletter, Stats, Testimonials, Blog, Contact, Team, Content, Logo Clouds, FAQs, Footers

**Hero layout variants (named):**
- Simple centered
- Split with screenshot / bordered screenshot / code example / image
- Simple centered with background image
- With app screenshot / bordered app screenshot
- With angled image on right
- With image tiles / offset image

**URLs:** [Tailwind Plus](https://tailwindcss.com/plus), [Hero sections catalog](https://tailwindcss.com/plus/ui-blocks/marketing/sections/heroes), [Tailwind Plus rebrand blog](https://tailwindcss.com/blog/tailwind-plus)

---

### 21st.dev

| | |
|---|---|
| **What it does** | Community registry of React/Tailwind/shadcn components. Magic MCP for IDE integration ("v0 in your IDE"). Also: Screens (reference UI from Stripe/Linear/Notion), Themes. |
| **Layout decision** | **Browse/search catalog** or Magic MCP semantic search. Categories by component type (heroes, navbars, pricing, etc.). |
| **Taste source** | Designer-contributed components; curated quality guidelines. |
| **Open source** | Components: **MIT**. Registry CLI: **MIT** ([github.com/21st-dev/registry](https://github.com/21st-dev/registry)). Magic MCP: freemium. |
| **Layout/content/imagery split** | Components = layout; copy/images are demo props. |

**URLs:** [21st.dev community docs](https://help.21st.dev/community), [21st registry GitHub](https://github.com/21st-dev/registry)

---

## Open-Source & Learnable Taxonomies

| Project | License | What to steal | Block/section model |
|---------|---------|---------------|---------------------|
| [shadcn-ui/ui](https://github.com/shadcn-ui/ui) | MIT | Registry schema, `categories` tagging, block vs component types | `registry:block` with categories array |
| [21st.dev / registry](https://github.com/21st-dev/registry) | MIT | Community component distribution, MCP integration | shadcn-compatible registry |
| [buildingopen/openpage](https://github.com/buildingopen/openpage) | MIT | **Block × variant matrix** closest to what Arthor needs | 19 types × named variants (hero: centered, split, gradient, minimal) |
| [craigdanielk/web-builder](https://github.com/craigdanielk/web-builder) | Open | **Section taxonomy doc**—25 archetypes, 99+ variants, industry presets | HERO variants: centered, split-image, video-background, full-bleed-overlay, minimal-text, animated-gradient, editorial, product-hero |
| [opensite-ai/opensite-ui](https://github.com/opensite-ai/opensite-ui) | Apache-2.0 | Semantic block registry for AI-driven selection | Categories: hero, features, cta, testimonials, pricing, faq, contact, gallery, etc. + semantic tags |
| [mainzcript/ujl](https://github.com/mainzcript/ujl) | MIT | Content/design separation enforced in JSON schema | Brand-compliant layout JSON |
| [adrianwedd/grid2_repo](https://github.com/adrianwedd/grid2_repo) | — | Deterministic beam-search section assembly | Tone-aware section library + algorithmic picker |
| [avocadostudio-ai/avocado](https://github.com/avocadostudio-ai/avocado) | — | 20 Zod-schemas blocks, AI edits via structured ops | Hero, FeatureGrid, FAQ, CTA, etc. |
| [crediblemark/build-ui](https://github.com/crediblemark-official/credbuild) | MIT | 45+ thematic blocks for page builders | Hero, nav, features, accordion, footer |

**Not open (but taxonomy-reference-worthy):** Relume (1,500+ sections), Tailwind Plus (500+ components), Durable section catalog, Webflow section swap UX.

---

## Architectural Question: Layout vs Content vs Imagery

### Pattern A — Pipeline with explicit stages (best quality)

Used by: **Relume, Webflow AI, OpenPage, generative-page-pipeline skill, web-builder**

```
Brief → Page IA → Section plan → Layout archetype pick → Content generation → Image slot fill → Assembly
```

| Stage | Relume example | Webflow example |
|-------|----------------|-----------------|
| Layout | Section description → component from 1,000+ library | Section list → layout swap → "Generate design" |
| Content | AI copy per wireframe text element; "Ask AI" rewrite | Contextual copy during site generation |
| Imagery | Placeholder boxes; replaced at export | Explicitly excluded from AI Assistant first draft |

### Pattern B — Section-by-section prompting (good quality, user-driven)

Used by: **Lovable, Framer Agents, Bolt (with design system)**

User/agent prompts one section with explicit layout language + real copy. Images attached separately.

### Pattern C — Freeform single-pass (fastest, most "slop")

Used by: **v0 default, Replit default, Bolt default**

LLM generates layout + content + placeholders together. Quality depends on component library bias (shadcn) and prompt specificity.

### Pattern D — Deterministic assembly (most predictable)

Used by: **grid2 (beam search), OpenPage (typed schema), Durable (template remap)**

Algorithm picks from finite variant set; AI only for understanding/intent, not layout invention.

---

## Smallest Set of "Moves" (Generic → Credible)

Synthesized from tool docs, web-builder taxonomy, and builder pipeline analyses:

1. **Constrain layout before content.** Pick section archetype + variant from a finite registry. Never ask LLM to invent page structure in one shot. (Relume, Lovable, web-builder, Webflow)

2. **Industry → page set → section sequence preset.** Plumber ≠ SaaS ≠ dental. Different IA, not just different words. (Webflow multi-page, web-builder presets, Durable industry templates)

3. **Separate hero *layout archetype* from hero *imagery archetype*.** Split-copy+abstract-right and full-bleed-photo are different layout primitives; imagery corpus attaches to slots within layout. (Tailwind Plus hero naming, web-builder HERO variants, OpenPage hero variants)

4. **Design tokens restated every section.** Compact style header (colors, radius, spacing, font scale) injected into every generation pass prevents visual drift. (web-builder compact style header)

5. **Real copy early; no lorem ipsum.** Layout decisions improve with actual headline length and CTA count. (Lovable docs explicit on this)

6. **Curated component library > generated CSS.** Relume's 1,000+ human components; shadcn defaults; Tailwind Plus. AI selects/composes; humans designed the parts.

7. **One global chrome pass first.** Nav, footer, button styles, spacing grid before page sections. (Lovable tactics, Tailwind Catalyst)

8. **Image slots typed by role.** `hero-background`, `hero-side-media`, `product-screenshot`, `abstract-gradient`, `team-photo`, `logo-strip`—not generic "image." (Tailwind hero variants, Relume filters)

9. **Swap/regenerate at section granularity.** Fix one block without rerolling entire page. (Relume component swap, Durable section regenerate, Webflow section swap)

10. **Deterministic fallbacks.** When AI pick fails, default to industry-appropriate layout variant from preset—not random generation. (grid2 beam search, OpenPage typed schema)

---

## What Arthor Should Steal

Mapped directly to the hero taste corpus + layout-archetype gap.

### 1. Add `layout_archetype` as a peer axis to `scene_archetype`

The corpus today: `industry × scene_archetype × hero_job × authenticity_mode` → photo.  
Missing dimension: **how the hero is composed on the page.**

Minimum viable hero layout archetypes (from Tailwind + web-builder + OpenPage convergence):

| Layout archetype | When | Imagery slot |
|------------------|------|--------------|
| `full_bleed_overlay` | Local services, trust/outcome (current default) | Background photo + gradient scrim |
| `split_copy_media` | SaaS, agency, professional services | Side media: photo, abstract, or UI screenshot |
| `centered_typographic` | Premium/minimal brands | Optional small accent image or none |
| `gradient_abstract` | Tech, AI, startup | Generated abstract/mesh; no people |
| `product_screenshot` | Software, tools | Product UI in device frame |
| `split_with_proof_strip` | High-conversion local | Photo + logos/stats/rating strip |

**Steal from:** [web-builder HERO variants](https://github.com/craigdanielk/web-builder/blob/main/skills/section-taxonomy.md), [Tailwind hero catalog](https://tailwindcss.com/plus/ui-blocks/marketing/sections/heroes), [OpenPage hero variants](https://github.com/buildingopen/openpage)

### 2. Run Relume's three-stage pipeline, not one-shot page gen

```
Industry brief → page/section IA → layout archetype per section → copy → imagery slot fill
```

Arthor already has deterministic imagery for one layout. Extend the pipeline so **layout selection happens before image lookup**. Section title + description as prompt (Relume's "section prompt" pattern).

**Steal from:** [Relume sitemap docs](https://www.relume.io/resources/docs/building-a-sitemap-with-ai)

### 3. Build a `hero_layout_corpus` parallel to `hero_taste_corpus`

Photo corpus: *what* to show.  
Layout corpus: *how* to frame it—component templates per layout archetype, responsive rules, copy zone geometry, media aspect ratios.

Start with 6–8 layout archetypes × 2–3 variants each (~15–20 templates). Match Relume's "Category-Style-Number" naming: `hero-split-01`, `hero-centered-01`.

### 4. Map industry → default hero layout (not just default photo)

| Industry cluster | Default hero layout | Why |
|------------------|---------------------|-----|
| Dental, legal, HVAC, home services | `full_bleed_overlay` | Trust via people + place (current corpus) |
| SaaS, AI tools, dev agencies | `split_copy_media` or `product_screenshot` | Show product or abstract capability |
| Premium/luxury services | `centered_typographic` | Restraint signals quality |
| Tech startups | `gradient_abstract` | Avoid uncanny stock humans |

Override via `hero_job` (trust → people; outcome → product/result; experience → abstract/mood).

### 5. Type image slots by layout, not by section

Replace implicit "hero background photo" with explicit slots:

```yaml
slots:
  - id: hero_media_primary
    role: side_media | background | product_frame | abstract
    aspect: 4:3 | 16:9 | 1:1 | full
    corpus_key: industry.scene.job  # only for photographic roles
```

Non-photographic slots (`abstract`, `product_frame`) bypass taste corpus; use gradient presets or client assets.

**Steal from:** Webflow AI Assistant (no images in first draft), Tailwind hero variant naming

### 6. Adopt OpenPage's block × variant schema for all sections

Extend beyond hero to full page:

- 19 block types, 42 variants (OpenPage)
- 25 section archetypes (web-builder)

Arthor page builder should emit JSON matching this shape before any React render. Enables diffing, versioning, deterministic regen.

### 7. Industry presets = section sequence + default layout variants + style header

web-builder's preset pattern: each industry gets ordered section list + compact 6-line style header restated per section. Arthor's brand packet already has colors/fonts—formalize as injected style header.

### 8. Use semantic tags for AI layout selection (OpenSite pattern)

Each layout template carries tags: `split`, `two-column`, `saas`, `local-service`, `trust`, `conversion`, `minimal`, `has-screenshot-slot`. AI/intent classifier picks from tagged registry, not freeform.

**Steal from:** [opensite-ai/opensite-ui](https://github.com/opensite-ai/opensite-ui) block registry concept

### 9. Section-level swap/regenerate UX (don't reroll site)

Match Durable/Relume/Webflow: operator can swap `hero-split-02` → `hero-centered-01` keeping copy, or regenerate copy keeping layout. Critical for one-shot + refinement workflow.

### 10. Learn taxonomy; don't copy proprietary components

- **MIT-safe to study/adapt:** shadcn blocks schema, OpenPage variant matrix, web-builder taxonomy, 21st.dev patterns
- **Reference only (license restricted):** Tailwind Plus (no redistribution in builder), Relume library (proprietary)
- **Implement Arthor-native templates** informed by Tailwind/Relume naming, not copied markup

---

## Competitive Landscape Summary Table

| System | Layout selection | Taste source | OSS library? | Layout/content/image split |
|--------|------------------|--------------|--------------|----------------------------|
| v0 | Freeform + shadcn bias | shadcn, RAG, fine-tune | shadcn MIT | Weak |
| Lovable | Section prompts | Custom knowledge, globals | No | Moderate (user-driven) |
| Bolt | Freeform / design system | DS injection | No | DS mode: strong |
| Framer | Wireframer + canvas | Framer DS | No | Moderate |
| Webflow AI | Section list → layout swap | Generated DS | No | Strong (structure) |
| Durable | Industry template + sections | Templates | No | Moderate |
| **Relume** | **AI picks from 1,500+ library** | **Human components** | No (paid) | **Strong** |
| Replit | Freeform / Canvas | Agent defaults | No | Moderate |
| shadcn blocks | Registry pick | MIT defaults | **MIT** | Blocks = layout |
| Tailwind Plus | Manual catalog | Tailwind Labs | No (paid) | Full separation |
| 21st.dev | Search/MCP | Community | **MIT** | Component-level |
| OpenPage | Block × variant schema | Theme presets | **MIT** | **Strong** |
| web-builder | Taxonomy + presets | Style header | Open | **Strong** |

---

## Key URLs (Quick Reference)

- v0 pipeline: https://vercel.com/blog/how-we-made-v0-an-effective-coding-agent
- Lovable prompting: https://docs.lovable.dev/prompting/prompting-one
- Bolt design systems: https://stackblitz.mintlify.app/building/design-system/use-design-system
- Framer Wireframer: https://www.framer.com/updates/wireframer
- Webflow AI builder: https://help.webflow.com/hc/en-us/articles/38840145286035
- Relume sitemap AI: https://www.relume.io/resources/docs/building-a-sitemap-with-ai
- Relume hero library: https://www.relume.io/categories/hero-header-sections
- shadcn blocks: https://ui.shadcn.com/blocks
- Tailwind Plus heroes: https://tailwindcss.com/plus/ui-blocks/marketing/sections/heroes
- 21st.dev: https://help.21st.dev/community
- OpenPage: https://github.com/buildingopen/openpage
- web-builder taxonomy: https://github.com/craigdanielk/web-builder/blob/main/skills/section-taxonomy.md
- AI builder pipeline analysis: https://webforger.ai/blog/how-ai-website-builders-actually-work/

---

## Bottom Line for Arthor

**One-shot quality is a selection problem, not a generation problem.** The systems that look best constrain layout early, fill content into typed slots, and attach imagery last—using either a curated photo corpus (Arthor's strength) or non-photo media types (Arthor's gap).

Launch-blocking fix: **decouple hero layout archetype from hero imagery archetype.** The taste corpus remains valuable for `full_bleed_overlay` and photographic `split_copy_media` slots—but SaaS/agency/tech sites need `split_copy_media`, `gradient_abstract`, and `product_screenshot` layouts that never touch the human-photo corpus at all.
