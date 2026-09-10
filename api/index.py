import sys
import contextlib
from pathlib import Path

# Add the apps/api directory to sys.path so that absolute imports (e.g., `from hiron...`) resolve correctly
api_dir = Path(__file__).resolve().parent.parent / "apps" / "api"
sys.path.insert(0, str(api_dir))

# Import the FastAPI application instance
from hiron.main import app
import sentry_sdk
from opentelemetry import metrics

class VercelTelemetryFlushMiddleware:
    """Delays the final HTTP response body until Sentry and OTEL flush, keeping the Vercel container alive."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        final_message = None

        async def send_wrapper(message):
            nonlocal final_message
            if message.get("type") == "http.response.body" and not message.get("more_body", False):
                final_message = message
            else:
                await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            with contextlib.suppress(Exception):
                sentry_sdk.flush(timeout=2.0)

            with contextlib.suppress(Exception):
                provider = metrics.get_meter_provider()
                if hasattr(provider, "force_flush"):
                    provider.force_flush(timeout_millis=2000)

            if final_message is not None:
                await send(final_message)

# Replace the exported app instance for Vercel
app = VercelTelemetryFlushMiddleware(app)

# Export the app instance for the @vercel/python builder
__all__ = ["app"]
