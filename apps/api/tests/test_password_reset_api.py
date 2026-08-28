"""API Integration tests for password reset endpoints."""

import uuid
from unittest.mock import AsyncMock, patch
import pytest
from collections.abc import Generator
from fastapi.testclient import TestClient
from fastapi import status

from hiron.main import app
from hiron.auth.router import get_auth_service
from hiron.auth.service import AuthService
from hiron.core.cache import app_cache


@pytest.fixture
def mock_auth_service() -> AsyncMock:
    return AsyncMock(spec=AuthService)


from unittest.mock import MagicMock


@pytest.fixture
def mock_redis() -> AsyncMock:
    mock = AsyncMock()
    pipe_mock = AsyncMock()
    pipe_mock.execute.return_value = [1]

    # pipeline() must return a mock synchronously, not as a coroutine
    pipeline_method_mock = MagicMock(return_value=pipe_mock)
    mock.pipeline = pipeline_method_mock
    return mock


@pytest.fixture
def client(
    mock_auth_service: AsyncMock, mock_redis: AsyncMock
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    with patch.object(app_cache, "_get_redis", return_value=mock_redis), TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_forgot_password_success(client: TestClient, mock_auth_service: AsyncMock) -> None:
    """Test forgot-password below rate limit succeeds and returns generic response."""
    mock_auth_service.generate_password_reset_token.return_value = "fake_token"

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "user@example.com", "tenant_id": str(uuid.uuid4())},
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "password reset link" in response.json()["data"]["message"]
    mock_auth_service.generate_password_reset_token.assert_called_once()


def test_forgot_password_nonexistent_user(client: TestClient, mock_auth_service: AsyncMock) -> None:
    """Test forgot-password for nonexistent user does not enumerate."""
    mock_auth_service.generate_password_reset_token.return_value = None

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@example.com", "tenant_id": str(uuid.uuid4())},
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "password reset link" in response.json()["data"]["message"]
    mock_auth_service.generate_password_reset_token.assert_called_once()


def test_forgot_password_rate_limit_exceeded(
    client: TestClient, mock_auth_service: AsyncMock, mock_redis: AsyncMock
) -> None:
    """Test forgot-password rejects request over limit."""
    mock_auth_service.generate_password_reset_token.return_value = "fake_token"

    # Mock redis to simulate exceeding the limit
    pipe_mock = AsyncMock()
    pipe_mock.execute.return_value = [6]  # over 5
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "spammer@example.com", "tenant_id": str(uuid.uuid4())},
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    # Should block before calling the service
    mock_auth_service.generate_password_reset_token.assert_not_called()
