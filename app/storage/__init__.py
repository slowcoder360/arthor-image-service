"""Object storage primitives (Cloudflare R2 / S3-compatible)."""

from __future__ import annotations

from app.storage.asset_writer import (
    InvalidStateTransition,
    insert_pending_asset,
    mark_asset_failed,
    mark_asset_generated,
    mark_asset_uploaded,
)
from app.storage.r2 import ConfigurationError, R2Client, move_to_cold_storage
from app.storage.supersession import UnsupersedeUnavailable, supersede_asset, unsupersede_asset
from app.storage.uploader import AssetObjectMetadata, public_url_for, upload_asset

__all__ = [
    "AssetObjectMetadata",
    "ConfigurationError",
    "InvalidStateTransition",
    "R2Client",
    "UnsupersedeUnavailable",
    "insert_pending_asset",
    "mark_asset_failed",
    "mark_asset_generated",
    "mark_asset_uploaded",
    "move_to_cold_storage",
    "public_url_for",
    "supersede_asset",
    "unsupersede_asset",
    "upload_asset",
]
