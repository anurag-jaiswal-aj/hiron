"""Tests for async password reset dispatch via QStash webhooks."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi import status

from hiron.main import app
from hiron.auth.schemas import ForgotPasswordWebhookPayload


@pytest.fixture
def mock_auth_service() -> AsyncMock:
    from hiron.auth.service import AuthService

    return AsyncMock(spec=AuthService)


@pytest.fixture
def mock_verify_qstash_signature():
    """Mock the QStash signature verification dependency."""
    with patch("hiron.webhooks.qstash_auth.QStashSignatureVerifier.verify") as mock_verify:
        yield mock_verify


def test_qstash_webhook_success_existing_user(
    mock_verify_qstash_signature, mock_auth_service
) -> None:
    """Test webhook succeeds for existing user, generating token and emailing."""
    tenant_id = uuid.uuid4()
    payload = ForgotPasswordWebhookPayload(email="user@example.com", tenant_id=tenant_id)

    mock_auth_service.generate_password_reset_token.return_value = "raw_token_value"

    with (
        patch("hiron.webhooks.router.AuthService", return_value=mock_auth_service),
        patch("hiron.webhooks.router.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        response = client.post(
            "/api/v1/webhooks/qstash/auth/forgot-password",
            json=payload.model_dump(mode="json"),
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify token generation was called with the tenant isolation intact
        mock_auth_service.generate_password_reset_token.assert_called_once_with(
            session=mock_auth_service.generate_password_reset_token.call_args.kwargs["session"],
            email="user@example.com",
            tenant_id=tenant_id,
        )

        # Verify email adapter was called with the raw token
        mock_adapter.send_password_reset_email.assert_called_once_with(
            to_email="user@example.com", raw_token="raw_token_value"
        )


def test_qstash_webhook_success_nonexistent_user(
    mock_verify_qstash_signature, mock_auth_service
) -> None:
    """Test webhook succeeds without sending email if user doesn't exist."""
    tenant_id = uuid.uuid4()
    payload = ForgotPasswordWebhookPayload(email="nobody@example.com", tenant_id=tenant_id)

    mock_auth_service.generate_password_reset_token.return_value = None

    with (
        patch("hiron.webhooks.router.AuthService", return_value=mock_auth_service),
        patch("hiron.webhooks.router.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_adapter = AsyncMock()
        mock_get_adapter.return_value = mock_adapter

        response = client.post(
            "/api/v1/webhooks/qstash/auth/forgot-password",
            json=payload.model_dump(mode="json"),
        )

        assert response.status_code == status.HTTP_200_OK

        mock_auth_service.generate_password_reset_token.assert_called_once()
        # Verify email adapter was NEVER called
        mock_adapter.send_password_reset_email.assert_not_called()


def test_qstash_webhook_email_failure_propagate(
    mock_verify_qstash_signature, mock_auth_service
) -> None:
    """Test webhook propagates EmailDeliveryError as 500 so QStash retries."""
    tenant_id = uuid.uuid4()
    payload = ForgotPasswordWebhookPayload(email="user@example.com", tenant_id=tenant_id)

    mock_auth_service.generate_password_reset_token.return_value = "raw_token_value"

    with (
        patch("hiron.webhooks.router.AuthService", return_value=mock_auth_service),
        patch("hiron.webhooks.router.get_email_adapter") as mock_get_adapter,
        TestClient(app) as client,
    ):
        mock_adapter = AsyncMock()
        from hiron.core.email import EmailDeliveryError

        mock_adapter.send_password_reset_email.side_effect = EmailDeliveryError("Failed")
        mock_get_adapter.return_value = mock_adapter

        response = client.post(
            "/api/v1/webhooks/qstash/auth/forgot-password",
            json=payload.model_dump(mode="json"),
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        # Depending on exception handler, the message could be in detail or error.message
        resp_json = response.json()
        assert "Email delivery failed" in str(resp_json)
