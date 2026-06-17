# HANDOFF — Hero taste corpus wave (U9 + U10)

- **Audience:** Tier-1 orchestrator + arthor-ai consumer follow-up
- **Date:** 2026-06-16
- **Branches:** `pod/u9-visual-triad`, `pod/u10-hero-taste-corpus`

---

## Goal

Default builder `POST /images/hero-candidates/generate` returns three corpus URLs in <2s (no OpenAI). Live gen unchanged for escape hatches and build-time packs.

---

## Slices

| ID | Branch | Done when |
|----|--------|-----------|
| **U9** | `pod/u9-visual-triad` | `INDUSTRY_VISUAL_TRIAD` — three distinct `scene_archetype` per industry × `variant_index`; compiler 3.4 |
| **U10** | `pod/u10-hero-taste-corpus` | `generation_mode: "corpus"` default; YAML corpus; import script; inspector `/inspector/taste-corpus` |

---

## Corpus gaps (seeded 2026-06-16)

| Industry | Coverage |
|----------|----------|
| dental | 3/3 |
| general_services | 3/3 (fallback) |
| legal | TODO |
| home_services | TODO |
| healthcare | TODO |
| outdoor_services | TODO |

**Pause for Justin:** visual pass on seeded dental + general_services before arthor-ai switches default to corpus mode.

---

## Operator

```bash
# Import cohort winners
python scripts/import_cohort_to_corpus.py \
  --cohort-csv scratch/hero-cohort-eval/cohort_results.csv \
  --slug dental

# Inspector
open /inspector/taste-corpus
```

---

## Cross-links

- Consumer contract: [`HERO-CANDIDATES-CONSUMER.md`](HERO-CANDIDATES-CONSUMER.md)
- Visual triad idea: `~/arthor-brainstorm/inbox/idea25-hero-visual-triad.md`
- seo planning stays in seo-service — no `asset_pack_plan` parsing here
