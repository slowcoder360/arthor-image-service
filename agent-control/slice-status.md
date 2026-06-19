# Slice status — hero taste corpus wave (U9 + U10)

| Slice | Branch | SHA | Tests | Status |
|-------|--------|-----|-------|--------|
| U9 visual triad | `main` (merged via U1–U8 wave) | on `main` | hero triad suite | **landed on main** |
| U10 taste corpus | `pod/u10-hero-taste-corpus` | `738a80e` (738a80e357efa5e8978d96caf92ee833f5b76884) | 93/93 hero+corpus | **ready for Justin merge** (LB-M0) |

**LB-M0 pytest:** `pytest tests/test_hero*.py tests/test_import_cohort_to_corpus.py`

**Corpus on pod:** 30 v2 slug YAMLs (`data/hero_taste_corpus/v2/`), 6 v1 coarse labels; `generation_mode: "corpus"`, `corpus_version: "2.0"`.

**Blocks:** arthor-ai live hero triad (LB-E3) until Justin merges pod → main and deploys image-service with corpus data.

Justin: merge `pod/u10-hero-taste-corpus` to `main`, then deploy before arthor-ai default switch.
