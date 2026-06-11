#!/usr/bin/env python3
"""Batch hero quality metrics over scratch A/B assets (offline).

Usage:
  python scripts/hero_quality_batch.py scratch/hero-ab-review
  python scripts/hero_quality_batch.py scratch/hero-ab-review --with-clip

Writes CSV with palette drift and optional CLIPScore when ``open-clip-torch`` is installed.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.quality.palette_variance import check_palette_drift  # noqa: E402


def _load_prompt(run_dir: Path, tone: str) -> str:
    prompts_dir = run_dir.parent / "prompts"
    if not prompts_dir.is_dir():
        return ""
    for path in prompts_dir.glob(f"*{tone}*.txt"):
        return path.read_text(encoding="utf-8").strip()
    return ""


def _palette_for_run(run_dir: Path) -> list[str]:
    for path in run_dir.parent.glob("prompts/*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        palette = (
            data.get("brand_visual", {})
            .get("palette", {})
            .get("light", {})
        )
        if palette:
            return [
                str(palette.get("primary", "#0A4B6F")),
                str(palette.get("secondary", "#F4A261")),
                str(palette.get("background", "#FFFFFF")),
            ]
    return ["#0A4B6F", "#F4A261", "#FFFFFF"]


def _clip_score(image_path: Path, prompt: str) -> float | None:
    try:
        import open_clip
        import torch
        from PIL import Image
    except ImportError:
        return None
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="openai"
    )
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    image = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0)
    text = tokenizer([prompt])
    with torch.no_grad():
        image_features = model.encode_image(image)
        text_features = model.encode_text(text)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        return float((image_features @ text_features.T).item())


def scan_review_dir(review_dir: Path, *, with_clip: bool) -> list[dict[str, str | float | bool]]:
    rows: list[dict[str, str | float | bool]] = []
    palette = _palette_for_run(review_dir)
    for provider_dir in sorted(review_dir.iterdir()):
        if not provider_dir.is_dir():
            continue
        provider = provider_dir.name.split("-")[0]
        run_id = provider_dir.name.split("-", 1)[-1] if "-" in provider_dir.name else provider_dir.name
        for image_path in sorted(provider_dir.glob("*.png")):
            stem = image_path.stem
            parts = stem.split("-", 1)
            tone = parts[1] if len(parts) > 1 else stem
            prompt = _load_prompt(provider_dir, tone)
            drift, _ = check_palette_drift(image_path.read_bytes(), palette, 25.0)
            row: dict[str, str | float | bool] = {
                "run_id": run_id,
                "provider": provider,
                "tone": tone,
                "image_path": str(image_path),
                "palette_drift": drift,
                "prompt_chars": len(prompt),
            }
            if with_clip and prompt:
                score = _clip_score(image_path, prompt)
                if score is not None:
                    row["clip_score"] = score
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Hero A/B batch quality report")
    parser.add_argument("review_dir", type=Path, help="e.g. scratch/hero-ab-review")
    parser.add_argument("--with-clip", action="store_true", help="Compute CLIPScore if open-clip-torch installed")
    parser.add_argument("-o", "--output", type=Path, default=None)
    args = parser.parse_args()

    rows = scan_review_dir(args.review_dir, with_clip=args.with_clip)
    out_path = args.output or args.review_dir / "quality-batch.csv"
    if not rows:
        print(f"No PNG assets under {args.review_dir}", file=sys.stderr)
        sys.exit(1)

    fieldnames = sorted({k for row in rows for k in row})
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
