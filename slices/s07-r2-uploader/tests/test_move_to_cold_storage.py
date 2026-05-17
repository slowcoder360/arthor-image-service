"""s07 AC-9: move_to_cold_storage copies + deletes; returns 'cold/<src_key>'."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_move_to_cold_storage_copies_and_deletes():
    try:
        from app.storage.r2 import move_to_cold_storage  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-9: move_to_cold_storage must be importable ({exc})")

    copy_calls: list[dict] = []
    delete_calls: list[dict] = []

    class FakeRawClient:
        async def copy_object(self, **kwargs):
            copy_calls.append(kwargs)
            return {"CopyObjectResult": {"ETag": "fake"}}

        async def delete_object(self, **kwargs):
            delete_calls.append(kwargs)
            return {"DeleteMarker": True}

    class FakeR2Client:
        bucket = "test-bucket"
        client = FakeRawClient()

    src_key = "arthor-image-service/site-1/asset-1.png"
    new_key = await move_to_cold_storage(FakeR2Client(), src_key=src_key)

    assert new_key == f"cold/{src_key}", (
        f"AC-9: move_to_cold_storage must return 'cold/<src>'; got {new_key!r}"
    )
    assert len(copy_calls) == 1, "AC-9: must copy_object exactly once"
    assert len(delete_calls) == 1, "AC-9: must delete_object exactly once"
    assert delete_calls[0].get("Key") == src_key, (
        "AC-9: delete_object must target the original key"
    )
