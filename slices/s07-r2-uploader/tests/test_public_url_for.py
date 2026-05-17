"""s07 AC-4: public_url_for composes '<endpoint>/<bucket>/<key>'."""

from __future__ import annotations

import pytest

from _settings import FakeR2Settings


def test_public_url_for_composes_endpoint_bucket_key():
    try:
        from app.storage.uploader import public_url_for  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: public_url_for must be importable ({exc})")

    settings = FakeR2Settings(
        r2_endpoint_url="https://r2.example.com",
        r2_bucket="my-bucket",
    )
    url = public_url_for(settings, "arthor-image-service/site/asset.png")
    assert (
        url == "https://r2.example.com/my-bucket/arthor-image-service/site/asset.png"
    ), f"AC-4: public_url_for must compose '<endpoint>/<bucket>/<key>'; got {url!r}"
