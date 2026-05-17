"""s05 AC-4: insert_tool_call uses FK column run_id (NOT agent_run_id) — ADR-0004 critical drift."""

from __future__ import annotations

import uuid

import pytest

from _db_helpers import make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_insert_tool_call_round_trips_cost_provider_and_uses_run_id_column():
    try:
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runs.tool_calls import insert_tool_call  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: writers must be importable ({exc})")

    pool = await make_pool()
    try:
        run_id = await insert_pending_run(
            pool, run_type="image_pack_generation", site_id=uuid.uuid4()
        )
        tc_id = await insert_tool_call(
            pool,
            run_id=run_id,
            tool_name="openai.images.generate",
            args={"prompt_hash": "abc123"},
            result={"external_id": "img_123"},
            status="ok",
            latency_ms=420,
            cost_cents=7,
            provider="openai_image",
            model_version="gpt-image-1",
        )
        assert isinstance(tc_id, int) and tc_id > 0, (
            "AC-4: insert_tool_call must return a positive bigserial id"
        )
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT run_id, tool_name, status, cost_cents, provider, model_version "
                "FROM tool_calls WHERE id = $1",
                tc_id,
            )
        assert row is not None, "AC-4: tool_call row must persist"
        assert row["run_id"] == run_id, (
            "AC-4 (ADR-0004 critical drift): FK column on tool_calls is `run_id`, "
            "must equal the parent agent_runs.id"
        )
        assert row["cost_cents"] == 7, "AC-4: cost_cents must round-trip"
        assert row["provider"] == "openai_image", "AC-4: provider must round-trip"
        assert row["model_version"] == "gpt-image-1", "AC-4: model_version must round-trip"

        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM tool_calls WHERE id = $1", tc_id)
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
    finally:
        await pool.close()
