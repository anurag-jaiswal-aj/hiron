"""FastAPI application entry point for Hiron AI Engine microservice."""

from typing import Any

from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI(
    title="Hiron AI Service",
    description="Standalone AI Candidate-Job Scoring & Resume Parsing Microservice",
    version="0.1.0",
)


class HealthStatus(BaseModel):
    """Health check response schema."""

    status: str = "healthy"
    service: str = "ai_engine"


@app.get("/health", status_code=status.HTTP_200_OK, response_model=HealthStatus)
async def get_health() -> dict[str, Any]:
    """Health check endpoint for container orchestrator readiness probes."""
    return {"status": "healthy", "service": "ai_engine"}
