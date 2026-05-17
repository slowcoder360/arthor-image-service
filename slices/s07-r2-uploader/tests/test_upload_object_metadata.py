"""s07 AC-3: put_object Metadata={...} carries every required key; seed=None → ''."""

from __future__ import annotations

import uuid

import pytest


REQUIRED_KEYS = {
    "run_id",
    "slot_id",
    "agent_run_id",
    "provider",
    "model_version",
    "prompt_hash",
    "seed",
    "style_profile_id",
}


@pytest.mark.asyncio
async def test_object_metadata_dict_renders_required_keys_with_seed_none_as_empty_string():
    try:
        from app.storage.uploader import (  # type: ignore[import-not-found]
            AssetObjectMetadata,
            upload_asset,
        )
    except ImportError as exc:
        pytest.fail(f"AC-3: storage modules must be importable ({exc})")

    captured: dict = {}

    class FakeRawClient:
        async def put_object(self, **kwargs):
            captured.update(kwargs)
            return {"ETag": "fake-etag"}

    class FakeR2Client:
        bucket = "test-bucket"
        client = FakeRawClient()

    metadata = AssetObjectMetadata(
        run_id="r-1",
        slot_id="s-hero",
        agent_run_id="ar-1",
        provider="openai_image",
        model_version="gpt-image-1",
        prompt_hash="hash-1",
        seed=None,
        style_profile_id="sp-1",
    )

    await upload_asset(
        FakeR2Client(),
        image_bytes=b"x",
        site_id=uuid.uuid4(),
        asset_id=uuid.uuid4(),
        ext="png",
        content_type="image/png",
        object_metadata=metadata,
    )

    md = captured.get("Metadata")
    assert isinstance(md, dict), "AC-3: put_object must be called with Metadata=dict"
    missing = REQUIRED_KEYS - set(md.keys())
    assert not missing, f"AC-3: Metadata is missing required keys {missing}"
    assert all(isinstance(v, str) for v in md.values()), (
        "AC-3: every R2 metadata value must be a string"
    )
    assert md["seed"] == "", "AC-3: seed=None must render as the empty string"
    assert md["provider"] == "openai_image", "AC-3: provider must round-trip"
    assert md["prompt_hash"] == "hash-1", "AC-3: prompt_hash must round-trip"
