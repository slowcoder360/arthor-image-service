"""Async S3-compatible client configured for Cloudflare R2."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import aiobotocore.session


class ConfigurationError(RuntimeError):
    """Raised when R2 credentials or endpoint configuration is incomplete."""


@runtime_checkable
class HasR2Settings(Protocol):
    r2_endpoint_url: str | None
    r2_access_key_id: str | None
    r2_secret_access_key: str | None
    r2_bucket: str | None


def _require_full_r2_settings(settings: HasR2Settings) -> None:
    endpoint = getattr(settings, "r2_endpoint_url", None)
    key_id = getattr(settings, "r2_access_key_id", None)
    secret = getattr(settings, "r2_secret_access_key", None)
    bucket = getattr(settings, "r2_bucket", None)
    if endpoint and key_id and secret and bucket:
        return
    raise ConfigurationError(
        "Incomplete R2 configuration: r2_endpoint_url, r2_access_key_id, "
        "r2_secret_access_key, and r2_bucket must all be set"
    )


class R2Client:
    """Thin wrapper holding an aiobotocore ``AioBaseClient`` for S3/R2."""

    __slots__ = ("_client_cm", "_cfg", "_session", "client")

    def __init__(self, settings: HasR2Settings) -> None:
        _require_full_r2_settings(settings)
        self._cfg = settings
        self._session: Any = None
        self._client_cm: Any = None
        self.client: Any | None = None

    @property
    def bucket(self) -> str:
        b = self._cfg.r2_bucket
        if not b:
            raise RuntimeError("R2 bucket unchecked after validation")
        return b

    @classmethod
    def from_settings(cls, settings: HasR2Settings) -> R2Client:
        _require_full_r2_settings(settings)
        return cls(settings)

    async def __aenter__(self) -> R2Client:
        session = aiobotocore.session.get_session()
        self._session = session
        self._client_cm = session.create_client(
            "s3",
            endpoint_url=self._cfg.r2_endpoint_url,
            aws_access_key_id=self._cfg.r2_access_key_id,
            aws_secret_access_key=self._cfg.r2_secret_access_key,
            region_name="auto",
        )
        assert self._client_cm is not None
        self.client = await self._client_cm.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._client_cm is None:
            return
        await self._client_cm.__aexit__(exc_type, exc, tb)
        self._client_cm = None
        self.client = None
        self._session = None


async def move_to_cold_storage(r2: Any, *, src_key: str) -> str:
    """Copy ``src_key`` to ``cold/<src_key>`` server-side then delete the original."""
    bucket = r2.bucket
    client = r2.client
    new_key = f"cold/{src_key}"
    await client.copy_object(
        Bucket=bucket,
        CopySource={"Bucket": bucket, "Key": src_key},
        Key=new_key,
    )
    await client.delete_object(Bucket=bucket, Key=src_key)
    return new_key
