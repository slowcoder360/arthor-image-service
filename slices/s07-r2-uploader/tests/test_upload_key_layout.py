"""s07 AC-2: upload_asset uses key 'arthor-image-service/<site_id>/<asset_id>.<ext>'."""

from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_upload_asset_key_layout():
    try:
        from app.storage.r2 import R2Client  # type: ignore[import-not-found]
        from app.storage.uploader import (  # type: ignore[import-not-found]
            AssetObjectMetadata,
            upload_asset,
        )
    except ImportError as exc:
        pytest.fail(f"AC-2: storage modules must be importable ({exc})")

    captured: dict = {}

    class FakeRawClient:
        async def put_object(self, **kwargs):
            captured.update(kwargs)
            return {"ETag": "fake-etag"}

    class FakeR2Client:
        bucket = "test-bucket"
        client = FakeRawClient()

    site_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    metadata = AssetObjectMetadata(
        run_id=str(uuid.uuid4()),
        slot_id="s-hero",
        agent_run_id=str(uuid.uuid4()),
        provider="openai_image",
        model_version="gpt-image-1",
        prompt_hash="abc123",
        seed=None,
        style_profile_id=str(uuid.uuid4()),
    )

    r2_key = await upload_asset(
        FakeR2Client(),
        image_bytes=b"\x89PNGfake",
        site_id=site_id,
        asset_id=asset_id,
        ext="png",
        content_type="image/png",
        object_metadata=metadata,
    )

    expected_key = f"arthor-image-service/{site_id}/{asset_id}.png"
    assert r2_key == expected_key, (
        f"AC-2: upload_asset must return key {expected_key!r}; got {r2_key!r}"
    )
    assert captured.get("Key") == expected_key, (
        "AC-2: put_object must be called with the documented hybrid key layout"
    )
    assert captured.get("Bucket") == "test-bucket", (
        "AC-2: put_object must use the configured R2 bucket"
    )
    assert captured.get("ContentType") == "image/png", (
        "AC-2: put_object must set ContentType from the call"
    )
