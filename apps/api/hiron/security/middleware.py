"""Security headers and request payload size limit middlewares per Phase 16."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

MAX_JSON_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing mandatory security headers on every HTTP response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware rejecting oversized request bodies (1 MB JSON limit, 10 MB file limit)."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                is_upload_path = "/resumes/upload" in request.url.path
                max_allowed = MAX_FILE_SIZE_BYTES if is_upload_path else MAX_JSON_SIZE_BYTES

                if length > max_allowed:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "REQUEST_TOO_LARGE",
                                "message": f"Payload size exceeds maximum allowed limit ({max_allowed // (1024 * 1024)} MB)",
                            }
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)
