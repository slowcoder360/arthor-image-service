"""Process-wide service handles attached to FastAPI app.state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.config import Settings


@dataclass
class RuntimeServices:
    """Thin dataclass; downstream slices populate optional fields in lifespan."""

    settings: Settings
    pool: object | None = None
    r2: object | None = None
    asset_pack_semaphore: object | None = None
    providers: dict[str, object] | None = None
    prompt_improver: object | None = None
    background_tasks: list[asyncio.Task[object]] = field(default_factory=list)
