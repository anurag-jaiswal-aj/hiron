import sys
from pathlib import Path

# Add the apps/api directory to sys.path so that absolute imports (e.g., `from hiron...`) resolve correctly
api_dir = Path(__file__).resolve().parent.parent / "apps" / "api"
sys.path.insert(0, str(api_dir))

# Import the FastAPI application instance
from hiron.main import app
import sentry_sdk

class VercelSentryFlushMiddleware:
    """Synchronously flushes Sentry before Vercel suspends the function."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
            await self.app(scope, receive, send)
        finally:
            if scope.get("type") == "http":
                sentry_sdk.flush(timeout=2.0)

# Replace the exported app instance for Vercel
app = VercelSentryFlushMiddleware(app)

# Export the app instance for the @vercel/python builder
__all__ = ["app"]
