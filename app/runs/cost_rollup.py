"""Roll ``tool_calls`` spend and token counters onto ``agent_runs``."""

from __future__ import annotations

import uuid

import asyncpg
import asyncpg.exceptions


async def roll_up_cost(pool: asyncpg.pool.Pool, run_id: uuid.UUID) -> int:
    """Sum child ``tool_calls`` into the parent run; returns new ``cost_cents``."""
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                UPDATE agent_runs
                SET cost_cents = (
                    SELECT COALESCE(SUM(cost_cents), 0) FROM tool_calls WHERE run_id = $1
                  ),
                  prompt_tokens = (
                    SELECT COALESCE(SUM(prompt_tokens), 0) FROM tool_calls WHERE run_id = $1
                  ),
                  completion_tokens = (
                    SELECT COALESCE(SUM(completion_tokens), 0)
                    FROM tool_calls WHERE run_id = $1
                  ),
                  finished_at = COALESCE(finished_at, now())
                WHERE id = $1
                RETURNING cost_cents
                """,
                run_id,
            )
        except (
            asyncpg.exceptions.UndefinedColumnError,
            asyncpg.exceptions.GroupingError,
        ):
            row = await conn.fetchrow(
                """
                UPDATE agent_runs
                SET cost_cents = (
                    SELECT COALESCE(SUM(cost_cents), 0) FROM tool_calls WHERE run_id = $1
                  ),
                  prompt_tokens = 0,
                  completion_tokens = 0,
                  finished_at = COALESCE(finished_at, now())
                WHERE id = $1
                RETURNING cost_cents
                """,
                run_id,
            )
    assert row is not None
    return int(row["cost_cents"])
