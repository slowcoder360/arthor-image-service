# ADR 0013: Hero benefit-first prompts (compiler 4.0)

- Status: **accepted**
- Date: 2026-06-18
- Supersedes in spirit: ADR 0012 §3 scene catalog as provider subject
- Prior: [`plan/HANDOFF-HERO-BENEFIT-FIRST.md`](../HANDOFF-HERO-BENEFIT-FIRST.md), [`plan/HANDOFF-HERO-CORPUS-CANARY-GRID.md`](../HANDOFF-HERO-CORPUS-CANARY-GRID.md)

## Context

Canary pass 1 (30 slugs) and pass 2 (15 regens after patch wave A–D, compiler 3.5) proved that **scene catalog `subject`** dominates provider prompts. Models default to doorway consult, desk iPad, and two people talking regardless of industry modifiers layered in setting/people/invariants.

Root cause: `build_hero_prompt_brief()` set `subject=scene.subject` from `SCENE_CATALOG` (e.g. `threshold_invitation`, `desk_side_guidance`). Industry backdrop and people overrides fight a generic archetype story instead of owning it.

**North star:** Hero images sell the **benefit of the service**, not generic happy people. Each trade/keyword gets a **benefit template** — no blanket rule.

## Decisions

### 1. Benefit template layer (compiler 4.0)

Insert deterministic resolver before serializer:

```text
resolve_industry()              → coarse label (corpus fallback, analytics)
resolve_benefit_template()      → benefit_subject + people + avoid  (per slug × variant 0|1|2)
resolve_scene_archetype()       → metadata / triad label only
build_hero_prompt_brief()       → benefit_subject is provider line 1 (Subject:)
serialize_openai_hero_prompt()
```

- **`COMPILER_VERSION` → `4.0`** (prompt_hash cache break intentional).
- Module: `app/style/hero_benefit_templates.py`.
- API: `resolve_benefit_template(industry: str, variant_index: int) -> BenefitTemplate`.
- Match industry string to template via longest keyword win (same pattern as `resolve_industry()`).
- Start with all **30 canary slugs**; unknown industry falls back to `general_services` door-greet template.

### 2. Deprecate scene catalog as provider subject

- **`SCENE_CATALOG.subject` is not emitted** in provider prompts.
- **`scene_archetype`** remains on run metadata and triad labels only.
- Do **not** add more `INDUSTRY_SCENE_PEOPLE_OVERRIDES` or vertical subject patches on the old architecture.
- Keep: safe zones, serializer invariants, `resolve_industry()`, cohort eval, inspector review, team ref regenerate path.

### 3. People / likeness (locked)

| Context | Rule |
|---------|------|
| Provider in frame | Customer face OK; provider **back/profile** |
| WIP slots (v1) | Worker back/profile; customer face if present |
| Environment v0 | People optional; anonymous only |
| Team refs | Default back-face; regenerate + ref may show likeness |
| `general_services` door greet | **Unknown industry only** — no service imagery |

Desk consult (legal, dental, CPA) unchanged: both faces visible.

### 4. Triad patterns by bucket

| Bucket | v0 | v1 | v2 |
|--------|----|----|-----|
| **home_services** | Trade-specific benefit (HVAC/plumbing/electric → interior comfort; roofing/garage → exterior pride) | Shared WIP (trade-accurate) | Shared post-job trust |
| **outdoor_services** | Finished property outcome | WIP trade-accurate | Second outcome angle |
| **healthcare** | All 3 slots **trade-specific** (PT, chiro, med spa, vet) | trade-specific | trade-specific |
| **dental** | Consult/smile | Family warmth | Smile outcome |
| **legal** | Desk counsel | Office threshold welcome | Relieved client |
| **office family** (CPA, insurance, property, real estate) | Shared office + trade desk detail | office WIP | second office angle |
| **environment-first** (restaurant, cleaning, salon, pool, gym, wedding) | Dedicated environment | WIP trade-accurate | Second env angle |
| **pest** | Protected home exterior | treatment WIP | protected exterior angle |
| **auto** | Clean shop bay + vehicle serviced | bay WIP | finished vehicle |
| **concrete paving** | Dedicated (see §5) | pour/finish WIP | completed surface |
| **unknown** | Door greet only | — | — |

Known canary industries **never** get generic door greet.

### 5. Concrete paving — commercial vs residential

**Decision (v0):** Infer from industry string keywords until blocked:

- **Residential signals:** `driveway`, `patio`, `walkway`, `sidewalk`, `residential`, `home`.
- **Commercial signals:** `commercial`, `parking`, `industrial`, `municipal`, `storefront`.
- **Default:** residential (driveway/walkway at home facade) when ambiguous.

Defer dedicated API field (`business.property_type` or similar) unless Justin blocks on inference quality.

### 6. Healthcare v1/v2 defaults

Full per-trade benefit sentences for slots 1 and 2 were not fully grilled. **Sensible defaults** from v0 patterns (PT movement, chiro adjustment, med spa treatment room, vet exam) ship in compiler 4.0; Justin may refine in promotion wave.

### 7. Out of scope (this ADR)

- Hero API contract changes.
- Import canary singles to corpus YAML.
- Enable arthor-ai default `generation_mode: "corpus"`.
- v2 slug corpus resolver (`resolve_taste_corpus` longest match).

## Consequences

- Provider prompts have one authoritative benefit subject per slug × variant — no archetype fight.
- Prompt tuning moves to `hero_benefit_templates.py` tables, not scene catalog patches.
- Tests assert **benefit_subject content** per slug, not doorway/desk catalog strings.
- Pass 3 canary regens failing slugs for Justin sign-off before corpus promotion.

## References

- Canary failure report: `scratch/hero-cohort-canary-20260618T144308Z/canary_failure_report.md`
- Pass 2 review: `scratch/hero-cohort-canary-20260618T170652Z/human_review.json`
