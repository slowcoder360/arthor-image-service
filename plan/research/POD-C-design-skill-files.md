# POD-C: AI Web Design Skill Files & Anti-Slop Research

**Date:** 2026-06-25  
**Scope:** Web research only — catalog public skill files, system prompts, and rubrics for AI web design quality; synthesize rules; map to Arthor’s StyleProfile + proposed layout-archetype layer.  
**Arthor context:** Image-service resolves a **photographic** `StyleProfile` per pack (palette, lighting, composition, `do_not`, etc.) and serves hero plates via `hero_taste_corpus` (`scene_archetype`, `hero_job`). A downstream builder assembles the site. UI taste rules must not be conflated with image taste rules.

---

## 1. Catalog — best public skill files / prompts / rubrics

| Name | Source | License | What it's for |
|------|--------|---------|---------------|
| **frontend-design** | [anthropics/skills/skills/frontend-design/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) | Apache-2.0 (example skills per repo README) | Official Anthropic skill: distinctive UI, typography pairing, two-pass design plan before code, hero-as-thesis, anti-default self-critique |
| **web-artifacts-builder** | [anthropics/skills/skills/web-artifacts-builder/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/web-artifacts-builder/SKILL.md) | Apache-2.0 | React + Tailwind + shadcn artifact stack; explicit “avoid AI slop” list (centered layouts, purple gradients, uniform radii, Inter) |
| **Agent Skills spec + template** | [anthropics/skills/spec](https://github.com/anthropics/skills/tree/main/spec), [template-skill](https://github.com/anthropics/skills/tree/main/template) | Apache-2.0 | Portable `SKILL.md` format (YAML frontmatter + markdown instructions) |
| **anti-slop-design** | [Cuuper22/anti-slop-design](https://github.com/Cuuper22/anti-slop-design) | MIT | Full anti-slop system: 5-step Design Thinking Protocol, 15-rule checklist, 8 domain profiles (`domain-map.json`), platform refs (`references/web-landing.md`), templates + CSS token assets |
| **taste-design** | [google-labs-code/stitch-skills/plugins/stitch-utilities/skills/taste-design](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/taste-design) | Apache-2.0 | Generates premium `DESIGN.md` for Google Stitch: typography bans, asymmetric heroes, motion philosophy, explicit NEVER-DO anti-patterns |
| **design-md** | [google-labs-code/stitch-skills/skills/design-md](https://github.com/google-labs-code/stitch-skills/tree/main/skills/design-md) | Apache-2.0 | Extract semantic design system from existing Stitch screens → `DESIGN.md` source of truth |
| **enhance-prompt** | [google-labs-code/stitch-skills/plugins/stitch-utilities/skills/enhance-prompt](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/enhance-prompt) | Apache-2.0 | Turns vague UI requests into structured Stitch prompts; injects `DESIGN.md` when present |
| **Refero Research-First Design** | Refero MCP skill (community; see [Refero](https://refero.design)) | Third-party / Refero ToS | Research-before-build methodology; `references/anti-ai-slop.md` indigo ban + screenshot test |
| **Anti-Slop Companion Prompt** | [Glenskii/Glenski-Toolkit/anti-slop-companion-prompt.md](https://github.com/Glenskii/Glenski-Toolkit/blob/main/anti-slop-companion-prompt.md) | Check repo (no SPDX in file) | Paste-in system prefix: mandatory **Design Declaration** block before any code |
| **Anti-Slop Prompt Template (2026)** | [Sailop blog](https://sailop.com/blog/anti-slop-prompt-template-2026) | Blog / methodology | Named visual archetypes, concrete pattern bans, self-audit close; cites 9 layout archetypes in companion guide |
| **AI Slop Definitive Guide (2026)** | [Sailop blog](https://sailop.com/blog/ai-slop-definitive-guide-2026) | Blog / methodology | 7-dimension slop model; procedural design-system layer; hero→features→3-card fingerprint |
| **Design System Approach (Claude Design)** | [MindStudio](https://www.mindstudio.ai/blog/claude-design-avoid-ai-slop-design-system) | Blog | Markdown design-system doc: typography, hex roles, spacing base unit, component + layout rules, negative constraints |
| **v0 system prompt (leaked)** | [leaked-system-prompts.com/v0](https://leaked-system-prompts.com/prompts/v0/v0_20250428), [dontriskit/awesome-ai-system-prompts/v0](https://github.com/dontriskit/awesome-ai-system-prompts) | No license (leaked); aggregator MIT | shadcn/ui default stack, semantic Tailwind tokens, avoid indigo/blue unless specified, `<Thinking>` before Code Project, responsive + lucide icons |
| **Lovable Agent Prompt** | [x1xhlol/system-prompts-and-models-of-ai-tools/Lovable/Agent Prompt.txt](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Lovable/Agent%20Prompt.txt) | GPL-3.0 (repo) | React/Vite/Tailwind/shadcn; **design system is everything** — semantic tokens in `index.css`, no raw `text-white`, customize shadcn variants |
| **Bolt project prompt template** | [Bolt support — Prompting effectively](https://support.bolt.new/best-practices/prompting-effectively) | StackBlitz docs | Example `.bolt/prompt`: “beautiful, not cookie cutter”; shadcn + lucide + Unsplash; user-editable project/system prompts |
| **awesome-ai-system-prompts** | [dontriskit/awesome-ai-system-prompts](https://github.com/dontriskit/awesome-ai-system-prompts) | MIT | Curated v0, Lovable, same.new, Manus, etc. + prompt-engineering guide |
| **awesome-agent-skills** | [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | MIT | Index of 1000+ skills including Anthropic, Google Labs Stitch, Microsoft design review |
| **shadcn/ui theming** | [ui.shadcn.com/docs/theming](https://ui.shadcn.com/docs/theming), [Vercel Academy — globals.css](https://examples.vercel.com/academy/shadcn-ui/exploring-globals-css) | MIT (shadcn) | Semantic CSS variables (`background`, `primary`, `radius`); OKLCH guidance; **defaults are not a finished design** |
| **landing-page-optimization** | Arthor builder-os skill (internal) | Internal | Conversion + section **tone rhythm** (`paper` / `wash` / `dark`); hero clarity; not slop-focused but complements layout variety |

**Notable omissions / caution**

- **Leaked product prompts** (v0, Lovable, Bolt internals): useful for *reading* patterns; **GPL-3.0** (x1xhlol) and no license on leaks → do not ship verbatim in Arthor product; extract rules only.
- **Microsoft frontend-design-review**: listed in VoltAgent index; public path unverified at research time — treat as secondary until linked.
- **Impeccable (Vercel Labs)**: referenced in community lists; no stable public `SKILL.md` URL found.

---

## 2. Distilled anti-slop design rules (synthesized checklist)

Cross-source consensus on what “good” means and what to ban.

### A. Process gates (apply before generation)

- [ ] **Declare intent first** — Design Declaration / design plan / `<Thinking>`: aesthetic name, rejected defaults (≥3), typography pair, palette hex roles, layout strategy, one signature element ([Glenskii](https://github.com/Glenskii/Glenski-Toolkit/blob/main/anti-slop-companion-prompt.md), [Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md), [v0](https://leaked-system-prompts.com/prompts/v0/v0_20250428)).
- [ ] **Pick domain + visual archetype** — Match industry/job (SaaS vs local service vs editorial); commit to ONE named archetype (Bauhaus, brutalist editorial, Swiss minimal, terminal/HUD, etc.) — half-measures collapse to centroid ([Sailop](https://sailop.com/blog/anti-slop-prompt-template-2026), [anti-slop-design Step 1–2](https://github.com/Cuuper22/anti-slop-design)).
- [ ] **Uniqueness review** — Before code: “Would a similar prompt produce the same plan?” Revise if yes ([Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)).
- [ ] **Self-audit after build** — List 3 AI tells + fixes ([Sailop](https://sailop.com/blog/anti-slop-prompt-template-2026), [Refero anti-ai-slop checklist](https://refero.design)).

### B. Typography

- [ ] **No default AI fonts as primary** — Inter, Roboto, Poppins, Geist-as-only-face, system-ui stacks flagged repeatedly.
- [ ] **Display + body pair deliberately** — Weight/width/spacing create hierarchy, not size alone.
- [ ] **Fluid scale** — `clamp()` for headings; max ~65ch body measure ([Glenskii](https://github.com/Glenskii/Glenski-Toolkit/blob/main/anti-slop-companion-prompt.md), [Google taste-design](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/taste-design)).
- [ ] **Letter-spacing on caps/small labels** — Missing tracking = instant generic ([Refero](https://refero.design)).

### C. Color & contrast

- [ ] **Ban unjustified indigo/violet/purple-blue gradients** — #1 fingerprint ([Refero](https://refero.design), [v0 styling rule #3](https://leaked-system-prompts.com/prompts/v0/v0_20250306), [Google taste-design](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/taste-design)).
- [ ] **Semantic tokens, not raw utilities** — `bg-primary`, CSS variables; never ad-hoc `text-white` / `bg-white` in components ([Lovable prompt](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Lovable/Agent%20Prompt.txt), [shadcn theming](https://ui.shadcn.com/docs/theming)).
- [ ] **Off-white light / off-black dark** — Not `#FFFFFF` / `#000000` flats ([anti-slop-design Rules 4–5](https://github.com/Cuuper22/anti-slop-design)).
- [ ] **One accent, dominant + sharp** — Max one saturated accent; no rainbow equal distribution ([Google taste-design](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/taste-design)).

### D. Spacing & rhythm

- [ ] **Hierarchy through spacing** — Section gaps > card gaps > inline gaps; avoid uniform `16px` everywhere ([anti-slop-design Rule 10](https://github.com/Cuuper22/anti-slop-design)).
- [ ] **Section tone alternation** — Adjacent sections must not share the same background tone; use `paper` / `wash` / `dark` bands ([Arthor landing-page-optimization skill]).
- [ ] **Restraint** — Whitespace is structural; one bold signature element, quiet surround ([Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)).

### E. Layout & section variety

- [ ] **Ban Holy Trinity** — Centered hero → 3 equal feature cards → testimonial carousel → footer ([anti-slop-design Rule 3](https://github.com/Cuuper22/anti-slop-design), [Sailop](https://sailop.com/blog/ai-slop-definitive-guide-2026)).
- [ ] **Ban symmetric defaults** — Prefer 60/40 or 70/30 splits, bento, editorial columns, zig-zag ([Sailop](https://sailop.com/blog/anti-slop-prompt-template-2026), [anti-slop web-landing](https://github.com/Cuuper22/anti-slop-design/blob/main/references/web-landing.md)).
- [ ] **Domain-specific section order** — Local service ≠ SaaS template ([anti-slop web-landing § Section Anatomy](https://github.com/Cuuper22/anti-slop-design/blob/main/references/web-landing.md)).
- [ ] **No blob SVGs, gradient mesh heroes, floating dashboard mockups** unless brief demands ([Sailop](https://sailop.com/blog/anti-slop-prompt-template-2026)).

### F. Hero premium signals

- [ ] **Hero = thesis** — Most characteristic subject/world, not “big stat + gradient accent + sublabel” template ([Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)).
- [ ] **Match hero pattern to domain** — Full-bleed (emotional/visual trades), split 60/40 (SaaS/fintech/local pro), minimal text (devtools), video (creative) ([anti-slop web-landing § Hero Patterns](https://github.com/Cuuper22/anti-slop-design/blob/main/references/web-landing.md)).
- [ ] **Copy-safe image zones** — Text over low-detail areas; overlay/scrim when photo-led ([Arthor `slot.layout.safe_area`](app/style/prompts.py), [landing-page-optimization]).
- [ ] **One primary CTA** — No filler “scroll to explore” chevrons ([Google taste-design](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/taste-design)).
- [ ] **Real copy** — No lorem, no “Welcome to our amazing platform”, no fabricated metrics ([anti-slop-design Rules 12–14](https://github.com/Cuuper22/anti-slop-design), [Google taste-design](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/taste-design)).

### G. Components & motion (AI tells)

- [ ] **No universal `rounded-2xl` + `shadow-md`** on every surface ([Sailop](https://sailop.com/blog/anti-slop-prompt-template-2026)).
- [ ] **Radius from domain** — 2–4px fintech, 12–16px creative; vary by component size ([anti-slop-design Rule 6](https://github.com/Cuuper22/anti-slop-design)).
- [ ] **Motion: one orchestrated moment** — Not fade-in-on-scroll on everything; respect `prefers-reduced-motion` ([Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md), [Google taste-design](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/taste-design)).
- [ ] **Icons** — Lucide ok; Heroicons-on-everything flagged; editorial may use zero icons ([anti-slop-design Rule 9](https://github.com/Cuuper22/anti-slop-design), [v0](https://leaked-system-prompts.com/prompts/v0/v0_20250306)).
- [ ] **Voice** — Ban “elevate, seamless, leverage, robust, delve, tapestry” ([Sailop](https://sailop.com/blog/anti-slop-prompt-template-2026)).

### H. Accessibility floor (non-negotiable across quality skills)

- [ ] Responsive through mobile; 44px touch targets; visible focus; WCAG AA contrast ([Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md), [Google taste-design](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/taste-design)).

---

## 3. Hero design & layout-decision steps

| Source | Pre-generation layout step? | How heroes are chosen |
|--------|----------------------------|------------------------|
| **Anthropic frontend-design** | Yes — design plan with **Layout: one-sentence concept + ASCII wireframes**; revise if generic | Hero is “thesis”; warns against default cream/serif/terracotta, dark+acid-green, broadsheet clusters |
| **anti-slop-design** | Yes — 5-step protocol; Step 1 domain → Step 3 platform ref (`web-landing.md`) | Hero pattern picked from domain: full-bleed, split ratios (60/40 SaaS, 50/50, 40/60), video, minimal text |
| **Google taste-design** | Yes — atmosphere sliders (density/variance/motion) before `DESIGN.md` | Hero rules: asymmetric if variance > 4; inline-image typography signature; no centered high-variance heroes |
| **Glenskii companion** | Yes — **Design Declaration** incl. `Layout Strategy` | Bans default centered-hero pipeline explicitly |
| **Refero design** | Yes — discovery brief (job, objection, hook) before research | Hero patterns from real-product research, not template pick list |
| **Sailop template** | Yes — pick ONE visual archetype; describe in 3 lines before code | Forbids hero+floating-screenshot, gradient mesh; forces asymmetry |
| **v0** | Partial — `<Thinking>` on structure/styling before Code Project | shadcn + semantic colors; screenshot recreation mode; no explicit hero archetype enum |
| **Lovable** | Implicit — customize `index.css` / `tailwind.config` tokens first | Beautiful via design-system tokens + shadcn variants; less layout archetype logic |
| **Bolt template** | User-supplied project prompt only | “Beautiful, not cookie cutter” + shadcn stack |

**Arthor today (image layer only):** `scene_archetype` (`threshold_invitation`, `desk_side_guidance`, `environment_warmth`, …) and `hero_job` (`trust`, `experience`, `outcome`) in [`hero_visual_strategy.py`](../../app/style/hero_visual_strategy.py) + [`hero_taste_corpus`](../../data/hero_taste_corpus/) govern **photography**, not HTML hero layout. Payload `slot.layout` carries dimensions and `safe_area` for copy overlay — already aligned with premium hero practice.

**Gap:** No encoded **HTML hero layout archetype** (split vs full-bleed vs minimal) in image-service; that belongs on the builder side, keyed off the same industry slug + brand packet.

---

## 4. Reuse vs adaptation for Arthor’s pipeline

```
Payload + brand packet
        │
        ▼
┌───────────────────────┐     StyleProfile (image)     ┌─────────────────────┐
│ image-service         │ ───────────────────────────► │ Hero PNG + safe_area │
│ resolve_style_profile │     hero_taste_corpus        │ metadata             │
│ scene_archetype       │                              └──────────┬──────────┘
└───────────────────────┘                                         │
        │                                                          ▼
        │                                              ┌─────────────────────┐
        │                                              │ builder (downstream) │
        └────────────────────────────────────────────► │ SiteDesignProfile +  │
             (proposed) layout_archetype layer         │ layout_archetype     │
                                                       └─────────────────────┘
```

### Reusable as-is (or near-as-is)

| Asset | License | Arthor use |
|-------|---------|------------|
| **anti-slop-design 15-rule checklist** | MIT | Builder lint rubric / PR audit checklist |
| **Glenskii Design Declaration schema** | Verify repo | Builder pre-codegen JSON block (machine-parseable) |
| **shadcn semantic token model** | MIT | Builder `globals.css` contract ([design-system-from-packet](file:///Users/justinmendez/.cursor/skills/design-system-from-packet/SKILL.md) already maps brand.json → tokens) |
| **landing-page-optimization tone rhythm** | Internal | Section background alternation in builder |
| **Refero anti-ai-slop.md indigo ban + checklist** | Refero ToS | Builder copy-paste rules (not the MCP itself unless licensed) |

### Adapt (do not drop in verbatim)

| Asset | Why adapt | Arthor mapping |
|-------|-----------|----------------|
| **Anthropic frontend-design** | Single-agent codegen skill | Extract **two-pass plan**: (1) tokens + layout wireframe + signature, (2) uniqueness critique → emit **`SiteDesignBrief`** JSON consumed by builder |
| **anti-slop-design domain-map** | 8 B2B/SaaS-heavy domains | Map to Arthor **service verticals** (30 v2 slugs): local pro → `general`/`healthcare`/`creative` hybrid; use [`hero_taste_corpus/v2/*.yaml`](../../data/hero_taste_corpus/v2/) as taste anchor per slug |
| **Google taste-design** | Stitch-specific `DESIGN.md` | Translate to **`SiteDesignProfile`**: atmosphere sliders → `density`, `variance`, `motion_level`; hero rules → **`layout_archetype`** constraints |
| **Sailop visual archetypes** | Prompt prose for chat models | Enum **`visual_archetype`** on builder (7–9 values) orthogonal to **`layout_archetype`** (4–5 HTML patterns) |
| **Lovable / v0 styling rules** | Tied to React/shadcn monolith | Keep **semantic token discipline** only; ignore CodeProject/QuickEdit mechanics |
| **Leaked v0/Lovable prompts** | GPL / no license | Rule extraction only — already covered in checklist above |

### Do not reuse as-is

- Full **x1xhlol** prompt files in product (GPL-3.0).
- **Stitch MCP skills** without Stitch in loop — `design-md` workflow assumes Stitch API.
- **Anthropic frontend-design** wholesale in image-service — wrong layer (UI vs photography).

---

## 5. Recommendations for Arthor adoption

### 5.1 Split taste into two profiles (clarify ownership)

| Field group | Owner | Today | Extend |
|-------------|-------|-------|--------|
| **StyleProfile** | image-service | `palette`, `lighting`, `composition`, `do_not`, `mood`, … | Add **UI-adjacent image bans** from anti-slop: “no purple gradient lighting”, “no symmetric stock handshake” mirroring HTML slop |
| **SiteDesignProfile** (new) | builder / seo-service packet | Partially in `brand.json` | Typography pair, `--radius` scale, spacing base, `visual_archetype`, **`layout_archetype`**, section order template, `ui_do_not[]` |
| **scene_archetype** | image-service | Photo scene catalog | Keep separate from HTML layout; link via **`hero_job`** + safe_area compatibility table |

### 5.2 Proposed `layout_archetype` enum (builder layer)

Derived from [anti-slop web-landing Hero Patterns](https://github.com/Cuuper22/anti-slop-design/blob/main/references/web-landing.md) + [Google taste-design §4–6](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/taste-design):

| ID | When | Pairs with image `scene_archetype` |
|----|------|-------------------------------------|
| `full_bleed_overlay` | Visual/emotional trades (salon, restaurant, med spa) | `environment_warmth`, full-bleed plates |
| `split_60_40` | Local services, trust CTAs | `threshold_invitation`, `desk_side_guidance` |
| `split_50_50` | Balanced product + proof | `confident_smile` |
| `minimal_text` | High-trust professional (legal, CPA) | `desk_side_guidance`, low overlay_text_risk |
| `editorial_header` | Content-forward / blog-heavy | Rare for v1 service sites |

**Selection algorithm (deterministic, no LLM required for v1):**

1. Input: `business.slug` / industry label, `hero_job`, `StyleProfile.mood`, packet `brand.json` density hint.
2. Lookup table slug → default `layout_archetype` + `section_order` (from anti-slop domain → local-service mapping).
3. Override if hero image `safe_area.mode` is `left` / `right` / `bottom` → force split orientation matching safe zone.
4. Emit **Design Declaration** record for audit (Glenskii fields).

### 5.3 StyleProfile mapping (concrete)

| Anti-slop rule | StyleProfile field | Action |
|----------------|-------------------|--------|
| No neon / purple gradients | `do_not` | Merge builder-ui bans into **`ui_do_not`** on SiteDesignProfile; keep image `do_not` for photographic neon |
| Off-white / warm canvas | `palette` | Already from brand; builder sets `--background` from same palette neutrals |
| Rule-of-thirds + copy safe zone | `composition`, `slot.layout.safe_area` | **Already implemented** — ensure builder respects inset_pct from payload |
| No stock-photo aesthetic | `do_not` | **Already in** [`DEFAULT_DO_NOT`](../../app/style/defaults.py) |
| Industry faces / YMYL | `INDUSTRY_DO_NOT_EXTENSIONS` | **Already implemented** — extend with “no generic 3-person handshake stock” if needed |
| Mood adjectives | `mood` | Feed **`visual_archetype`** picker (warm professional → Swiss minimal or editorial, not SaaS bento) |

### 5.4 Suggested skill files to vendor into Arthor repos

| Priority | File to copy/adapt | Target path | License |
|----------|---------------------|-------------|---------|
| P0 | anti-slop checklist (15 rules, shortened) | `builder/skills/anti-slop-checklist/SKILL.md` | MIT |
| P0 | Design Declaration template | `builder/skills/design-declaration/SKILL.md` | Adapt from Glenskii |
| P1 | Anthropic frontend-design **process section only** | `builder/skills/ui-design-plan/SKILL.md` | Apache-2.0 |
| P1 | anti-slop `web-landing.md` hero + section anatomy | `builder/references/layout-archetypes.md` | MIT |
| P2 | Google taste-design hero + NEVER-DO list | `builder/references/site-design-profile-schema.md` | Apache-2.0 |
| P2 | Refero discovery questions (no MCP dependency) | `builder/skills/page-brief/SKILL.md` | Adapt methodology |

### 5.5 Pipeline insertion point

1. **seo-service / packet** — `brand.json` + page brief (job, objection, hook).
2. **image-service** — resolve `StyleProfile` + corpus hero (`scene_archetype`, `hero_job`, safe_area).
3. **NEW: design resolver (builder)** — inputs: brand + industry slug + hero metadata → outputs: `SiteDesignProfile` + `layout_archetype` + Design Declaration.
4. **builder agent** — MUST NOT write JSX until Declaration validates against anti-slop checklist.
5. **QA** — automated slop lint (indigo class scan, Inter font scan, 3-column grid detector) + Sailop-style self-audit prompt optional.

---

## 6. Key URLs (quick reference)

- Anthropic skills: https://github.com/anthropics/skills  
- Anti-slop design: https://github.com/Cuuper22/anti-slop-design  
- Google Stitch skills: https://github.com/google-labs-code/stitch-skills  
- Awesome system prompts: https://github.com/dontriskit/awesome-ai-system-prompts  
- v0 leaked prompt mirror: https://leaked-system-prompts.com/prompts/v0/v0_20250428  
- Lovable prompt mirror: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Lovable/Agent%20Prompt.txt  
- Bolt prompting guide: https://support.bolt.new/best-practices/prompting-effectively  
- shadcn theming: https://ui.shadcn.com/docs/theming  
- Sailop anti-slop template: https://sailop.com/blog/anti-slop-prompt-template-2026  
- Agent Skills standard: https://agentskills.io  

---

## 7. Research limits

- Anthropic per-skill `LICENSE.txt` was not fetched (404 on raw URL); repo README states **Apache-2.0 for example skills** (frontend-design qualifies).
- Some GitHub raw fetches timed out in environment; content verified via curl partial reads + cached search extracts.
- No application code was modified in this pod.
