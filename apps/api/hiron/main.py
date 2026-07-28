"""FastAPI application factory and main entrypoint for Hiron Core API."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from hiron import __version__
from hiron.common.exceptions import register_exception_handlers
from hiron.core.config import get_settings
from hiron.core.database import engine
from hiron.core.logging import setup_logging
from hiron.core.middleware import RequestTracingMiddleware
from hiron.health.router import health_router

logger = structlog.get_logger("hiron.api.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown events."""
    settings = get_settings()
    setup_logging(log_level=settings.log_level, environment=settings.environment)

    logger.info(
        "Application starting up",
        environment=settings.environment,
        version=__version__,
        api_prefix=settings.api_v1_prefix,
    )

    yield

    logger.info("Application shutting down: disposing database connection pool")
    await engine.dispose()


def create_app() -> FastAPI:
    """FastAPI application factory configuring middleware, exception handlers, and routers."""
    settings = get_settings()

    app = FastAPI(
        title="Hiron API",
        description="AI-Powered Hiring Intelligence Platform Core REST API",
        version=__version__,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        lifespan=lifespan,
    )

    # 1. CORS Middleware (§14)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Custom Request Tracing & Timing Middleware
    app.add_middleware(RequestTracingMiddleware)

    # 3. Global Exception Handlers (§14 & API Contract §8)
    register_exception_handlers(app)

    # 4. Include Routers
    app.include_router(health_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
