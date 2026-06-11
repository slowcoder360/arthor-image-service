"""Hybrid-key upload helper and public URL composition for R2 objects."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

_KEY_RE = re.compile(r"^[a-z0-9_]+$")


@runtime_checkable
class HasBucketAndClient(Protocol):
    bucket: str
    client: Any


@dataclass(frozen=True)
class AssetObjectMetadata:
    """Fields mirrored into S3 object Metadata (string-typed)."""

    run_id: str
    slot_id: str
    agent_run_id: str
    provider: str
    model_version: str
    prompt_hash: str
    seed: int | None
    style_profile_id: str

    def as_metadata_dict(self) -> dict[str, str]:
        pairs: dict[str, str] = {
            "run_id": self.run_id,
            "slot_id": self.slot_id,
            "agent_run_id": self.agent_run_id,
            "provider": self.provider,
            "model_version": self.model_version,
            "prompt_hash": self.prompt_hash,
            "seed": "" if self.seed is None else str(self.seed),
            "style_profile_id": self.style_profile_id,
        }
        for key, value in pairs.items():
            if not _KEY_RE.match(key):
                raise ValueError(f"Invalid R2 metadata key (lowercase ASCII expected): {key!r}")
            if not isinstance(value, str):
                raise TypeError(f"R2 metadata values must be str; {key!r} is {type(value)}")
        return pairs


@runtime_checkable
class HasR2UrlParts(Protocol):
    r2_endpoint_url: str | None
    r2_bucket: str | None
    r2_public_url: str | None


def public_url_for(settings: HasR2UrlParts, r2_key: str) -> str:
    """Browser-loadable URL for an object key.

    Prefer ``R2_PUBLIC_URL`` (``pub-*.r2.dev`` or custom domain) when set.
    The S3 API endpoint is not usable in ``<img src>`` tags.
    """
    public_base = getattr(settings, "r2_public_url", None)
    if public_base:
        return f"{public_base.rstrip('/')}/{r2_key.lstrip('/')}"
    base = settings.r2_endpoint_url or ""
    bucket = settings.r2_bucket or ""
    return f"{base}/{bucket}/{r2_key}"


def browser_url_for(
    settings: HasR2UrlParts,
    *,
    r2_key: str | None,
    stored_url: str | None = None,
) -> str:
    """Resolve a stored ``r2_url`` for browser display (fixes legacy S3 API URLs)."""
    if r2_key:
        return public_url_for(settings, r2_key)
    return stored_url or ""


async def upload_asset(
    r2: HasBucketAndClient,
    *,
    image_bytes: bytes,
    site_id: uuid.UUID,
    asset_id: uuid.UUID,
    ext: str,
    content_type: str,
    object_metadata: AssetObjectMetadata,
) -> str:
    """Upload bytes to the configured bucket; return deterministic object key."""
    r2_key = f"arthor-image-service/{site_id}/{asset_id}.{ext}"
    await r2.client.put_object(
        Bucket=r2.bucket,
        Key=r2_key,
        Body=image_bytes,
        ContentType=content_type,
        Metadata=object_metadata.as_metadata_dict(),
    )
    return r2_key


async def upload_asset_at_key(
    r2: HasBucketAndClient,
    *,
    image_bytes: bytes,
    r2_key: str,
    content_type: str,
    object_metadata: AssetObjectMetadata,
) -> str:
    """Upload bytes to an explicit object key (hero-candidates temp prefix)."""
    await r2.client.put_object(
        Bucket=r2.bucket,
        Key=r2_key,
        Body=image_bytes,
        ContentType=content_type,
        Metadata=object_metadata.as_metadata_dict(),
    )
    return r2_key
