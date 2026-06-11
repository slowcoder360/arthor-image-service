"""FastAPI entrypoint for arthor-image-service."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import Response

from app.config import Settings
from app.inspector.router import router as inspector_router
from app.jobs.cold_storage import cold_storage_worker
from app.routes.asset_pack import router as asset_pack_router
from app.routes.hero_candidates import router as hero_candidates_router
from app.routes.regenerate_slot import router as regenerate_slot_router
from app.routes.style_preview import router as style_preview_router
from app.runtime import RuntimeServices

logger = logging.getLogger(__name__)

_missing_database_url_logged = False
_missing_r2_config_logged = False


def configure_logging() -> None:
    settings = Settings()
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def ensure_runtime_ready(app: FastAPI) -> None:
    """Idempotent app startup: services + optional DB pool.

    Uvicorn sends ASGI ``lifespan`` events; pure HTTP in-process clients (for example
    ``httpx.ASGITransport``) do not. The HTTP middleware invokes this on each request
    so ``app.state.services`` — and ``services.pool`` when ``database_url`` is set —
    match production behaviour without a second code path for tests.
    """
    global _missing_database_url_logged
    services = getattr(app.state, "services", None)
    if services is None:
        configure_logging()
        app.state.services = RuntimeServices(settings=Settings())
        services = app.state.services

    assert services is not None
    settings = services.settings

    if getattr(services, "asset_pack_semaphore", None) is None:
        services.asset_pack_semaphore = asyncio.Semaphore(settings.max_concurrent_packs)

    if getattr(services, "prompt_improver", None) is None:
        from app.style.prompt_improver import build_prompt_improver

        services.prompt_improver = build_prompt_improver(settings)

    if settings.database_url:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if services.pool is not None and running_loop is not None:
            pool_loop = getattr(services.pool, "_loop", None)
            if pool_loop is not running_loop:
                # pytest-asyncio gives each test a fresh loop while ``app.state`` persists.
                # asyncpg pools are loop-bound; dropping the reference avoids "different loop"
                # errors. (Leaks an idle pool in multi-loop test runs only.)
                services.pool = None

        if services.pool is None:
            from db.pool import init_pool

            services.pool = await init_pool(settings.database_url)
        return

    if services.pool is None:
        msg = (
            "database_url is unset; DATABASE_URL / settings.database_url missing — "
            "persistence disabled (no asyncpg pool)"
        )
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.warning(msg)
        elif not _missing_database_url_logged:
            logger.warning(msg)
            _missing_database_url_logged = True


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    global _missing_r2_config_logged
    await ensure_runtime_ready(app)

    services = getattr(app.state, "services", None)
    if services is not None:
        st = services.settings
        if (
            st.r2_endpoint_url
            and st.r2_access_key_id
            and st.r2_secret_access_key
            and st.r2_bucket
        ):
            from app.storage.r2 import R2Client

            r2_cm = R2Client.from_settings(st)
            services.r2 = await r2_cm.__aenter__()
        else:
            if not _missing_r2_config_logged:
                logger.warning(
                    "r2_* settings incomplete; skipping R2 client initialization "
                    "(services.r2 unset)"
                )
                _missing_r2_config_logged = True
            services.r2 = None

        services.background_tasks.append(
            asyncio.create_task(cold_storage_worker(services))
        )

    try:
        yield
    finally:
        services = getattr(app.state, "services", None)
        if services is not None:
            for task in list(services.background_tasks):
                task.cancel()
            for task in list(services.background_tasks):
                with suppress(asyncio.CancelledError, TimeoutError):
                    await asyncio.wait_for(task, timeout=5)
        if services is not None and services.r2 is not None:
            await services.r2.__aexit__(None, None, None)
            services.r2 = None
        if services is not None and services.pool is not None:
            from db.pool import close_pool

            await close_pool(services.pool)


app = FastAPI(title="arthor-image-service v1", lifespan=lifespan)
app.include_router(asset_pack_router)
app.include_router(hero_candidates_router)
app.include_router(style_preview_router)
app.include_router(regenerate_slot_router)
_INSPECTOR_STATIC_DIR = Path(__file__).resolve().parent / "inspector" / "static"
app.mount(
    "/inspector/static",
    StaticFiles(directory=str(_INSPECTOR_STATIC_DIR)),
    name="inspector_static",
)
app.include_router(inspector_router, prefix="/inspector")


@app.middleware("http")
async def ensure_runtime_services(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    await ensure_runtime_ready(request.app)
    return await call_next(request)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "arthor-image-service",
        "version": "0.1.0",
    }


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
