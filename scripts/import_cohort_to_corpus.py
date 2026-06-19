#!/usr/bin/env python3
"""Import cohort eval winners into hero taste corpus YAML."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.style.hero_archetypes import resolve_industry  # noqa: E402
from app.style.hero_taste_corpus import CORPUS_DATA_ROOT, clear_corpus_cache  # noqa: E402
from app.style.hero_visual_strategy import INDUSTRY_VISUAL_TRIAD  # noqa: E402

DEFAULT_REVIEWS = ROOT / "scratch" / "hero-cohort-eval" / "human_review_all.csv"


def _r2_key_from_url(url: str) -> str:
    if "/hero-candidates/" in url:
        return "hero-candidates/" + url.split("/hero-candidates/", 1)[1]
    return url


def _scene_for_row(row: dict[str, str], idx: int, industry: str) -> str:
    scene = (row.get("scene_archetype") or "").strip()
    if scene:
        return scene
    coarse = resolve_industry(industry).label
    return INDUSTRY_VISUAL_TRIAD.get(coarse, INDUSTRY_VISUAL_TRIAD["general_services"])[idx]


def _match_keys_for_slug(slug: str, industry: str) -> list[str]:
    keys: list[str] = []
    for candidate in (industry, slug.replace("_", " "), slug):
        c = candidate.strip().lower()
        if c and c not in keys:
            keys.append(c)
    return sorted(keys, key=len, reverse=True)


def _load_reviews(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    out: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = f"{row.get('run_id', '')}:{row.get('variant_index', '')}"
            if row.get("verdict") == "good":
                out[key] = row
    return out


def _load_cohort_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _variant_entry(
    row: dict[str, str],
    *,
    approved_by: str,
    approved_at: str,
) -> dict[str, Any]:
    idx = int(row["variant_index"])
    industry = row.get("industry") or row.get("slug") or "general"
    scene = _scene_for_row(row, idx, industry)
    tone = row.get("tone_angle") or "search"
    hero_job = {"search": "trust", "story": "experience", "offer": "outcome"}.get(tone, "trust")
    url = row.get("url") or row.get("r2_url") or ""
    r2_key = row.get("r2_key") or (_r2_key_from_url(url) if url else f"corpus/{industry}/{idx}.webp")
    return {
        "variant_index": idx,
        "scene_archetype": scene,
        "hero_job": hero_job,
        "r2_key": r2_key,
        "public_url": url,
        "style_profile_fragment": {
            "lighting": row.get("style_lighting") or "soft natural window light",
            "color_grading": row.get("style_color_grading") or "warm professional",
        },
        "compiler_version": row.get("compiler_version") or "4.1",
        "approved_at": approved_at,
        "approved_by": approved_by,
    }


def build_slug_yaml(
    slug: str,
    industry_label: str,
    match_keys: list[str],
    rows: list[dict[str, str]],
    *,
    corpus_version: str,
    approved_by: str,
    approved_at: str,
) -> dict[str, Any]:
    by_index = {int(r["variant_index"]): r for r in rows}
    industry = str(rows[0].get("industry") or slug)
    variants = [
        _variant_entry(by_index[i], approved_by=approved_by, approved_at=approved_at)
        for i in (0, 1, 2)
    ]
    return {
        "corpus_version": corpus_version,
        "slug": slug,
        "industry_label": industry_label,
        "match_keys": match_keys,
        "variants": variants,
    }


def build_industry_yaml(
    industry_label: str,
    rows: list[dict[str, str]],
    *,
    corpus_version: str,
    approved_by: str,
    approved_at: str,
) -> dict[str, Any]:
    by_index = {int(r["variant_index"]): r for r in rows}
    variants = [
        _variant_entry(by_index[i], approved_by=approved_by, approved_at=approved_at)
        for i in sorted(by_index.keys())
    ]
    return {
        "corpus_version": corpus_version,
        "industry_label": industry_label,
        "variants": variants,
    }


def write_corpus_yaml(
    label: str,
    doc: dict[str, Any],
    *,
    corpus_version: str,
) -> Path:
    out_dir = CORPUS_DATA_ROOT / f"v{corpus_version.split('.')[0]}"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{label}.yaml"
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(doc, handle, sort_keys=False, allow_unicode=True)
    return path


def import_v2_slugs_from_cohort_csv(
    cohort_csv: Path,
    *,
    slug: str | None,
    reviews_csv: Path | None,
    corpus_version: str,
    approved_by: str,
    dry_run: bool,
    require_complete_triad: bool = True,
) -> list[Path]:
    rows = _load_cohort_csv(cohort_csv)
    good_keys: set[str] | None = None
    if reviews_csv is not None:
        good_keys = set(_load_reviews(reviews_csv).keys())

    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        row_slug = row.get("slug") or ""
        if not row_slug:
            continue
        if slug and row_slug != slug:
            continue
        if not row.get("url"):
            continue
        idx_raw = row.get("variant_index")
        if idx_raw is None:
            continue
        idx = int(idx_raw)
        if good_keys is not None:
            key = f"{row.get('run_id', '')}:{idx}"
            if key not in good_keys:
                continue
        grouped.setdefault(row_slug, []).append(row)

    written: list[Path] = []
    approved_at = date.today().isoformat()
    for row_slug, slug_rows in sorted(grouped.items()):
        indices = {int(r["variant_index"]) for r in slug_rows}
        if require_complete_triad and indices != {0, 1, 2}:
            print(f"skip {row_slug}: need variants 0,1,2 got {sorted(indices)}", file=sys.stderr)
            continue
        industry = str(slug_rows[0].get("industry") or row_slug)
        industry_label = resolve_industry(industry).label
        match_keys = _match_keys_for_slug(row_slug, industry)
        doc = build_slug_yaml(
            row_slug,
            industry_label,
            match_keys,
            slug_rows,
            corpus_version=corpus_version,
            approved_by=approved_by,
            approved_at=approved_at,
        )
        if dry_run:
            print(json.dumps({"slug": row_slug, "variants": len(doc["variants"])}, indent=2))
            continue
        written.append(write_corpus_yaml(row_slug, doc, corpus_version=corpus_version))
    clear_corpus_cache()
    return written


def import_from_cohort_csv(
    cohort_csv: Path,
    *,
    slug: str | None,
    variant_indices: tuple[int, ...] | None,
    reviews_csv: Path | None,
    corpus_version: str,
    approved_by: str,
    dry_run: bool,
) -> list[Path]:
    rows = _load_cohort_csv(cohort_csv)
    good_keys: set[str] | None = None
    if reviews_csv is not None:
        good_keys = set(_load_reviews(reviews_csv).keys())

    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        row_slug = row.get("slug") or row.get("industry_label") or ""
        if slug and row_slug != slug:
            continue
        idx_raw = row.get("variant_index")
        if idx_raw is None:
            continue
        idx = int(idx_raw)
        if variant_indices is not None and idx not in variant_indices:
            continue
        if good_keys is not None:
            key = f"{row.get('run_id', '')}:{idx}"
            if key not in good_keys:
                continue
        industry_label = resolve_industry(row.get("industry") or row_slug).label
        grouped.setdefault(industry_label, []).append(row)

    written: list[Path] = []
    approved_at = date.today().isoformat()
    for industry_label, industry_rows in grouped.items():
        if len({int(r["variant_index"]) for r in industry_rows}) < 1:
            continue
        doc = build_industry_yaml(
            industry_label,
            industry_rows,
            corpus_version=corpus_version,
            approved_by=approved_by,
            approved_at=approved_at,
        )
        if dry_run:
            print(json.dumps({"industry": industry_label, "variants": len(doc["variants"])}, indent=2))
            continue
        written.append(write_corpus_yaml(industry_label, doc, corpus_version=corpus_version))
    clear_corpus_cache()
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-csv", type=Path, required=True)
    parser.add_argument("--reviews-csv", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--slug", type=str, default=None)
    parser.add_argument("--variant-index", type=int, action="append", dest="variant_indices")
    parser.add_argument("--corpus-version", type=str, default="1.0")
    parser.add_argument("--approved-by", type=str, default="justin")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    indices = tuple(args.variant_indices) if args.variant_indices else None
    reviews = args.reviews_csv if args.reviews_csv.is_file() else None
    if args.corpus_version.startswith("2"):
        paths = import_v2_slugs_from_cohort_csv(
            args.cohort_csv,
            slug=args.slug,
            reviews_csv=reviews,
            corpus_version=args.corpus_version,
            approved_by=args.approved_by,
            dry_run=args.dry_run,
        )
    else:
        paths = import_from_cohort_csv(
            args.cohort_csv,
            slug=args.slug,
            variant_indices=indices,
            reviews_csv=reviews,
            corpus_version=args.corpus_version,
            approved_by=args.approved_by,
            dry_run=args.dry_run,
        )
    for path in paths:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
