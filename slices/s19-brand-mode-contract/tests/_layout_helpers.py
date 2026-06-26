"""Shared helpers for s19 hero-candidates route tests (mocked provider + in-memory pool).

Mirrors tests/test_hero_candidates.py so the layout-decision assertions run without a DB.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class _FakeCall:
    method: str
    slot_id: str | None


class FakeProvider:
    def __init__(self, name: str = "google_nano_banana") -> None:
        self.name = name
        self.supports_reference_image = False
        self.supports_pack_consistent = False
        self.model_version = "fake-hero-v1"
        self.calls: list[_FakeCall] = []

    async def generate_single(self, **kwargs: Any):
        self.calls.append(_FakeCall("generate_single", kwargs.get("slot_id")))
        from app.providers.protocol import ProviderResult

        return ProviderResult(
            image_bytes=b"\x89PNGfake-hero",
            width=1920,
            height=1080,
            seed=kwargs.get("seed"),
            provider=self.name,
            model_version=self.model_version,
            cost_cents=2,
            latency_ms=3,
            external_id="fake-ext",
            response_shape={},
            determinism_level="best-effort",
        )


def build_hero_request(*, industry: str = "dental", **overrides: Any) -> dict[str, Any]:
    site_id = str(uuid.uuid4())
    req: dict[str, Any] = {
        "site_id": site_id,
        "idempotency_key": f"hero:{site_id}:abc123hash",
        "business": {
            "site_name": "Acme Co",
            "industry": industry,
            "icp_summary": "local customers",
            "value_prop": "great service",
            "proof_points": [],
            "forbidden_subjects": [],
            "priority_services": [],
        },
        "location": {
            "mode": "local",
            "country": "US",
            "city": "Austin",
            "region": "TX",
            "service_areas": [],
        },
        "brand_voice": {
            "tone": "warm",
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
            "lighting": "soft natural window light",
            "camera_language": "",
            "composition_rules": [],
            "color_grading": "",
            "texture": "",
            "era_mood": None,
            "do_not": [],
            "must_include": [],
        },
        "variants": [
            {"tone_angle": "search", "headline": "Find us in Austin", "subhead": "Same-week service"},
            {"tone_angle": "story", "headline": "Care that feels personal", "subhead": "Built around you"},
            {"tone_angle": "offer", "headline": "Book this week", "subhead": "Transparent pricing"},
        ],
        "base_seed": 77,
        "default_provider_hint": "google_nano_banana",
    }
    req.update(overrides)
    return req


async def prepare_app(monkeypatch, tmp_path, *, pool: Any = None):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from tests._hero_fake_pool import HeroFakePool

    from app.main import app, ensure_runtime_ready

    await ensure_runtime_ready(app)
    fake = FakeProvider()
    services = app.state.services
    services.pool = pool or HeroFakePool()
    services.providers = {"google_nano_banana": fake, "openai_image": fake}
    services.r2 = None
    services.asset_pack_semaphore = asyncio.Semaphore(4)
    return app, fake, services
