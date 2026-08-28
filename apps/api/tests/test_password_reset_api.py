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
    from hiron.core.config import get_settings

    settings = get_settings()
    original_url = settings.qstash_webhook_url
    settings.qstash_webhook_url = "http://localhost:8000"

    with patch("hiron.core.cache.CacheManager._get_redis", return_value=mock_redis), TestClient(app) as client:
        yield client

    settings.qstash_webhook_url = original_url
    app.dependency_overrides.clear()


def test_forgot_password_success(client: TestClient) -> None:
    """Test forgot-password below rate limit succeeds and publishes to QStash."""

    with patch(
        "hiron.auth.router.qstash_publisher.publish", new_callable=AsyncMock
    ) as mock_publish:
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "user@example.com", "tenant_id": str(uuid.uuid4())},
            headers={"X-Forwarded-For": "1.1.1.1"},
        )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "password reset link" in response.json()["data"]["message"]
    mock_publish.assert_called_once()
    payload = mock_publish.call_args.kwargs["payload"]
    assert payload["email"] == "user@example.com"
    assert "tenant_id" in payload
    assert "token" not in payload


def test_forgot_password_publish_failure(client: TestClient) -> None:
    """Test forgot-password handles publish failures securely."""
    with patch(
        "hiron.auth.router.qstash_publisher.publish", new_callable=AsyncMock
    ) as mock_publish:
        mock_publish.side_effect = Exception("QStash is down")

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody@example.com", "tenant_id": str(uuid.uuid4())},
            headers={"X-Forwarded-For": "1.1.1.2"},
        )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    mock_publish.assert_called_once()


def test_forgot_password_rate_limit_exceeded(client: TestClient, mock_redis: AsyncMock) -> None:
    """Test forgot-password rejects request over limit."""

    # Mock redis to simulate exceeding the limit
    pipe_mock = AsyncMock()
    pipe_mock.execute.return_value = [6]  # over 5
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)

    with patch(
        "hiron.auth.router.qstash_publisher.publish", new_callable=AsyncMock
    ) as mock_publish:
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "spammer@example.com", "tenant_id": str(uuid.uuid4())},
            headers={"X-Forwarded-For": "1.1.1.3"},
        )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    mock_publish.assert_not_called()
