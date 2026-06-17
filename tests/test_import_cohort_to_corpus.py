"""Unit tests for cohort → corpus import script."""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

from scripts.import_cohort_to_corpus import build_industry_yaml, import_from_cohort_csv


def test_build_industry_yaml_from_csv_row(tmp_path: Path) -> None:
    row = {
        "variant_index": "0",
        "tone_angle": "search",
        "url": "https://cdn.example/hero.webp",
        "r2_key": "corpus/dental/0.webp",
        "industry": "dental",
        "slug": "dental",
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
    }
    doc = build_industry_yaml(
        "dental",
        [row],
        corpus_version="1.0",
        approved_by="justin",
        approved_at="2026-06-16",
    )
    assert doc["industry_label"] == "dental"
    assert doc["variants"][0]["scene_archetype"] == "threshold_invitation"
    assert doc["variants"][0]["public_url"] == "https://cdn.example/hero.webp"


def test_import_from_cohort_csv_writes_yaml(tmp_path: Path, monkeypatch) -> None:
    from app.style import hero_taste_corpus as corpus_mod

    monkeypatch.setattr(corpus_mod, "CORPUS_DATA_ROOT", tmp_path / "hero_taste_corpus")

    cohort = tmp_path / "cohort_results.csv"
    with cohort.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["slug", "industry", "variant_index", "tone_angle", "url", "r2_key", "run_id"],
        )
        writer.writeheader()
        for idx in range(3):
            writer.writerow(
                {
                    "slug": "dental",
                    "industry": "dental",
                    "variant_index": str(idx),
                    "tone_angle": ["search", "story", "offer"][idx],
                    "url": f"https://cdn.example/dental/{idx}.webp",
                    "r2_key": f"corpus/dental/{idx}.webp",
                    "run_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            )

    paths = import_from_cohort_csv(
        cohort,
        slug="dental",
        variant_indices=None,
        reviews_csv=None,
        corpus_version="1.0",
        approved_by="justin",
        dry_run=False,
    )
    assert len(paths) == 1
    data = yaml.safe_load(paths[0].read_text(encoding="utf-8"))
    assert data["industry_label"] == "dental"
    assert len(data["variants"]) == 3
