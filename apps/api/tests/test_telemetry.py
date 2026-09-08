import pytest
from unittest.mock import patch, MagicMock

import sentry_sdk
from hiron.core.sentry import sentry_before_send
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


@pytest.mark.asyncio
async def test_worker_sentry_initialization():
    """Verify worker startup calls sentry_sdk.init."""
    from unittest.mock import patch
    import importlib

    with patch("hiron.core.sentry.init_sentry") as mock_init:
        import apps.worker.src.main
        importlib.reload(apps.worker.src.main)

        mock_init.assert_called()
        # The last call should be the reload
        args, _kwargs = mock_init.call_args_list[-1]
        assert apps.worker.src.main.settings.sentry_dsn == args[0]
        assert apps.worker.src.main.settings.environment == args[1]


@pytest.mark.asyncio
async def test_ai_sentry_capture_embedding_swallowed():
    """Verify swallowed embedding failure is captured with expected scoped tags."""
    from hiron.embeddings.generator import EmbeddingGenerator
    from unittest.mock import AsyncMock, patch

    generator = EmbeddingGenerator(model_version="test-model")
    generator.gemini_api_key = "fake"

    with patch("google.genai.Client") as mock_client, \
         patch("hiron.embeddings.generator.get_settings") as mock_settings, \
         patch("sentry_sdk.push_scope") as mock_push_scope, \
         patch("sentry_sdk.capture_exception") as mock_capture:

        mock_settings.return_value.gemini_api_key = "fake_key"
        mock_settings.return_value.is_production = False

        mock_client_instance = mock_client.return_value
        test_exception = Exception("Gemini Down")
        mock_client_instance.aio.models.embed_content = AsyncMock(side_effect=test_exception)

        mock_scope = MagicMock()
        mock_push_scope.return_value.__enter__.return_value = mock_scope

        # The fallback will succeed and swallow the error
        result = await generator.generate_embedding("Test")
        assert result.is_fallback is True

        # Verify Sentry captured the exception
        mock_capture.assert_called_once_with(test_exception)

        # Verify scope tags were set
        mock_scope.set_tag.assert_any_call("ai.provider", "gemini")
        mock_scope.set_tag.assert_any_call("ai.operation", "embedding")


@pytest.mark.asyncio
async def test_ai_sentry_capture_scoring_terminal():
    """Verify terminal scoring AI failure is captured."""
    from hiron.scores.engine import AIScoringEngine
    from fastapi import HTTPException
    import httpx

    engine = AIScoringEngine()

    with patch("httpx.AsyncClient.post") as mock_post, \
         patch("hiron.scores.engine.get_settings") as mock_settings, \
         patch("sentry_sdk.push_scope") as mock_push_scope, \
         patch("sentry_sdk.capture_exception") as mock_capture:

        mock_settings.return_value.gemini_api_key = "fake_key"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid Request"

        test_exception = httpx.HTTPStatusError("400 Bad Request", request=MagicMock(), response=mock_response)
        mock_post.side_effect = test_exception

        mock_scope = MagicMock()
        mock_push_scope.return_value.__enter__.return_value = mock_scope

        candidate_mock = MagicMock()
        candidate_mock.skills = []
        candidate_mock.summary = "summary"
        job_mock = MagicMock()
        job_mock.required_skills = []
        job_mock.description = "description"

        # Should raise HTTPException and capture Sentry
        with pytest.raises(HTTPException) as exc_info:
            await engine.evaluate(candidate_mock, job_mock)

        assert exc_info.value.status_code == 400

        mock_capture.assert_called_once_with(test_exception)
        mock_scope.set_tag.assert_any_call("ai.provider", "gemini")
        mock_scope.set_tag.assert_any_call("ai.operation", "scoring")

@pytest.mark.asyncio
async def test_vercel_sentry_flush_middleware():
    """Verify VercelSentryFlushMiddleware flushes on HTTP and handles exceptions."""
    from api.index import VercelSentryFlushMiddleware
    from unittest.mock import AsyncMock, patch

    mock_app = AsyncMock()
    middleware = VercelSentryFlushMiddleware(mock_app)

    with patch("api.index.sentry_sdk.flush") as mock_flush:
        # 1. HTTP scope
        await middleware({"type": "http"}, {}, {})
        mock_app.assert_awaited_once_with({"type": "http"}, {}, {})
        mock_flush.assert_called_once_with(timeout=2.0)

        mock_app.reset_mock()
        mock_flush.reset_mock()

        # 2. Non-HTTP scope (e.g. lifespan)
        await middleware({"type": "lifespan"}, {}, {})
        mock_app.assert_awaited_once_with({"type": "lifespan"}, {}, {})
        mock_flush.assert_not_called()

        mock_app.reset_mock()
        mock_flush.reset_mock()

        # 3. Exception propagation
        mock_app.side_effect = ValueError("App crash")
        with pytest.raises(ValueError, match="App crash"):
            await middleware({"type": "http"}, {}, {})

        mock_flush.assert_called_once_with(timeout=2.0)
