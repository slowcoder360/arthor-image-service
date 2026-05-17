"""Shared DB helpers for s05 tests. NOT a test module."""

from __future__ import annotations

import os

import pytest


async def make_pool():
    try:
        import asyncpg
    except ImportError as exc:
        pytest.fail(f"asyncpg is not installed: {exc}")
    return await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
