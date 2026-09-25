# Lifespan & Configuration — Examples

Ready-to-use code for the FastAPI application factory, lifespan context
manager, and Pydantic v2 BaseSettings config.

---

## Application Factory

```python
# src/main.py
from __future__ import annotations

from fastapi import FastAPI

from src.api.v1 import agents as agents_router
from src.api.v1 import webhook as webhook_router
from src.core.lifespan import lifespan


def create_app() -> FastAPI:
    """Application factory — called by Uvicorn with ``--factory``."""
    app = FastAPI(
        title="Multi-Agent Microservice",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(agents_router.router, prefix="/api/v1")
    app.include_router(webhook_router.router)
    return app
```

---

## Lifespan Context Manager

```python
# src/core/lifespan.py
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from google.cloud import tasks_v2
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config import Settings
from src.core.telemetry import setup_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage shared resources across the application lifecycle.

    Everything before ``yield`` runs on startup.
    Everything after ``yield`` runs on shutdown.
    """
    settings = Settings()
    app.state.settings = settings

    # ── Telemetry ───────────────────────────────────────────────
    setup_telemetry(service_name=settings.service_name)

    # ── Database ────────────────────────────────────────────────
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    app.state.async_session_factory = async_sessionmaker(
        engine, expire_on_commit=False,
    )

    # ── HTTP client ─────────────────────────────────────────────
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        app.state.http_client = http_client

        # ── Cloud Tasks client ──────────────────────────────────
        app.state.tasks_client = tasks_v2.CloudTasksAsyncClient()

        yield  # ← App is running

    # ── Shutdown ────────────────────────────────────────────────
    await engine.dispose()
```

> **Key point:** Resources are attached to `app.state` so that
> `dependencies.py` can access them via `request.app.state`. This avoids
> module-level singletons and makes everything overridable in tests.

---

## Pydantic v2 BaseSettings

```python
# src/core/config.py
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised, validated configuration.

    Missing **required** fields (no default) cause an immediate
    ``ValidationError`` at startup — fail fast.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Service ─────────────────────────────────────────────────
    service_name: str = Field(
        default="multi-agent-service",
        description="Logical service name used in telemetry and logging.",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode. Never True in production.",
    )

    # ── Database ────────────────────────────────────────────────
    database_url: str = Field(
        ...,
        description="Async database connection string (e.g. postgresql+asyncpg://...).",
    )
    db_pool_size: int = Field(
        default=5,
        ge=1,
        description="SQLAlchemy async engine connection pool size.",
    )
    db_max_overflow: int = Field(
        default=10,
        ge=0,
        description="Max number of connections above pool_size before blocking.",
    )

    # ── GCP ─────────────────────────────────────────────────────
    gcp_project_id: str = Field(
        ...,
        description="GCP project ID for Cloud Tasks, Cloud Trace, and GCS.",
    )
    cloud_tasks_queue: str = Field(
        default="agent-jobs",
        description="Cloud Tasks queue name for async agent dispatch.",
    )
    cloud_tasks_location: str = Field(
        default="us-central1",
        description="GCP region where the Cloud Tasks queue is provisioned.",
    )
    gcs_bucket: str = Field(
        default="agent-artifacts",
        description="GCS bucket for storing agent artifacts and results.",
    )

    # ── Auth ────────────────────────────────────────────────────
    webhook_secret: str = Field(
        default="",
        description="Shared secret for webhook payload validation. Must be set in production.",
    )
```

---

## Global Exception Handler

```python
# src/core/exceptions.py
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import structlog

logger = structlog.get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request, exc: ValueError,
    ) -> JSONResponse:
        logger.warning("value_error", detail=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception,
    ) -> JSONResponse:
        logger.exception("unhandled_error", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
```
