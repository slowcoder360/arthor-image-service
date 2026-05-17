"""Mini Settings stub for s07 tests; matches the field set R2Client.from_settings reads."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FakeR2Settings:
    r2_endpoint_url: str | None = "https://r2.example.com"
    r2_access_key_id: str | None = "test-access"
    r2_secret_access_key: str | None = "test-secret"
    r2_bucket: str | None = "test-bucket"


def fully_unset() -> FakeR2Settings:
    return FakeR2Settings(
        r2_endpoint_url=None,
        r2_access_key_id=None,
        r2_secret_access_key=None,
        r2_bucket=None,
    )
