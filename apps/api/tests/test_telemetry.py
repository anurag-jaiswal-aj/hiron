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
async def test_vercel_telemetry_flush_middleware():
    """Verify VercelTelemetryFlushMiddleware delays final body, flushes Sentry/OTEL on HTTP, and handles exceptions safely."""
    from api.index import VercelTelemetryFlushMiddleware
    from unittest.mock import AsyncMock, patch, MagicMock

    mock_app = AsyncMock()
    middleware = VercelTelemetryFlushMiddleware(mock_app)
    mock_send = AsyncMock()

    # Helper for normal app behavior
    async def app_normal(scope, receive, send_wrapper):
        await send_wrapper({"type": "http.response.start"})
        await send_wrapper({"type": "http.response.body", "body": b"hello", "more_body": False})

    # Test A: App success + flush success
    mock_app.side_effect = app_normal
    events = []

    def mock_sentry_flush_success(*args, **kwargs):
        events.append("sentry_flush")

    mock_provider = MagicMock()
    def mock_otel_flush_success(*args, **kwargs):
        events.append("otel_flush")
    mock_provider.force_flush.side_effect = mock_otel_flush_success

    async def tracking_send(message):
        events.append(f"send_{message['type']}")

    with patch("api.index.sentry_sdk.flush") as mock_sentry_flush, \
         patch("api.index.metrics.get_meter_provider", return_value=mock_provider):
        mock_sentry_flush.side_effect = mock_sentry_flush_success
        await middleware({"type": "http"}, {}, tracking_send)

        assert events == [
            "send_http.response.start",
            "sentry_flush",
            "otel_flush",
            "send_http.response.body"
        ]

    # Test B: App success + sentry raises, otel succeeds
    mock_app.side_effect = app_normal
    events = []

    def mock_sentry_flush_raises(*args, **kwargs):
        events.append("sentry_flush_raises")
        raise RuntimeError("Sentry network error")

    async def tracking_send_b(message):
        events.append(f"send_{message['type']}")

    with patch("api.index.sentry_sdk.flush") as mock_sentry_flush, \
         patch("api.index.metrics.get_meter_provider", return_value=mock_provider):
        mock_sentry_flush.side_effect = mock_sentry_flush_raises
        # The flush exception should be swallowed and NOT mask the response
        await middleware({"type": "http"}, {}, tracking_send_b)

        assert events == [
            "send_http.response.start",
            "sentry_flush_raises",
            "otel_flush",
            "send_http.response.body"
        ]

    # Test B2: App success + sentry succeeds, otel raises
    mock_app.side_effect = app_normal
    events = []

    def mock_otel_flush_raises(*args, **kwargs):
        events.append("otel_flush_raises")
        raise RuntimeError("OTEL network error")

    mock_provider2 = MagicMock()
    mock_provider2.force_flush.side_effect = mock_otel_flush_raises

    with patch("api.index.sentry_sdk.flush") as mock_sentry_flush, \
         patch("api.index.metrics.get_meter_provider", return_value=mock_provider2):
        mock_sentry_flush.side_effect = mock_sentry_flush_success
        await middleware({"type": "http"}, {}, tracking_send_b)

        assert events == [
            "send_http.response.start",
            "sentry_flush",
            "otel_flush_raises",
            "send_http.response.body"
        ]

    # Test C: App raises + both flushes succeed
    events = []
    mock_app.side_effect = ValueError("App crash")

    with patch("api.index.sentry_sdk.flush") as mock_sentry_flush, \
         patch("api.index.metrics.get_meter_provider", return_value=mock_provider):
        mock_sentry_flush.side_effect = mock_sentry_flush_success
        with pytest.raises(ValueError, match="App crash"):
            await middleware({"type": "http"}, {}, mock_send)

        assert events == ["sentry_flush", "otel_flush"]

    # Test D: App raises + both flushes also raise
    events = []
    mock_app.side_effect = ValueError("App crash")

    with patch("api.index.sentry_sdk.flush") as mock_sentry_flush, \
         patch("api.index.metrics.get_meter_provider", return_value=mock_provider2):
        mock_sentry_flush.side_effect = mock_sentry_flush_raises
        # The original exception MUST propagate, and flush exceptions are swallowed
        with pytest.raises(ValueError, match="App crash"):
            await middleware({"type": "http"}, {}, mock_send)

        assert events == ["sentry_flush_raises", "otel_flush_raises"]

    # Test E: Streaming behavior remains unchanged
    events = []
    async def app_streaming(scope, receive, send_wrapper):
        await send_wrapper({"type": "http.response.start"})
        await send_wrapper({"type": "http.response.body", "body": b"chunk1", "more_body": True})
        await send_wrapper({"type": "http.response.body", "body": b"chunk2", "more_body": False})

    mock_app.side_effect = app_streaming

    with patch("api.index.sentry_sdk.flush") as mock_sentry_flush, \
         patch("api.index.metrics.get_meter_provider", return_value=mock_provider):
        mock_sentry_flush.side_effect = mock_sentry_flush_success

        async def streaming_send(message):
            events.append(f"send_{message.get('body', b'start').decode()}")

        await middleware({"type": "http"}, {}, streaming_send)

        assert events == [
            "send_start",
            "send_chunk1",
            "sentry_flush",
            "otel_flush",
            "send_chunk2",
        ]

    # Test F: Non-HTTP scope
    mock_app.reset_mock()
    mock_app.side_effect = None
    mock_provider.reset_mock()

    with patch("api.index.sentry_sdk.flush") as mock_sentry_flush, \
         patch("api.index.metrics.get_meter_provider", return_value=mock_provider):
        await middleware({"type": "lifespan"}, {}, mock_send)
        mock_app.assert_awaited_once_with({"type": "lifespan"}, {}, mock_send)
        mock_sentry_flush.assert_not_called()
        mock_provider.force_flush.assert_not_called()
