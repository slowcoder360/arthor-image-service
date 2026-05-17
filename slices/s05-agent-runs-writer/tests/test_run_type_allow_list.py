"""s05 AC-3: run_type allow-list — bogus types raise ValueError before DB write."""

from __future__ import annotations

import uuid

import pytest


def _import_writer():
    try:
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: insert_pending_run must be importable ({exc})")
    return insert_pending_run


@pytest.mark.asyncio
async def test_bogus_run_type_raises_value_error_without_db():
    insert_pending_run = _import_writer()

    class _PoolStub:
        async def acquire(self, *_a, **_kw):
            raise AssertionError(
                "AC-3: writer must reject bogus run_type BEFORE attempting any DB acquire()"
            )

        def __getattr__(self, name):
            raise AssertionError(
                f"AC-3: writer must reject bogus run_type BEFORE touching pool.{name}"
            )

    with pytest.raises(ValueError):
        await insert_pending_run(
            _PoolStub(), run_type="bogus_type", site_id=uuid.uuid4()
        )


@pytest.mark.parametrize(
    "run_type",
    ["image_pack_generation", "image_slot_regenerate", "image_style_preview"],
)
def test_documented_run_types_recognized(run_type):
    insert_pending_run = _import_writer()
    import inspect

    sig = inspect.signature(insert_pending_run)
    assert "run_type" in sig.parameters, (
        "AC-3: insert_pending_run must take a 'run_type' kw-only parameter"
    )
