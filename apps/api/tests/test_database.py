"""Unit and structure tests for Async SQLAlchemy database engine and base model."""

import uuid
from datetime import datetime

import pytest

from hiron.common.models import Base, BaseModel
from hiron.core.database import check_database_connection, engine


def test_base_model_inheritance() -> None:
    """Verify BaseModel defines common audit columns (id, created_at, updated_at)."""
    assert issubclass(BaseModel, Base)
    assert hasattr(BaseModel, "id")
    assert hasattr(BaseModel, "created_at")
    assert hasattr(BaseModel, "updated_at")


@pytest.mark.asyncio
async def test_database_connection_probe_structure() -> None:
    """Verify check_database_connection returns a tuple of (bool, float)."""
    is_healthy, latency_ms = await check_database_connection()
    assert isinstance(is_healthy, bool)
    assert isinstance(latency_ms, float)
    assert latency_ms >= 0.0
