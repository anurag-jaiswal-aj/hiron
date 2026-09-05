import pytest
from unittest.mock import patch, MagicMock

import sentry_sdk
from hiron.main import sentry_before_send
from hiron.security.middleware import TenantIsolationMiddleware
from fastapi import Request
from starlette.datastructures import Headers


def test_sentry_before_send_filters_pii():
    """Verify that the before_send hook strips PII from Sentry events."""
    event = {
        "request": {
            "headers": {
                "authorization": "Bearer secret_token",
                "cookie": "session_id=123",
                "user-agent": "test-agent",
            },
            "data": '{"resume_text": "John Doe"}',
        }
    }

    filtered_event = sentry_before_send(event, {})

    assert filtered_event["request"]["headers"]["authorization"] == "[Filtered]"
    assert filtered_event["request"]["headers"]["cookie"] == "[Filtered]"
    assert filtered_event["request"]["headers"]["user-agent"] == "test-agent"
    assert filtered_event["request"]["data"] == "[Filtered payload]"


def test_sentry_before_send_no_request():
    """Verify before_send handles events without request data."""
    event = {"message": "Test error"}
    filtered_event = sentry_before_send(event, {})
    assert filtered_event == event


@pytest.mark.asyncio
async def test_tenant_context_tag():
    """Verify tenant isolation sets Sentry tag, not user."""
    middleware = TenantIsolationMiddleware(MagicMock())

    request = MagicMock(spec=Request)
    # Simulate headers missing or no token to verify it doesn't crash
    request.headers = Headers({})

    # We just want to make sure it runs without crashing and sets context if a tenant was resolved
    # We can mock set_tenant_context and sentry_sdk.set_tag

    async def call_next(req):
        return MagicMock()

    with patch("hiron.security.middleware.verify_token") as mock_verify, patch("sentry_sdk.set_tag") as mock_set_tag:
            # Fake token verification for a tenant
            mock_verify.return_value = {"tenantId": "123e4567-e89b-12d3-a456-426614174000"}
            request.headers = Headers({"Authorization": "Bearer fake_token"})

            await middleware.dispatch(request, call_next)

            # Assert set_tag was called with tenant_id, not set_user
            mock_set_tag.assert_any_call("tenant_id", "123e4567-e89b-12d3-a456-426614174000")
            # And it should be cleared at the end
            mock_set_tag.assert_called_with("tenant_id", None)
