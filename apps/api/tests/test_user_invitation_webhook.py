"""Tests for async user invitation dispatch via QStash webhooks."""

import uuid
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.exc import IntegrityError

from hiron.main import app
from hiron.users.schemas import UserInvitationWebhookPayload
from hiron.tenants.models import Tenant
from hiron.users.models import User, UserInvitationToken
from hiron.core.email import EmailDeliveryError


@pytest.fixture
def mock_verify_qstash_signature() -> Generator[AsyncMock, None, None]:
    """Mock the QStash signature verification dependency."""
    with patch("hiron.webhooks.qstash_auth.QStashSignatureVerifier.verify") as mock_verify:
        yield mock_verify


@pytest.fixture
def base_payload() -> dict[str, Any]:
    return {
        "user_id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "email": "invite@example.com",
    }


def test_qstash_invitation_webhook_success(
    mock_verify_qstash_signature: Any, base_payload: dict[str, Any]
) -> None:
    """Test webhook succeeds for valid user, generates token, and sends email."""
    mock_tenant = Tenant(id=uuid.UUID(base_payload["tenant_id"]), name="Acme Corp")
    mock_user = User(
        id=uuid.UUID(base_payload["user_id"]),
        tenant_id=uuid.UUID(base_payload["tenant_id"]),
        email="invite@example.com",
        is_active=True,
        is_email_verified=False,
    )

    with (
        patch(
            "hiron.tenants.repository.TenantRepository.get_by_id", new_callable=AsyncMock
        ) as mock_get_tenant,
        patch(
            "hiron.users.repository.UserRepository.get_by_id_and_tenant", new_callable=AsyncMock
        ) as mock_get_user,
        patch(
            "hiron.users.repository.UserInvitationTokenRepository.revoke_pending_for_user",
            new_callable=AsyncMock,
        ) as mock_revoke,
        patch(
            "hiron.users.repository.UserInvitationTokenRepository.create", new_callable=AsyncMock
        ) as mock_create,
        patch("hiron.core.email.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_get_tenant.return_value = mock_tenant
        mock_get_user.return_value = mock_user

        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        response = client.post(
            "/api/v1/webhooks/qstash/users/invite",
            json=base_payload,
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify old tokens revoked
        mock_revoke.assert_called_once_with(mock_revoke.call_args.args[0], uuid.UUID(base_payload["user_id"]))

        # Verify new token created
        mock_create.assert_called_once()
        token_arg = mock_create.call_args.args[1]
        assert isinstance(token_arg, UserInvitationToken)
        assert str(token_arg.user_id) == base_payload["user_id"]
        assert token_arg.token_hash is not None
        # 7 days expiration should be set
        assert token_arg.expires_at is not None

        # Verify email adapter was called with the raw token
        mock_adapter.send_invitation_email.assert_called_once()
        kwargs = mock_adapter.send_invitation_email.call_args.kwargs
        assert kwargs["to_email"] == "invite@example.com"
        assert kwargs["organization_name"] == "Acme Corp"
        # The raw token must be string and urlsafe base64 (approx 43 chars for 32 bytes)
        assert isinstance(kwargs["raw_token"], str)
        assert len(kwargs["raw_token"]) > 32


def test_qstash_invitation_webhook_tenant_not_found(
    mock_verify_qstash_signature: Any, base_payload: dict[str, Any]
) -> None:
    """Test webhook ignores request if tenant does not exist."""
    with (
        patch(
            "hiron.tenants.repository.TenantRepository.get_by_id", new_callable=AsyncMock
        ) as mock_get_tenant,
        patch("hiron.core.email.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_get_tenant.return_value = None
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/api/v1/webhooks/qstash/users/invite", json=base_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ignored", "reason": "Tenant not found"}
        mock_adapter.send_invitation_email.assert_not_called()


def test_qstash_invitation_webhook_user_not_found(
    mock_verify_qstash_signature: Any, base_payload: dict[str, Any]
) -> None:
    """Test webhook ignores request if user does not exist."""
    mock_tenant = Tenant(id=uuid.UUID(base_payload["tenant_id"]), name="Acme")
    with (
        patch(
            "hiron.tenants.repository.TenantRepository.get_by_id", new_callable=AsyncMock
        ) as mock_get_tenant,
        patch(
            "hiron.users.repository.UserRepository.get_by_id_and_tenant", new_callable=AsyncMock
        ) as mock_get_user,
        patch("hiron.core.email.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_get_tenant.return_value = mock_tenant
        mock_get_user.return_value = None
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/api/v1/webhooks/qstash/users/invite", json=base_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ignored", "reason": "User not found"}
        mock_adapter.send_invitation_email.assert_not_called()


def test_qstash_invitation_webhook_email_mismatch(
    mock_verify_qstash_signature: Any, base_payload: dict[str, Any]
) -> None:
    """Test webhook ignores request if payload email does not match user email."""
    mock_tenant = Tenant(id=uuid.UUID(base_payload["tenant_id"]), name="Acme")
    mock_user = User(
        id=uuid.UUID(base_payload["user_id"]),
        tenant_id=uuid.UUID(base_payload["tenant_id"]),
        email="different@example.com",
    )
    with (
        patch(
            "hiron.tenants.repository.TenantRepository.get_by_id", new_callable=AsyncMock
        ) as mock_get_tenant,
        patch(
            "hiron.users.repository.UserRepository.get_by_id_and_tenant", new_callable=AsyncMock
        ) as mock_get_user,
        patch("hiron.core.email.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_get_tenant.return_value = mock_tenant
        mock_get_user.return_value = mock_user
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/api/v1/webhooks/qstash/users/invite", json=base_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ignored", "reason": "Email mismatch"}
        mock_adapter.send_invitation_email.assert_not_called()


def test_qstash_invitation_webhook_user_inactive(
    mock_verify_qstash_signature: Any, base_payload: dict[str, Any]
) -> None:
    """Test webhook ignores request if user is inactive."""
    mock_tenant = Tenant(id=uuid.UUID(base_payload["tenant_id"]), name="Acme")
    mock_user = User(
        id=uuid.UUID(base_payload["user_id"]),
        tenant_id=uuid.UUID(base_payload["tenant_id"]),
        email=base_payload["email"],
        is_active=False,
    )
    with (
        patch(
            "hiron.tenants.repository.TenantRepository.get_by_id", new_callable=AsyncMock
        ) as mock_get_tenant,
        patch(
            "hiron.users.repository.UserRepository.get_by_id_and_tenant", new_callable=AsyncMock
        ) as mock_get_user,
        patch("hiron.core.email.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_get_tenant.return_value = mock_tenant
        mock_get_user.return_value = mock_user
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/api/v1/webhooks/qstash/users/invite", json=base_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ignored", "reason": "User inactive"}
        mock_adapter.send_invitation_email.assert_not_called()


def test_qstash_invitation_webhook_user_already_verified(
    mock_verify_qstash_signature: Any, base_payload: dict[str, Any]
) -> None:
    """Test webhook ignores request if user is already verified."""
    mock_tenant = Tenant(id=uuid.UUID(base_payload["tenant_id"]), name="Acme")
    mock_user = User(
        id=uuid.UUID(base_payload["user_id"]),
        tenant_id=uuid.UUID(base_payload["tenant_id"]),
        email=base_payload["email"],
        is_active=True,
        is_email_verified=True,
    )
    with (
        patch(
            "hiron.tenants.repository.TenantRepository.get_by_id", new_callable=AsyncMock
        ) as mock_get_tenant,
        patch(
            "hiron.users.repository.UserRepository.get_by_id_and_tenant", new_callable=AsyncMock
        ) as mock_get_user,
        patch("hiron.core.email.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_get_tenant.return_value = mock_tenant
        mock_get_user.return_value = mock_user
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/api/v1/webhooks/qstash/users/invite", json=base_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ignored", "reason": "User already verified"}
        mock_adapter.send_invitation_email.assert_not_called()


def test_qstash_invitation_webhook_email_failure_propagate(
    mock_verify_qstash_signature: Any, base_payload: dict[str, Any]
) -> None:
    """Test webhook propagates EmailDeliveryError as 500 so QStash retries."""
    mock_tenant = Tenant(id=uuid.UUID(base_payload["tenant_id"]), name="Acme Corp")
    mock_user = User(
        id=uuid.UUID(base_payload["user_id"]),
        tenant_id=uuid.UUID(base_payload["tenant_id"]),
        email=base_payload["email"],
        is_active=True,
        is_email_verified=False,
    )

    with (
        patch(
            "hiron.tenants.repository.TenantRepository.get_by_id", new_callable=AsyncMock
        ) as mock_get_tenant,
        patch(
            "hiron.users.repository.UserRepository.get_by_id_and_tenant", new_callable=AsyncMock
        ) as mock_get_user,
        patch(
            "hiron.users.repository.UserInvitationTokenRepository.revoke_pending_for_user",
            new_callable=AsyncMock,
        ),
        patch(
            "hiron.users.repository.UserInvitationTokenRepository.create", new_callable=AsyncMock
        ),
        patch("hiron.core.email.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_get_tenant.return_value = mock_tenant
        mock_get_user.return_value = mock_user

        mock_adapter = AsyncMock()
        mock_adapter.send_invitation_email.side_effect = EmailDeliveryError("Failed")
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/api/v1/webhooks/qstash/users/invite", json=base_payload)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        resp_json = response.json()
        assert "Email delivery failed" in str(resp_json)


def test_qstash_invitation_webhook_malformed_payload(mock_verify_qstash_signature: Any) -> None:
    """Test webhook safely rejects malformed payloads."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/webhooks/qstash/users/invite", json={"user_id": "not-a-uuid"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        resp_json = response.json()
        assert "Malformed payload" in str(resp_json)


def test_qstash_invitation_webhook_db_failure(
    mock_verify_qstash_signature: Any, base_payload: dict[str, Any]
) -> None:
    """Test webhook handles DB creation failures."""
    mock_tenant = Tenant(id=uuid.UUID(base_payload["tenant_id"]), name="Acme Corp")
    mock_user = User(
        id=uuid.UUID(base_payload["user_id"]),
        tenant_id=uuid.UUID(base_payload["tenant_id"]),
        email=base_payload["email"],
        is_active=True,
        is_email_verified=False,
    )

    with (
        patch(
            "hiron.tenants.repository.TenantRepository.get_by_id", new_callable=AsyncMock
        ) as mock_get_tenant,
        patch(
            "hiron.users.repository.UserRepository.get_by_id_and_tenant", new_callable=AsyncMock
        ) as mock_get_user,
        patch(
            "hiron.users.repository.UserInvitationTokenRepository.revoke_pending_for_user",
            new_callable=AsyncMock,
        ),
        patch(
            "hiron.users.repository.UserInvitationTokenRepository.create", new_callable=AsyncMock
        ) as mock_create,
        patch("hiron.core.email.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_get_tenant.return_value = mock_tenant
        mock_get_user.return_value = mock_user

        mock_create.side_effect = IntegrityError("fake stmt", "fake params", Exception("fake orig"))

        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        response = client.post("/api/v1/webhooks/qstash/users/invite", json=base_payload)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        resp_json = response.json()
        assert "Database failure" in str(resp_json)

        # Ensure email is NEVER sent if token persistence fails
        mock_adapter.send_invitation_email.assert_not_called()
