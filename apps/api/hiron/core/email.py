"""Email delivery adapters and abstractions."""

import urllib.parse
from abc import ABC, abstractmethod

import httpx
import structlog

from hiron.core.config import get_settings

logger = structlog.get_logger("hiron.core.email")


class EmailDeliveryError(Exception):
    """Raised when an email adapter fails to deliver the message."""


class BaseEmailAdapter(ABC):
    """Abstract interface for transactional email delivery."""

    @abstractmethod
    async def send_password_reset_email(self, to_email: str, raw_token: str) -> None:
        """Send a password reset email.

        Args:
            to_email: The recipient's email address.
            raw_token: The raw cryptographic reset token.

        Raises:
            EmailDeliveryError: If the provider rejects the message or times out.
        """

    def _build_reset_url(self, raw_token: str) -> str:
        """Safely construct the reset URL using the configured APP_BASE_URL."""
        settings = get_settings()
        base = settings.app_base_url.rstrip("/")
        # Safely URL encode the token
        query = urllib.parse.urlencode({"token": raw_token})
        return f"{base}/reset-password?{query}"

    @abstractmethod
    async def send_invitation_email(
        self, to_email: str, raw_token: str, organization_name: str
    ) -> None:
        """Send an invitation email.

        Args:
            to_email: The recipient's email address.
            raw_token: The raw cryptographic invitation token.
            organization_name: The name of the organization inviting the user.

        Raises:
            EmailDeliveryError: If the provider rejects the message or times out.
        """

    def _build_invitation_url(self, raw_token: str) -> str:
        """Safely construct the invitation URL using the configured APP_BASE_URL."""
        settings = get_settings()
        base = settings.app_base_url.rstrip("/")
        query = urllib.parse.urlencode({"token": raw_token})
        return f"{base}/accept-invite?{query}"


class ConsoleEmailAdapter(BaseEmailAdapter):
    """Development-only adapter that safely logs the reset link to the console."""

    async def send_password_reset_email(self, to_email: str, raw_token: str) -> None:
        reset_url = self._build_reset_url(raw_token)
        # Log the complete reset URL clearly labelled for development
        # The raw token is implicitly in the URL, which is safe for local dev
        logger.info(
            "*** DEVELOPMENT EMAIL INTERCEPTED ***",
            to_email=to_email,
            subject="Reset your password",
            reset_url=reset_url,
        )

    async def send_invitation_email(
        self, to_email: str, raw_token: str, organization_name: str
    ) -> None:
        invitation_url = self._build_invitation_url(raw_token)
        logger.info(
            "*** DEVELOPMENT EMAIL INTERCEPTED ***",
            to_email=to_email,
            subject="You've been invited to join Hiron",
            organization_name=organization_name,
            invitation_url=invitation_url,
        )


class ResendEmailAdapter(BaseEmailAdapter):
    """Production adapter for the Resend transactional email API."""

    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.resend_api_key:
            raise ValueError("RESEND_API_KEY must be configured to use ResendEmailAdapter")

        self.api_url = "https://api.resend.com/emails"
        self.sender = f"{self.settings.email_from_name} <{self.settings.email_from_address}>"
        # 10 second timeout for external API
        self.timeout = httpx.Timeout(10.0)

    async def _send_resend_email(self, payload: dict, to_email: str) -> None:
        """Internal helper to dispatch email and handle network/provider errors uniformly."""
        headers = {
            "Authorization": f"Bearer {self.settings.resend_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)

                # Check for HTTP errors without logging the request payload (which contains the token)
                if not response.is_success:
                    # Do not log the raw response content if it risks echoing back the payload
                    # Resend error messages are typically static, but we use a generic error safely.
                    logger.error(
                        "Resend API rejected email",
                        status_code=response.status_code,
                        to_email=to_email,
                    )
                    raise EmailDeliveryError(
                        f"Provider rejected request with status {response.status_code}"
                    )

        except httpx.RequestError as e:
            logger.error("Network error communicating with Resend", to_email=to_email)
            raise EmailDeliveryError("Network communication failed") from e

    async def send_password_reset_email(self, to_email: str, raw_token: str) -> None:
        import html

        reset_url = self._build_reset_url(raw_token)
        safe_url = html.escape(reset_url)

        html_body = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Hiron Password Reset</h2>
            <p>We received a request to reset the password for your Hiron account.</p>
            <p>Click the link below to securely reset your password. This link will expire in 30 minutes.</p>
            <p style="margin: 30px 0;">
                <a href="{safe_url}" style="background-color: #0070f3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                    Reset Password
                </a>
            </p>
            <p style="color: #666; font-size: 14px;">If you did not request this password reset, you can safely ignore this email.</p>
        </div>
        """

        text_body = f"""Hiron Password Reset

We received a request to reset the password for your Hiron account.

Please copy and paste the following link into your browser to reset your password. This link will expire in 30 minutes.

{reset_url}

If you did not request this password reset, you can safely ignore this email.
"""

        payload = {
            "from": self.sender,
            "to": [to_email],
            "subject": "Reset your Hiron password",
            "html": html_body,
            "text": text_body,
        }
        await self._send_resend_email(payload, to_email)

    async def send_invitation_email(
        self, to_email: str, raw_token: str, organization_name: str
    ) -> None:
        import html

        invitation_url = self._build_invitation_url(raw_token)
        safe_url = html.escape(invitation_url)
        safe_org_name = html.escape(organization_name)

        html_body = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>You've been invited to join Hiron</h2>
            <p>You have been invited to join <strong>{safe_org_name}</strong> on Hiron.</p>
            <p>Click the button below to accept the invitation and set up your account. This invitation will expire in 7 days.</p>
            <p style="margin: 30px 0;">
                <a href="{safe_url}" style="background-color: #0070f3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                    Accept Invitation
                </a>
            </p>
            <p style="color: #666; font-size: 14px;">If you were not expecting this invitation, you can safely ignore this email or contact your administrator.</p>
        </div>
        """

        text_body = f"""You've been invited to join Hiron

You have been invited to join {organization_name} on Hiron.

Please copy and paste the following link into your browser to accept the invitation. This invitation will expire in 7 days.

{invitation_url}

If you were not expecting this invitation, you can safely ignore this email or contact your administrator.
"""

        payload = {
            "from": self.sender,
            "to": [to_email],
            "subject": "You've been invited to join Hiron",
            "html": html_body,
            "text": text_body,
        }
        await self._send_resend_email(payload, to_email)


def get_email_adapter() -> BaseEmailAdapter:
    """Factory to retrieve the configured email adapter."""
    settings = get_settings()
    if settings.email_provider == "resend":
        return ResendEmailAdapter()
    return ConsoleEmailAdapter()
