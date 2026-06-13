#!/usr/bin/env python3
"""Run hero-candidates cohort eval across business types; aggregate QA pass/fail.

Usage:
  python scripts/hero_cohort_eval.py --base-url http://127.0.0.1:8010
  python scripts/hero_cohort_eval.py --replicates 2 --output scratch/hero-cohort-eval

Writes:
  {output}/cohort_results.csv
  {output}/cohort_summary.md
  {output}/payloads/  (one JSON per run for replay)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.auth.hmac import sign_body  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.style.hero_archetypes import resolve_industry  # noqa: E402

# One scenario per resolved industry label (see hero_archetypes.INDUSTRY_CONTEXTS).
COHORT_SCENARIOS: list[dict[str, Any]] = [
    {
        "slug": "dental",
        "business": {
            "site_name": "Bright Smile Family Dental",
            "industry": "dental",
            "icp_summary": "local families seeking preventive care",
            "value_prop": "gentle, modern dentistry with same-week appointments",
            "proof_points": [],
            "forbidden_subjects": [],
            "priority_services": ["cleanings", "pediatric dentistry"],
        },
        "location": {"mode": "local", "country": "US", "city": "Austin", "region": "TX", "service_areas": []},
        "variants": [
            {"tone_angle": "search", "headline": "Find a dentist you trust in Austin", "subhead": "Same-week appointments"},
            {"tone_angle": "story", "headline": "Care that feels personal from day one", "subhead": "A calm office for your family"},
            {"tone_angle": "offer", "headline": "New patient exam — book this week", "subhead": "Transparent pricing"},
        ],
    },
    {
        "slug": "legal",
        "business": {
            "site_name": "Mendez & Associates Law",
            "industry": "personal injury law",
            "icp_summary": "accident victims comparing local attorneys",
            "value_prop": "contingency-fee representation with clear communication",
            "proof_points": [],
            "forbidden_subjects": [],
            "priority_services": ["car accidents", "slip and fall"],
        },
        "location": {"mode": "local", "country": "US", "city": "Phoenix", "region": "AZ", "service_areas": []},
        "variants": [
            {"tone_angle": "search", "headline": "Injured in Phoenix? Know your options", "subhead": "Free case review"},
            {"tone_angle": "story", "headline": "Advocates who listen first", "subhead": "Personal attention on every case"},
            {"tone_angle": "offer", "headline": "No fee unless we win", "subhead": "Start with a free consultation"},
        ],
    },
    {
        "slug": "home_services",
        "business": {
            "site_name": "CoolAir HVAC Pros",
            "industry": "hvac repair",
            "icp_summary": "homeowners needing fast AC repair",
            "value_prop": "same-day HVAC service with upfront pricing",
            "proof_points": [],
            "forbidden_subjects": [],
            "priority_services": ["AC repair", "furnace tune-up"],
        },
        "location": {"mode": "local", "country": "US", "city": "Dallas", "region": "TX", "service_areas": []},
        "variants": [
            {"tone_angle": "search", "headline": "AC out in Dallas? We can help today", "subhead": "Licensed technicians"},
            {"tone_angle": "story", "headline": "Comfort restored without the runaround", "subhead": "Trusted local crew"},
            {"tone_angle": "offer", "headline": "$49 tune-up special", "subhead": "Book before summer rush"},
        ],
    },
    {
        "slug": "healthcare",
        "business": {
            "site_name": "Peak Physical Therapy",
            "industry": "physical therapy clinic",
            "icp_summary": "active adults recovering from sports injuries",
            "value_prop": "evidence-based rehab with one-on-one sessions",
            "proof_points": [],
            "forbidden_subjects": [],
            "priority_services": ["sports rehab", "post-surgery recovery"],
        },
        "location": {"mode": "local", "country": "US", "city": "Denver", "region": "CO", "service_areas": []},
        "variants": [
            {"tone_angle": "search", "headline": "Get moving again in Denver", "subhead": "Same-week evals"},
            {"tone_angle": "story", "headline": "Recovery plans built around your goals", "subhead": "Hands-on care"},
            {"tone_angle": "offer", "headline": "Free injury screening", "subhead": "Limited spots this month"},
        ],
    },
    {
        "slug": "general_services",
        "business": {
            "site_name": "GreenPath Landscaping",
            "industry": "landscaping",
            "icp_summary": "homeowners wanting curb appeal without hassle",
            "value_prop": "reliable lawn and landscape maintenance",
            "proof_points": [],
            "forbidden_subjects": [],
            "priority_services": ["lawn care", "seasonal cleanup"],
        },
        "location": {"mode": "local", "country": "US", "city": "Portland", "region": "OR", "service_areas": []},
        "variants": [
            {"tone_angle": "search", "headline": "Landscaping you can count on", "subhead": "Serving Portland homeowners"},
            {"tone_angle": "story", "headline": "Yards that feel cared for", "subhead": "Consistent weekly service"},
            {"tone_angle": "offer", "headline": "Spring cleanup special", "subhead": "Book your first visit"},
        ],
    },
]

_SHARED_BRAND = {
    "brand_voice": {
        "tone": "warm and reassuring",
        "notes": [],
        "style_direction": "",
        "reference_likes": [],
        "do_not": [],
    },
    "brand_visual": {
        "palette": {
            "light": {
                "primary": "#0A4B6F",
                "secondary": "#F4A261",
                "background": "#FFFFFF",
                "foreground": "#111111",
                "muted": "#999999",
            },
            "dark": {
                "primary": "#0A4B6F",
                "secondary": "#F4A261",
                "background": "#0A0A0A",
                "foreground": "#FAFAFA",
                "muted": "#666666",
            },
        },
        "typography": {"sans": "Inter", "heading": "Inter"},
        "register_default": "photographic",
        "logo_asset_id": None,
        "customer_reference_assets": [],
    },
    "style_profile_hint": {
        "lighting": "soft natural window light, welcoming interior",
        "camera_language": "",
        "composition_rules": [],
        "color_grading": "",
        "texture": "",
        "era_mood": None,
        "do_not": ["stock photo smiles", "rendered text", "website mockups"],
        "must_include": [],
    },
}


def build_payload(
    scenario: dict[str, Any],
    *,
    replicate: int,
    hero_viewport: str,
) -> dict[str, Any]:
    site_id = str(uuid.uuid4())
    industry = str(scenario["business"]["industry"])
    label = resolve_industry(industry).label
    return {
        "site_id": site_id,
        "idempotency_key": f"cohort:{scenario['slug']}:r{replicate}:{uuid.uuid4()}",
        "payload_version": "hero_candidates.2",
        "hero_viewport": hero_viewport,
        "default_provider_hint": "openai_image",
        "business": scenario["business"],
        "location": scenario["location"],
        "variants": scenario["variants"],
        "base_seed": 100 + replicate * 17,
        **_SHARED_BRAND,
        "_eval_meta": {"slug": scenario["slug"], "industry_label": label, "replicate": replicate},
    }


@dataclass
class VariantRow:
    slug: str
    industry_label: str
    replicate: int
    run_id: str
    run_status: str
    variant_index: int
    tone_angle: str
    qa_pass: bool
    failure_mode: str
    url: str
    headline: str


@dataclass
class CohortEval:
    base_url: str
    secret: str
    poll_interval_s: float = 8.0
    poll_timeout_s: float = 900.0
    rows: list[VariantRow] = field(default_factory=list)
    run_errors: list[str] = field(default_factory=list)


def _strip_eval_meta(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    out = dict(payload)
    meta = out.pop("_eval_meta", {})
    return out, meta if isinstance(meta, dict) else {}


def submit_and_poll(eval_ctx: CohortEval, payload: dict[str, Any], meta: dict[str, Any]) -> None:
    api_payload, _ = _strip_eval_meta(payload)
    raw = json.dumps(api_payload, separators=(",", ":")).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Arthor-Signature": sign_body(eval_ctx.secret, raw),
    }
    get_sig = sign_body(eval_ctx.secret, b"")

    with httpx.Client(base_url=eval_ctx.base_url, timeout=120.0) as client:
        post = client.post("/images/hero-candidates/generate", content=raw, headers=headers)
        if post.status_code not in (200, 202):
            eval_ctx.run_errors.append(
                f"{meta.get('slug')}: POST {post.status_code} {post.text[:200]}"
            )
            return
        run_id = str(post.json()["agent_run_id"])
        deadline = time.monotonic() + eval_ctx.poll_timeout_s
        body: dict[str, Any] = {}
        while time.monotonic() < deadline:
            poll = client.get(
                f"/images/hero-candidates/{run_id}",
                headers={"X-Arthor-Signature": get_sig},
            )
            body = poll.json()
            status = str(body.get("status") or "")
            if status in ("complete", "partial", "failed"):
                break
            time.sleep(eval_ctx.poll_interval_s)

        urls = body.get("urls") or []
        run_status = str(body.get("status") or "timeout")
        url_by_idx = {int(u.get("variant_index", -1)): u for u in urls if u.get("variant_index") is not None}
        for idx in range(3):
            u = url_by_idx.get(idx, {})
            fm = str(u.get("failure_mode") or "")
            has_url = bool(u.get("url"))
            if not has_url:
                if run_status == "failed":
                    fm = fm or "run_failed"
                elif run_status in ("complete", "partial") and not fm:
                    fm = "missing_upload"
            eval_ctx.rows.append(
                VariantRow(
                    slug=str(meta.get("slug") or ""),
                    industry_label=str(meta.get("industry_label") or ""),
                    replicate=int(meta.get("replicate") or 0),
                    run_id=run_id,
                    run_status=run_status,
                    variant_index=idx,
                    tone_angle=str(u.get("tone_angle") or ""),
                    qa_pass=has_url and not fm,
                    failure_mode=fm or ("pass" if has_url else "no_image"),
                    url=str(u.get("url") or ""),
                    headline=str(u.get("headline") or ""),
                )
            )
        if body.get("error"):
            eval_ctx.run_errors.append(f"{meta.get('slug')} run {run_id}: {body['error']}")


def write_outputs(eval_ctx: CohortEval, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "cohort_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "slug",
                "industry_label",
                "replicate",
                "run_id",
                "run_status",
                "variant_index",
                "tone_angle",
                "qa_pass",
                "failure_mode",
                "url",
                "headline",
            ],
        )
        writer.writeheader()
        for row in eval_ctx.rows:
            writer.writerow(row.__dict__)

    total = len(eval_ctx.rows)
    passed = sum(1 for r in eval_ctx.rows if r.qa_pass)
    failed = total - passed

    by_industry: dict[str, list[VariantRow]] = defaultdict(list)
    for r in eval_ctx.rows:
        by_industry[r.industry_label].append(r)

    fail_modes = Counter(r.failure_mode for r in eval_ctx.rows if not r.qa_pass)
    tone_fails = Counter(
        (r.tone_angle, r.failure_mode) for r in eval_ctx.rows if not r.qa_pass and r.tone_angle
    )

    lines = [
        "# Hero cohort eval summary",
        "",
        f"- **Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"- **Base URL:** {eval_ctx.base_url}",
        f"- **Variants scored:** {total}",
        f"- **QA pass:** {passed} ({100 * passed / total:.1f}%)" if total else "- **QA pass:** 0",
        f"- **QA fail:** {failed} ({100 * failed / total:.1f}%)" if total else "- **QA fail:** 0",
        "",
        "## Pass rate by industry",
        "",
        "| industry_label | pass | fail | pass % | weakest tone |",
        "|---|---:|---:|---:|---|",
    ]
    for label in sorted(by_industry):
        rows = by_industry[label]
        p = sum(1 for r in rows if r.qa_pass)
        f = len(rows) - p
        pct = 100 * p / len(rows) if rows else 0
        tone_fail_counts: Counter[str] = Counter()
        for r in rows:
            if not r.qa_pass:
                tone_fail_counts[r.tone_angle or "?"] += 1
        weakest = tone_fail_counts.most_common(1)[0][0] if tone_fail_counts else "—"
        lines.append(f"| {label} | {p} | {f} | {pct:.0f}% | {weakest} |")

    lines.extend(["", "## Failure modes (all fails)", ""])
    if fail_modes:
        for mode, count in fail_modes.most_common():
            lines.append(f"- `{mode}`: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Failure by tone", ""])
    if tone_fails:
        for (tone, mode), count in tone_fails.most_common():
            lines.append(f"- `{tone}` + `{mode}`: {count}")
    else:
        lines.append("- none")

    if eval_ctx.run_errors:
        lines.extend(["", "## Run-level errors", ""])
        for err in eval_ctx.run_errors:
            lines.append(f"- {err}")

    lines.extend(
        [
            "",
            "## Prompt improvement hints",
            "",
            "Review failed URLs in CSV. Cross-check:",
            "- `rendered_text` / `rendered_ui` → safe-zone or headline-band edge density",
            "- `safe_zone_violation` → left/top quiet zone too busy vs subject",
            "- `palette_drift` → brand stack vs extracted colors",
            "- Industry-specific: compare fail rate column above; tune `hero_archetypes` + serializer invariants",
            "",
        ]
    )

    summary_path = output_dir / "cohort_summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {csv_path} ({total} rows)")
    print(f"Wrote {summary_path}")
    print(f"Review at http://127.0.0.1:8010/inspector/cohort-review?session={output_dir.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hero cohort QA eval across business types")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--replicates", type=int, default=1, help="Triads per industry scenario")
    parser.add_argument("--hero-viewport", default="desktop", choices=("desktop", "mobile"))
    parser.add_argument("--scenarios", nargs="*", default=None, help="Subset of slugs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.fastapi_arthor_shared_secret:
        print("FASTAPI_ARTHOR_SHARED_SECRET unset", file=sys.stderr)
        sys.exit(1)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output or (ROOT / "scratch" / f"hero-cohort-eval-{ts}")

    scenarios = COHORT_SCENARIOS
    if args.scenarios:
        wanted = set(args.scenarios)
        scenarios = [s for s in COHORT_SCENARIOS if s["slug"] in wanted]
        if not scenarios:
            print(f"No scenarios matched {wanted}", file=sys.stderr)
            sys.exit(1)

    plan_count = len(scenarios) * args.replicates * 3
    print(f"Plan: {len(scenarios)} industries × {args.replicates} triad(s) = {plan_count} images")

    if args.dry_run:
        for sc in scenarios:
            for rep in range(args.replicates):
                p = build_payload(sc, replicate=rep, hero_viewport=args.hero_viewport)
                label = resolve_industry(p["business"]["industry"]).label
                print(f"  {sc['slug']} ({label}) replicate={rep}")
        sys.exit(0)

    eval_ctx = CohortEval(base_url=args.base_url.rstrip("/"), secret=settings.fastapi_arthor_shared_secret)
    payload_dir = output_dir / "payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)

    for sc in scenarios:
        for rep in range(args.replicates):
            payload = build_payload(sc, replicate=rep, hero_viewport=args.hero_viewport)
            meta = payload["_eval_meta"]
            slug = sc["slug"]
            print(f"Submitting {slug} replicate={rep} …", flush=True)
            (payload_dir / f"{slug}-r{rep}.json").write_text(
                json.dumps(_strip_eval_meta(payload)[0], indent=2),
                encoding="utf-8",
            )
            submit_and_poll(eval_ctx, payload, meta)

    write_outputs(eval_ctx, output_dir)
    passed = sum(1 for r in eval_ctx.rows if r.qa_pass)
    total = len(eval_ctx.rows)
    print(f"Done: {passed}/{total} passed QA gates")


if __name__ == "__main__":
    main()
