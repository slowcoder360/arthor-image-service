# R2 retention and cold storage

## 30 days then cold

Superseded `external_media_assets` rows older than **30 days** may be rotated from their warm keys to **`cold/`** prefixed keys in R2 by the background cron.

## Prefix convention (`cold/`)

Rotated objects are stored under keys that begin with `cold/` relative to their original paths (see `cold/<original-key>`).

## Cron interval

The worker sleeps between sweeps according to **`cold_storage_interval_seconds`** (default 86400; one **interval** equals one day). Set `cold_storage_interval_seconds = 0` to disable the worker (useful for local development).

## Active assets

**Active assets** (`status = uploaded`) are never rotated; they remain on warm keys indefinitely regardless of age.

## Recovery procedure (manual)

To restore from cold prefix to a warm key: copy server-side (`aws s3 cp s3://bucket/cold/<key> s3://bucket/<key>` or equivalent against your R2/S3-compatible endpoint), then update the corresponding `external_media_assets` row. There is no automatic recovery path in v1.
