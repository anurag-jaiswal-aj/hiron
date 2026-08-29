"""Tests for user invitation API endpoints (Phase 10.5.4)."""

import uuid
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from collections.abc import Generator
from fastapi.testclient import TestClient
from fastapi import status
from datetime import UTC, datetime
import secrets

from hiron.main import app
from hiron.users.router import get_user_service
from hiron.users.service import UserService
from hiron.users.models import User
from hiron.auth.dependencies import get_current_user, require_role


@pytest.fixture
def mock_user_service() -> AsyncMock:
    return AsyncMock(spec=UserService)


@pytest.fixture
def mock_redis() -> AsyncMock:
    mock = AsyncMock()
    pipe_mock = AsyncMock()
    pipe_mock.execute.return_value = [1]

    pipeline_method_mock = MagicMock(return_value=pipe_mock)
    mock.pipeline = pipeline_method_mock
    return mock


@pytest.fixture
def client(
    mock_user_service: AsyncMock, mock_redis: AsyncMock
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    from hiron.core.config import get_settings

    settings = get_settings()
    original_url = settings.qstash_webhook_url
    settings.qstash_webhook_url = "http://localhost:8000"

    with (
        patch("hiron.core.cache.CacheManager._get_redis", return_value=mock_redis),
        TestClient(app) as client,
    ):
        yield client

    settings.qstash_webhook_url = original_url
    app.dependency_overrides.clear()


def test_invite_user_success(client: TestClient, mock_user_service: AsyncMock) -> None:
    """Test successful user invitation by org_admin."""
    tenant_id = uuid.uuid4()
    admin_user = User(id=uuid.uuid4(), tenant_id=tenant_id, role="org_admin")
    app.dependency_overrides[get_current_user] = lambda: admin_user

    mock_created_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="newuser@example.com",
        full_name="New User",
        role="recruiter",
        is_active=True,
        is_email_verified=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_user_service.create_user.return_value = mock_created_user

    with patch("hiron.users.router.qstash_publisher.publish") as mock_publish:
        payload = {"email": "newuser@example.com", "full_name": "New User", "role": "recruiter"}
        response = client.post("/api/v1/users/invite", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["email"] == "newuser@example.com"

        mock_publish.assert_called_once()
        publish_kwargs = mock_publish.call_args.kwargs
        assert publish_kwargs["payload"]["email"] == "newuser@example.com"
        assert publish_kwargs["payload"]["user_id"] == str(mock_created_user.id)
        assert publish_kwargs["payload"]["tenant_id"] == str(tenant_id)
        assert "password" not in publish_kwargs["payload"]
        assert "token" not in publish_kwargs["payload"]


def test_invite_user_not_org_admin(client: TestClient) -> None:
    """Test that a non-admin cannot invite users."""
    tenant_id = uuid.uuid4()
    recruiter_user = User(id=uuid.uuid4(), tenant_id=tenant_id, role="recruiter")

    # We do not override require_role("org_admin"), so it will run normally and fail,
    # but since this is unit test on the router we need to mock get_current_user
    app.dependency_overrides[get_current_user] = lambda: recruiter_user

    payload = {"email": "newuser@example.com", "full_name": "New User", "role": "recruiter"}
    response = client.post("/api/v1/users/invite", json=payload)

    # In fastapi, dependency failure returns 403 or 401. The actual implementation uses HironException (403 usually)
    assert response.status_code in [401, 403]


def test_resend_invitation_success(client: TestClient, mock_user_service: AsyncMock) -> None:
    """Test successful resend of invitation."""
    tenant_id = uuid.uuid4()
    admin_user = User(id=uuid.uuid4(), tenant_id=tenant_id, role="org_admin")
    app.dependency_overrides[get_current_user] = lambda: admin_user

    mock_target_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="pending@example.com",
        is_active=True,
        is_email_verified=False,
    )
    mock_user_service.get_user_by_id.return_value = mock_target_user

    with patch("hiron.users.router.qstash_publisher.publish") as mock_publish:
        response = client.post(f"/api/v1/users/{mock_target_user.id}/invite/resend")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["status"] == "invitation_queued"

        mock_publish.assert_called_once()
        publish_kwargs = mock_publish.call_args.kwargs
        assert publish_kwargs["payload"]["email"] == "pending@example.com"
        assert publish_kwargs["payload"]["user_id"] == str(mock_target_user.id)
        assert publish_kwargs["payload"]["tenant_id"] == str(tenant_id)


def test_resend_invitation_already_verified(
    client: TestClient, mock_user_service: AsyncMock
) -> None:
    """Test resend blocked if user already verified."""
    tenant_id = uuid.uuid4()
    admin_user = User(id=uuid.uuid4(), tenant_id=tenant_id, role="org_admin")
    app.dependency_overrides[get_current_user] = lambda: admin_user

    mock_target_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        is_active=True,
        is_email_verified=True,
    )
    mock_user_service.get_user_by_id.return_value = mock_target_user

    response = client.post(f"/api/v1/users/{mock_target_user.id}/invite/resend")
    assert response.status_code == status.HTTP_409_CONFLICT


def test_resend_invitation_deactivated(client: TestClient, mock_user_service: AsyncMock) -> None:
    """Test resend blocked if user inactive."""
    tenant_id = uuid.uuid4()
    admin_user = User(id=uuid.uuid4(), tenant_id=tenant_id, role="org_admin")
    app.dependency_overrides[get_current_user] = lambda: admin_user

    mock_target_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        is_active=False,
        is_email_verified=False,
    )
    mock_user_service.get_user_by_id.return_value = mock_target_user

    response = client.post(f"/api/v1/users/{mock_target_user.id}/invite/resend")
    assert response.status_code == status.HTTP_409_CONFLICT


def test_accept_invitation_success(client: TestClient, mock_user_service: AsyncMock) -> None:
    """Test successful token acceptance."""
    mock_user_service.accept_invitation.return_value = None

    payload = {"token": secrets.token_urlsafe(32), "password": "newSecurePassword123!"}

    response = client.post("/api/v1/users/invite/accept", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["status"] == "invitation_accepted"
    mock_user_service.accept_invitation.assert_called_once()


def test_accept_invitation_invalid_token(client: TestClient, mock_user_service: AsyncMock) -> None:
    """Test acceptance failure when token is invalid or expired."""
    from hiron.users.service import InvalidInvitationTokenError

    mock_user_service.accept_invitation.side_effect = InvalidInvitationTokenError()

    payload = {"token": secrets.token_urlsafe(32), "password": "newSecurePassword123!"}

    response = client.post("/api/v1/users/invite/accept", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_accept_invitation_rate_limit(client: TestClient, mock_redis: AsyncMock) -> None:
    """Test brute-force protection hits rate limits."""
    # Simulate rate limit exceeded
    mock_redis.pipeline.return_value.execute.return_value = [6]

    payload = {"token": secrets.token_urlsafe(32), "password": "newSecurePassword123!"}

    response = client.post("/api/v1/users/invite/accept", json=payload)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
