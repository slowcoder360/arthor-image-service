"""Inspector helpers for hero taste corpus coverage."""

from __future__ import annotations

from typing import Any

from app.style.hero_taste_corpus import corpus_coverage, resolve_taste_corpus
from app.style.hero_visual_strategy import INDUSTRY_VISUAL_TRIAD


def taste_corpus_rows(*, corpus_version: str = "1.0") -> list[dict[str, Any]]:
    coverage = corpus_coverage(corpus_version=corpus_version)
    rows: list[dict[str, Any]] = []
    for label in sorted(INDUSTRY_VISUAL_TRIAD.keys()):
        indices = coverage.get(label, [])
        triad = resolve_taste_corpus(label, corpus_version=corpus_version)
        variants: list[dict[str, Any]] = []
        if triad is not None:
            for entry in triad.variants:
                variants.append(
                    {
                        "variant_index": entry.variant_index,
                        "scene_archetype": entry.scene_archetype,
                        "url": entry.public_url or entry.r2_key,
                        "style_profile_fragment": entry.style_profile_fragment,
                    }
                )
        rows.append(
            {
                "industry_label": label,
                "variant_indices": indices,
                "coverage": f"{len(indices)}/3",
                "variants": variants,
                "complete": len(indices) == 3,
            }
        )
    return rows
