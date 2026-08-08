"""FastAPI application entry point, middleware registration, and core router initialization."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hiron.ai_usage.router import router as ai_usage_router
from hiron.audit.router import router as audit_router
from hiron.auth.router import router as auth_router
from hiron.candidates.router import jobs_candidate_router, router as candidates_router
from hiron.common.exceptions import register_exception_handlers
from hiron.core.config import get_settings
from hiron.core.logging import configure_logging
from hiron.core.middleware import ProcessTimeAndRequestIdMiddleware
from hiron.dashboard.router import router as dashboard_router
from hiron.embeddings.router import router as embeddings_router
from hiron.health.router import router as health_router
from hiron.jobs.router import router as jobs_router
from hiron.maintenance.router import router as maintenance_router
from hiron.notes.router import router as notes_router
from hiron.performance.router import router as performance_router
from hiron.pipeline.router import router as pipeline_router
from hiron.resumes.router import router as resumes_router
from hiron.scores.router import router as scores_router
from hiron.search.router import router as search_router
from hiron.security.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from hiron.security.router import router as security_router
from hiron.tags.router import router as tags_router
from hiron.tenants.router import router as tenants_router
from hiron.users.router import router as users_router

# Initialize structured logging
settings = get_settings()
configure_logging(log_level=settings.log_level, environment=settings.environment)
logger = structlog.get_logger("hiron.api.main")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifespan events."""
    logger.info("Application starting up", environment=settings.environment, port=settings.port)
    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Construct and configure the main FastAPI application instance."""
    app_settings = get_settings()
    app = FastAPI(
        title="Hiron API",
        description="Multi-Tenant AI Recruitment Platform Backend API",
        version="0.1.0",
        docs_url="/docs" if app_settings.environment != "production" else None,
        redoc_url="/redoc" if app_settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # 1. Custom Tracing & Request ID Middleware
    app.add_middleware(ProcessTimeAndRequestIdMiddleware)

    # 2. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Custom Exception Handlers
    register_exception_handlers(app)

    # 4. Security & Router Registration
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)

    # Register API Routers
    app.include_router(health_router, prefix="/api/v1/health", tags=["Health"])
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(tenants_router, prefix="/api/v1/tenants", tags=["Tenants"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["Jobs"])
    app.include_router(candidates_router, prefix="/api/v1/candidates", tags=["Candidates"])
    app.include_router(jobs_candidate_router, prefix="/api/v1/jobs", tags=["Jobs/Candidates"])
    app.include_router(resumes_router, prefix="/api/v1/resumes", tags=["Resumes"])
    app.include_router(embeddings_router, prefix="/api/v1", tags=["Embeddings"])
    app.include_router(scores_router, prefix="/api/v1", tags=["AI Scoring"])
    app.include_router(search_router, prefix="/api/v1", tags=["Semantic Search"])
    app.include_router(pipeline_router, prefix="/api/v1", tags=["Pipeline"])
    app.include_router(notes_router, prefix="/api/v1", tags=["Candidate Notes"])
    app.include_router(tags_router, prefix="/api/v1", tags=["Candidate Tags"])
    app.include_router(dashboard_router, prefix="/api/v1", tags=["Dashboard & Analytics"])
    app.include_router(audit_router, prefix="/api/v1", tags=["Audit Logs"])
    app.include_router(ai_usage_router, prefix="/api/v1", tags=["AI Usage Monitoring"])
    app.include_router(performance_router, prefix="/api/v1", tags=["Performance & Benchmarking"])
    app.include_router(security_router, prefix="/api/v1", tags=["Security & Hardening"])
    app.include_router(maintenance_router, prefix="/api/v1", tags=["Maintenance"])

    from hiron.tasks.router import router as tasks_router
    app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["Tasks"])

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "hiron.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
    )
