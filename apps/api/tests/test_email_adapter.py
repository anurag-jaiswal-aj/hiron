"""Tests for email delivery adapters and URL builders."""

import pytest
from unittest.mock import AsyncMock, patch

import httpx

from hiron.core.config import get_settings
from hiron.core.email import (
    ConsoleEmailAdapter,
    ResendEmailAdapter,
    EmailDeliveryError,
    get_email_adapter,
)


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock application settings to safe values."""
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: get_settings())


def test_console_email_adapter_url_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the Console adapter builds the reset URL correctly with URL encoding."""
    # Override settings specifically for the test
    settings = get_settings()
    settings.app_base_url = "https://hiron.app/"
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    adapter = ConsoleEmailAdapter()

    # Token with special characters requiring url-encoding
    raw_token = "some/raw+token=value"
    url = adapter._build_reset_url(raw_token)

    assert url == "https://hiron.app/reset-password?token=some%2Fraw%2Btoken%3Dvalue"


def test_console_email_adapter_invitation_url_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the Console adapter builds the invitation URL correctly with URL encoding."""
    settings = get_settings()
    settings.app_base_url = "https://hiron.app/"
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    adapter = ConsoleEmailAdapter()

    raw_token = "invite/raw+token=value"
    url = adapter._build_invitation_url(raw_token)

    assert url == "https://hiron.app/accept-invite?token=invite%2Fraw%2Btoken%3Dvalue"


@pytest.mark.asyncio
async def test_console_email_adapter_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the Console adapter logs without hitting network."""
    adapter = ConsoleEmailAdapter()

    with patch("hiron.core.email.logger.info") as mock_logger:
        await adapter.send_password_reset_email("user@example.com", "fake_token")

        mock_logger.assert_called_once()
        kwargs = mock_logger.call_args.kwargs
        assert kwargs["to_email"] == "user@example.com"
        assert "token=fake_token" in kwargs["reset_url"]


@pytest.mark.asyncio
async def test_console_email_adapter_invitation_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the Console adapter logs invitation email without hitting network."""
    adapter = ConsoleEmailAdapter()

    with patch("hiron.core.email.logger.info") as mock_logger:
        await adapter.send_invitation_email("invite@example.com", "invite_token", "Acme Corp")

        mock_logger.assert_called_once()
        kwargs = mock_logger.call_args.kwargs
        assert kwargs["to_email"] == "invite@example.com"
        assert kwargs["organization_name"] == "Acme Corp"
        assert "token=invite_token" in kwargs["invitation_url"]


@pytest.mark.asyncio
async def test_resend_email_adapter_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Resend adapter successfully constructs and sends payload."""
    settings = get_settings()
    settings.resend_api_key = "test_resend_key"
    settings.email_from_address = "noreply@hiron.app"
    settings.email_from_name = "Hiron Support"
    settings.app_base_url = "https://hiron.app"
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    adapter = ResendEmailAdapter()

    mock_post = AsyncMock()
    mock_post.return_value.is_success = True

    with patch("httpx.AsyncClient.post", new=mock_post):
        await adapter.send_password_reset_email("user@example.com", "fake+token")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args

        assert args[0] == "https://api.resend.com/emails"
        assert kwargs["headers"]["Authorization"] == "Bearer test_resend_key"
        assert kwargs["json"]["to"] == ["user@example.com"]
        assert kwargs["json"]["from"] == "Hiron Support <noreply@hiron.app>"
        assert kwargs["json"]["subject"] == "Reset your Hiron password"
        assert "https://hiron.app/reset-password?token=fake%2Btoken" in kwargs["json"]["html"]
        assert "https://hiron.app/reset-password?token=fake%2Btoken" in kwargs["json"]["text"]
        assert "expire in 30 minutes" in kwargs["json"]["text"]


@pytest.mark.asyncio
async def test_resend_email_adapter_invitation_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Resend adapter successfully constructs and sends invitation payload."""
    settings = get_settings()
    settings.resend_api_key = "test_resend_key"
    settings.email_from_address = "noreply@hiron.app"
    settings.email_from_name = "Hiron Support"
    settings.app_base_url = "https://hiron.app"
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    adapter = ResendEmailAdapter()

    mock_post = AsyncMock()
    mock_post.return_value.is_success = True

    with patch("httpx.AsyncClient.post", new=mock_post):
        await adapter.send_invitation_email("invite@example.com", "invite+token", "Acme <Corp>")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args

        assert args[0] == "https://api.resend.com/emails"
        assert kwargs["headers"]["Authorization"] == "Bearer test_resend_key"
        assert kwargs["json"]["to"] == ["invite@example.com"]
        assert kwargs["json"]["from"] == "Hiron Support <noreply@hiron.app>"
        assert kwargs["json"]["subject"] == "You've been invited to join Hiron"

        html_body = kwargs["json"]["html"]
        assert "https://hiron.app/accept-invite?token=invite%2Btoken" in html_body
        # Check HTML escaping
        assert "Acme &lt;Corp&gt;" in html_body
        assert "expire in 7 days" in html_body

        text_body = kwargs["json"]["text"]
        assert "https://hiron.app/accept-invite?token=invite%2Btoken" in text_body
        assert "Acme <Corp>" in text_body
        assert "expire in 7 days" in text_body


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 401, 403, 429, 500, 502, 503])
async def test_resend_email_adapter_http_error(
    monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    """Test Resend adapter handles non-2xx HTTP responses safely."""
    settings = get_settings()
    settings.resend_api_key = "test_resend_key"
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    adapter = ResendEmailAdapter()

    mock_post = AsyncMock()
    mock_post.return_value.is_success = False
    mock_post.return_value.status_code = status_code

    with (
        patch("httpx.AsyncClient.post", new=mock_post),
        pytest.raises(EmailDeliveryError, match=f"status {status_code}"),
    ):
        await adapter.send_password_reset_email("user@example.com", "fake_token")


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 401, 403, 429, 500, 502, 503])
async def test_resend_email_adapter_invitation_http_error(
    monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    """Test Resend adapter handles non-2xx HTTP responses safely for invitations."""
    settings = get_settings()
    settings.resend_api_key = "test_resend_key"
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    adapter = ResendEmailAdapter()

    mock_post = AsyncMock()
    mock_post.return_value.is_success = False
    mock_post.return_value.status_code = status_code

    with (
        patch("httpx.AsyncClient.post", new=mock_post),
        pytest.raises(EmailDeliveryError, match=f"status {status_code}"),
    ):
        await adapter.send_invitation_email("invite@example.com", "fake_token", "Org")


@pytest.mark.asyncio
async def test_resend_email_adapter_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Resend adapter translates network errors cleanly."""
    settings = get_settings()
    settings.resend_api_key = "test_resend_key"
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    adapter = ResendEmailAdapter()

    mock_post = AsyncMock(side_effect=httpx.RequestError("Network error"))

    with (
        patch("httpx.AsyncClient.post", new=mock_post),
        pytest.raises(EmailDeliveryError, match="Network communication failed"),
    ):
        await adapter.send_password_reset_email("user@example.com", "fake_token")


@pytest.mark.asyncio
async def test_resend_email_adapter_invitation_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Resend adapter translates network errors cleanly for invitations."""
    settings = get_settings()
    settings.resend_api_key = "test_resend_key"
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    adapter = ResendEmailAdapter()

    mock_post = AsyncMock(side_effect=httpx.RequestError("Network error"))

    with (
        patch("httpx.AsyncClient.post", new=mock_post),
        pytest.raises(EmailDeliveryError, match="Network communication failed"),
    ):
        await adapter.send_invitation_email("invite@example.com", "fake_token", "Org")


def test_missing_resend_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test missing production configuration fails immediately."""
    settings = get_settings()
    settings.email_provider = "resend"
    settings.resend_api_key = None
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    with pytest.raises(ValueError, match="RESEND_API_KEY must be configured"):
        get_email_adapter()


@pytest.mark.asyncio
async def test_resend_email_adapter_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Resend adapter translates timeouts cleanly."""
    settings = get_settings()
    settings.resend_api_key = "test_resend_key"
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    adapter = ResendEmailAdapter()

    mock_post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    with (
        patch("httpx.AsyncClient.post", new=mock_post),
        pytest.raises(EmailDeliveryError, match="Network communication failed"),
    ):
        await adapter.send_password_reset_email("user@example.com", "fake_token")


@pytest.mark.asyncio
async def test_resend_email_adapter_invitation_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Resend adapter translates timeouts cleanly for invitations."""
    settings = get_settings()
    settings.resend_api_key = "test_resend_key"
    monkeypatch.setattr("hiron.core.email.get_settings", lambda: settings)

    adapter = ResendEmailAdapter()

    mock_post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    with (
        patch("httpx.AsyncClient.post", new=mock_post),
        pytest.raises(EmailDeliveryError, match="Network communication failed"),
    ):
        await adapter.send_invitation_email("invite@example.com", "fake_token", "Org")


def test_production_app_base_url_validation() -> None:
    """Test production settings enforce a non-localhost APP_BASE_URL."""
    from hiron.core.config import Settings

    with pytest.raises(ValueError, match="APP_BASE_URL must be a real domain in production"):
        Settings(
            environment="production",
            worker_url="https://worker.hiron.app",
            gemini_api_key="key",
            email_provider="resend",
            resend_api_key="key",
            app_base_url="http://localhost:3000",
        )


def test_localhost_app_base_url_allowed_in_dev() -> None:
    """Test localhost APP_BASE_URL is allowed in development."""
    from hiron.core.config import Settings

    settings = Settings(environment="development", app_base_url="http://localhost:3000")
    assert settings.app_base_url == "http://localhost:3000"
