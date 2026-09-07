"""Custom FastAPI middleware for request tracing, timing, and structlog context binding."""

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from hiron.core.metrics import api_request_duration_histogram, api_requests_counter


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Binds request_id, HTTP method, and path to structlog context and measures latency."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()
        request.state.start_time = start_time

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

        route = request.scope.get("route")
        path_template = route.path if route and hasattr(route, "path") else "unknown"

        logger = structlog.get_logger("hiron.api.access")

        try:
            labels = {
                "method": request.method,
                "path": path_template,
                "status_code": str(response.status_code),
            }
            api_request_duration_histogram.record(process_time_ms, labels)
            api_requests_counter.add(1, labels)
        except Exception as e:
            logger.warning("metric_recording_failed", error=str(e))

        logger.info(
            "api_request",
            status_code=response.status_code,
            duration_ms=process_time_ms,
        )

        return response


ProcessTimeAndRequestIdMiddleware = RequestTracingMiddleware
