"""Load cohort eval CSVs from scratch/ and persist human review marks."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRATCH_DIR = REPO_ROOT / "scratch"
REVIEW_FILENAME = "human_review.json"
EXPORT_FILENAME = "human_review.csv"

# Human review tags — separate from automated ``failure_mode`` QA gates.
REVIEW_ISSUE_TAGS: tuple[tuple[str, str], ...] = (
    ("wrong_industry", "Wrong industry / setting"),
    ("residential_backdrop", "Residential, not commercial/clinic"),
    ("equipment_as_hero", "Equipment as hero subject"),
    ("dental_operatory", "Dental chair / operatory focal"),
    ("stock_posed", "Stock photo / posed at camera"),
    ("safe_zone_busy", "Copy safe zone too busy"),
    ("text_in_image", "Rendered text in image"),
    ("palette_off", "Off-brand colors"),
    ("composition", "Weak composition / framing"),
    ("people_wrong", "Wrong people / count"),
    ("not_photorealistic", "Not photorealistic enough"),
    ("other", "Other (use notes)"),
)


def list_eval_sessions() -> list[str]:
    if not SCRATCH_DIR.is_dir():
        return []
    names = sorted(
        p.name
        for p in SCRATCH_DIR.iterdir()
        if p.is_dir() and p.name.startswith("hero-cohort-eval")
    )
    return names


def _review_path(session_dir: Path) -> Path:
    return session_dir / REVIEW_FILENAME


def load_reviews(session_dir: Path) -> dict[str, dict[str, Any]]:
    path = _review_path(session_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    reviews = data.get("reviews")
    return reviews if isinstance(reviews, dict) else {}


def save_review_entry(
    session_dir: Path,
    item_key: str,
    *,
    verdict: str,
    issues: list[str],
    notes: str,
    reviewer: str = "inspector",
) -> dict[str, Any]:
    path = _review_path(session_dir)
    payload: dict[str, Any] = {"reviews": {}}
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"reviews": {}}
    if not isinstance(payload.get("reviews"), dict):
        payload["reviews"] = {}

    entry = {
        "verdict": verdict,
        "issues": issues,
        "notes": notes.strip(),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer": reviewer,
    }
    payload["reviews"][item_key] = entry
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return entry


def item_key(run_id: str, variant_index: int) -> str:
    return f"{run_id}:{variant_index}"


def _row_to_item(row: dict[str, str], *, session_name: str) -> dict[str, Any]:
    run_id = str(row.get("run_id") or "")
    variant_index = int(row.get("variant_index") or 0)
    return {
        "session_name": session_name,
        "key": item_key(run_id, variant_index),
        "slug": row.get("slug") or "",
        "industry_label": row.get("industry_label") or "",
        "replicate": row.get("replicate") or "",
        "run_id": run_id,
        "run_status": row.get("run_status") or "",
        "variant_index": variant_index,
        "tone_angle": row.get("tone_angle") or "",
        "auto_qa_pass": str(row.get("qa_pass", "")).lower() in ("true", "1", "yes"),
        "auto_failure_mode": row.get("failure_mode") or "",
        "url": row.get("url") or "",
        "headline": row.get("headline") or "",
    }


def load_cohort_items(*, session: str = "all", include_missing: bool = False) -> list[dict[str, Any]]:
    """Load eval rows from scratch hero-cohort-eval* directories."""
    sessions = list_eval_sessions()
    if session != "all":
        if session not in sessions:
            return []
        sessions = [session]

    by_slot: dict[tuple[str, int], dict[str, Any]] = {}
    for name in sessions:
        csv_path = SCRATCH_DIR / name / "cohort_results.csv"
        if not csv_path.is_file():
            continue
        reviews = load_reviews(SCRATCH_DIR / name)
        with csv_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                item = _row_to_item(row, session_name=name)
                if not item["url"] and not include_missing:
                    continue
                slot = (item["slug"], item["variant_index"])
                existing = by_slot.get(slot)
                if existing is None or (not existing.get("url") and item["url"]):
                    by_slot[slot] = item
                elif item["url"] and existing.get("url"):
                    # Prefer latest session (lexicographic eval dir names include timestamp).
                    if name >= str(existing.get("session_name") or ""):
                        by_slot[slot] = item

    items: list[dict[str, Any]] = []
    for item in by_slot.values():
        session_dir = SCRATCH_DIR / str(item["session_name"])
        rev = load_reviews(session_dir)
        item["review"] = rev.get(item["key"]) or {}
        items.append(item)

    items.sort(key=lambda i: (i["industry_label"], i["slug"], i["variant_index"]))
    return items


def review_stats(items: list[dict[str, Any]]) -> dict[str, int]:
    total = len(items)
    reviewed = sum(1 for i in items if i.get("review", {}).get("verdict"))
    good = sum(1 for i in items if i.get("review", {}).get("verdict") == "good")
    bad = sum(1 for i in items if i.get("review", {}).get("verdict") == "bad")
    return {
        "total": total,
        "reviewed": reviewed,
        "good": good,
        "bad": bad,
        "pending": total - reviewed,
    }


def issue_label(tag: str) -> str:
    for slug, label in REVIEW_ISSUE_TAGS:
        if slug == tag:
            return label
    return tag


def export_reviews_csv(session: str = "all") -> str:
    items = load_cohort_items(session=session, include_missing=True)
    lines: list[str] = []
    fieldnames = [
        "session_name",
        "industry_label",
        "slug",
        "tone_angle",
        "headline",
        "url",
        "auto_failure_mode",
        "verdict",
        "issues",
        "notes",
        "reviewed_at",
    ]
    buf: list[dict[str, str]] = []
    for item in items:
        rev = item.get("review") or {}
        buf.append(
            {
                "session_name": str(item.get("session_name") or ""),
                "industry_label": str(item.get("industry_label") or ""),
                "slug": str(item.get("slug") or ""),
                "tone_angle": str(item.get("tone_angle") or ""),
                "headline": str(item.get("headline") or ""),
                "url": str(item.get("url") or ""),
                "auto_failure_mode": str(item.get("auto_failure_mode") or ""),
                "verdict": str(rev.get("verdict") or ""),
                "issues": ";".join(rev.get("issues") or []),
                "notes": str(rev.get("notes") or "").replace("\n", " "),
                "reviewed_at": str(rev.get("reviewed_at") or ""),
            }
        )
    import io

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(buf)
    return out.getvalue()
