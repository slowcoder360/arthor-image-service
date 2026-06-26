"""Deterministic abstract hero prompt — for non-photo layout archetypes (no people, no slop)."""

from __future__ import annotations


def build_abstract_hero_prompt(*, palette_primary: str, seed: int, variant_index: int) -> str:
    """Build a deterministic abstract/gradient hero prompt. No people, no text, no slop tells."""
    return (
        f"Abstract gradient hero background, deterministic seed {seed}-{variant_index}. "
        f"Soft mesh gradient built from the brand color {palette_primary} with at most two accents, "
        "subtle grain and generous negative space for left-aligned copy. "
        "No human subjects, no faces, no lettering or text. "
        "Restrained and premium; avoid rainbow or neon color casts."
    )
