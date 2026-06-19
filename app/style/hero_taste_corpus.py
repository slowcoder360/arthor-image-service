"""Deterministic hero taste corpus — curated plates for builder style pick (no OpenAI)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml

from app.payload.hero_models import HeroCandidatesRequest, variant_to_slot
from app.storage.asset_writer import insert_pending_asset, mark_asset_uploaded
from app.storage.uploader import browser_url_for
from app.style.hero_archetypes import HeroJob, resolve_industry
from app.style.hero_visual_strategy import SceneArchetypeId
from app.style.profile import StyleProfile

CORPUS_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "hero_taste_corpus"


@dataclass(frozen=True)
class CorpusVariantEntry:
    variant_index: int
    scene_archetype: SceneArchetypeId
    hero_job: HeroJob
    r2_key: str
    public_url: str | None
    style_profile_fragment: dict[str, Any]
    compiler_version: str
    approved_at: str
    approved_by: str


@dataclass(frozen=True)
class CorpusTriad:
    corpus_version: str
    industry_label: str
    variants: tuple[CorpusVariantEntry, CorpusVariantEntry, CorpusVariantEntry]
    slug: str | None = None
    match_keys: tuple[str, ...] = ()


def _parse_variant(raw: dict[str, Any]) -> CorpusVariantEntry:
    fragment = raw.get("style_profile_fragment") or {}
    if not isinstance(fragment, dict):
        fragment = {}
    return CorpusVariantEntry(
        variant_index=int(raw["variant_index"]),
        scene_archetype=raw["scene_archetype"],
        hero_job=raw["hero_job"],
        r2_key=str(raw["r2_key"]),
        public_url=str(raw["public_url"]) if raw.get("public_url") else None,
        style_profile_fragment=fragment,
        compiler_version=str(raw.get("compiler_version") or "4.1"),
        approved_at=str(raw.get("approved_at") or ""),
        approved_by=str(raw.get("approved_by") or ""),
    )


def _triad_from_dict(data: dict[str, Any]) -> CorpusTriad | None:
    raw_variants = data.get("variants")
    if not isinstance(raw_variants, list) or len(raw_variants) != 3:
        return None
    try:
        variants = tuple(_parse_variant(v) for v in raw_variants)
    except (KeyError, TypeError, ValueError):
        return None
    indices = sorted(v.variant_index for v in variants)
    if indices != [0, 1, 2]:
        return None
    match_keys_raw = data.get("match_keys") or []
    if isinstance(match_keys_raw, str):
        match_keys_raw = [match_keys_raw]
    match_keys = tuple(str(k).strip().lower() for k in match_keys_raw if str(k).strip())
    slug = str(data["slug"]).strip() if data.get("slug") else None
    return CorpusTriad(
        corpus_version=str(data.get("corpus_version") or "1.0"),
        industry_label=str(data.get("industry_label") or slug or ""),
        slug=slug,
        match_keys=match_keys,
        variants=variants,  # type: ignore[return-value]
    )


@lru_cache(maxsize=64)
def _load_corpus_file(industry_label: str, corpus_version: str) -> CorpusTriad | None:
    path = CORPUS_DATA_ROOT / f"v{corpus_version.split('.')[0]}" / f"{industry_label}.yaml"
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        return None
    return _triad_from_dict(data)


@lru_cache(maxsize=1)
def _v2_slug_index() -> tuple[tuple[tuple[str, ...], CorpusTriad], ...]:
    version_dir = CORPUS_DATA_ROOT / "v2"
    if not version_dir.is_dir():
        return ()
    entries: list[tuple[tuple[str, ...], CorpusTriad]] = []
    for path in sorted(version_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if not isinstance(data, dict):
            continue
        triad = _triad_from_dict(data)
        if triad is None:
            continue
        keys = triad.match_keys or (triad.slug or path.stem, triad.industry_label)
        entries.append((keys, triad))
    return tuple(entries)


def _resolve_v2_by_match_keys(industry: str) -> CorpusTriad | None:
    low = industry.lower()
    best: tuple[int, CorpusTriad] | None = None
    for keys, triad in _v2_slug_index():
        for key in keys:
            k = key.lower()
            if k and k in low:
                if best is None or len(k) > best[0]:
                    best = (len(k), triad)
    return best[1] if best else None


def resolve_taste_corpus(industry: str, *, corpus_version: str = "2.0") -> CorpusTriad | None:
    """Resolve corpus triad — v2 slug match_keys (longest win), then v1 coarse fallback."""
    major = corpus_version.split(".")[0]
    if major == "2":
        triad = _resolve_v2_by_match_keys(industry)
        if triad is not None:
            return triad
        ctx = resolve_industry(industry)
        triad = _load_corpus_file(ctx.label, "1.0")
        if triad is None and ctx.label != "general_services":
            triad = _load_corpus_file("general_services", "1.0")
        return triad

    ctx = resolve_industry(industry)
    triad = _load_corpus_file(ctx.label, corpus_version)
    if triad is None and ctx.label != "general_services":
        triad = _load_corpus_file("general_services", corpus_version)
    return triad


def load_corpus_triad(industry_label: str, *, corpus_version: str = "1.0") -> CorpusTriad | None:
    """Load one v1 industry corpus file — no fallback (inspector / admin)."""
    return _load_corpus_file(industry_label, corpus_version)


def load_corpus_slug(slug: str, *, corpus_version: str = "2.0") -> CorpusTriad | None:
    """Load one v2 slug corpus file — no fallback."""
    return _load_corpus_file(slug, corpus_version)


def list_corpus_industries(*, corpus_version: str = "1.0") -> list[str]:
    version_dir = CORPUS_DATA_ROOT / f"v{corpus_version.split('.')[0]}"
    if not version_dir.is_dir():
        return []
    return sorted(p.stem for p in version_dir.glob("*.yaml"))


def corpus_coverage(*, corpus_version: str = "1.0") -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for label in list_corpus_industries(corpus_version=corpus_version):
        triad = _load_corpus_file(label, corpus_version)
        if triad is None:
            continue
        key = triad.slug or triad.industry_label or label
        out[key] = sorted(v.variant_index for v in triad.variants)
    return out


def _corpus_prompt_hash(entry: CorpusVariantEntry) -> str:
    blob = json.dumps({"r2_key": entry.r2_key, "scene": entry.scene_archetype}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


async def fulfill_corpus_hero_run(
    pool: Any,
    *,
    run_id: uuid.UUID,
    request: HeroCandidatesRequest,
    style_profile: StyleProfile,
    corpus: CorpusTriad,
    settings: Any,
) -> None:
    """Insert three uploaded corpus assets synchronously — no provider call."""
    for entry in corpus.variants:
        variant = request.variants[entry.variant_index]
        slot = variant_to_slot(request, variant, entry.variant_index)
        prompt_hash = _corpus_prompt_hash(entry)
        pending_meta: dict[str, Any] = {
            "slot_id": slot.slot_id,
            "slot_intent": slot.intent,
            "style_profile_id": str(style_profile.id),
            "prompt_hash": prompt_hash,
            "seed": int(request.base_seed + entry.variant_index),
            "determinism_level": "deterministic",
            "run_id": str(run_id),
            "hero_candidate": True,
            "variant_index": entry.variant_index,
            "tone_angle": variant.tone_angle,
            "headline": variant.headline,
            "subhead": variant.subhead,
            "scene_archetype": entry.scene_archetype,
            "style_profile_fragment": entry.style_profile_fragment,
            "corpus_backed": True,
            "corpus_version": corpus.corpus_version,
            "corpus_industry_label": corpus.industry_label,
            "hero_job": entry.hero_job,
        }
        if corpus.slug:
            pending_meta["corpus_slug"] = corpus.slug
        asset_id = await insert_pending_asset(
            pool,
            agent_run_id=run_id,
            site_id=request.site_id,
            provider="corpus",
            model_version=f"v{corpus.corpus_version}",
            metadata=pending_meta,
        )
        stored_url = entry.public_url
        url = browser_url_for(
            settings,
            r2_key=entry.r2_key,
            stored_url=stored_url,
        )
        await mark_asset_uploaded(pool, asset_id, r2_key=entry.r2_key, r2_url=url)


def clear_corpus_cache() -> None:
    _load_corpus_file.cache_clear()
    _v2_slug_index.cache_clear()
