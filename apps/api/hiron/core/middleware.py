"""Custom FastAPI middleware for request tracing, timing, and structlog context binding."""

import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Binds request_id, HTTP method, and path to structlog context and measures latency."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        # Bind structlog context variables for the duration of the request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)

        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)

        logger = structlog.get_logger("hiron.api.access")
        logger.info(
            "HTTP request processed",
            status_code=response.status_code,
            latency_ms=process_time_ms,
        )

        return response


ProcessTimeAndRequestIdMiddleware = RequestTracingMiddleware
