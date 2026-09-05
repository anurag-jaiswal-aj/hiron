"""Security headers and request payload size limit middlewares per Phase 16."""

import ipaddress
import time
import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
import sentry_sdk
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware

from hiron.core.cache import CacheManager
from hiron.core.config import get_settings
from hiron.core.jwt import verify_token
from hiron.security.context import set_tenant_context

logger = structlog.get_logger("hiron.api.security")

MAX_JSON_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing mandatory security headers on every HTTP response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # Only send HSTS over HTTPS or in production environments where HTTPS is guaranteed
        settings = get_settings()
        if request.url.scheme == "https" or settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://cdn.jsdelivr.net;"
            )
        else:
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class RequestSizeLimitMiddleware:
    """Pure ASGI middleware rejecting oversized request bodies (1 MB JSON limit, 10 MB file limit)."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(  # noqa: C901
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_type = headers.get(b"content-type", b"").decode("utf-8", errors="ignore")
        content_length_raw = headers.get(b"content-length")

        path = scope.get("path", "")
        max_allowed = (
            MAX_FILE_SIZE_BYTES
            if "/resumes/upload" in path or "multipart/form-data" in content_type
            else MAX_JSON_SIZE_BYTES
        )

        if content_length_raw:
            try:
                length = int(content_length_raw)
                if length > max_allowed:
                    await self._send_413(send, max_allowed)
                    return
            except ValueError:
                pass

        total_size = 0
        too_large = False
        response_started = False

        async def intercept_send(message: MutableMapping[str, Any]) -> None:
            nonlocal response_started
            if too_large:
                return
            response_started = True
            await send(message)

        async def bounded_receive() -> MutableMapping[str, Any]:
            nonlocal total_size, too_large
            if too_large:
                return {"type": "http.disconnect"}

            message = await receive()
            if message["type"] == "http.request":
                total_size += len(message.get("body", b""))
                if total_size > max_allowed:
                    too_large = True
                    return {"type": "http.disconnect"}
            return message

        await self.app(scope, bounded_receive, intercept_send)

        if too_large and not response_started:
            await self._send_413(send, max_allowed)

        return

    async def _send_413(
        self, send: Callable[[MutableMapping[str, Any]], Awaitable[None]], max_allowed: int
    ) -> None:
        async def dummy_receive() -> MutableMapping[str, Any]:
            return {"type": "http.disconnect"}

        response = JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "error": {
                    "code": "REQUEST_TOO_LARGE",
                    "message": f"Payload size exceeds maximum allowed limit ({max_allowed // (1024 * 1024)} MB)",
                }
            },
        )
        await response(scope={"type": "http"}, receive=dummy_receive, send=send)


def is_trusted_proxy(ip: str, trusted_proxies: list[str]) -> bool:
    """Helper to check if an IP is within the trusted proxy list."""
    if not ip:
        return False
    try:
        ip_obj = ipaddress.ip_address(ip)
        for trusted in trusted_proxies:
            if "/" in trusted:
                if ip_obj in ipaddress.ip_network(trusted):
                    return True
            else:
                if ip_obj == ipaddress.ip_address(trusted):
                    return True
    except ValueError:
        pass
    return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed fixed-window rate limiter for API endpoints."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        settings = get_settings()

        # Skip rate limiting for internal health checks and docs
        if request.url.path in [
            "/api/health",
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]:
            return await call_next(request)

        path = request.url.path

        if path == "/api/v1/auth/forgot-password" or path == "/api/v1/users/invite/accept":
            limit = 5
            window_duration = 900  # 15 minutes
        else:
            limit = settings.rate_limit_requests_per_minute
            window_duration = 60  # 1 minute
            if limit <= 0:
                return await call_next(request)

        # Resolve direct peer IP
        direct_ip = request.client.host if request.client else "127.0.0.1"
        client_ip = direct_ip

        # If direct peer is a trusted proxy, try to extract X-Forwarded-For
        if is_trusted_proxy(direct_ip, settings.trusted_proxies):
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # The true client IP is usually the first in the comma-separated list
                client_ip = forwarded.split(",")[0].strip()

        window_time = int(time.time() / window_duration)
        if path == "/api/v1/auth/forgot-password":
            window_key = f"rate_limit:forgot_pwd:ip:{client_ip}:{window_time}"
        elif path == "/api/v1/users/invite/accept":
            window_key = f"rate_limit:invite_accept:ip:{client_ip}:{window_time}"
        else:
            window_key = f"rate_limit:ip:{client_ip}:{window_time}"

        try:
            cache = CacheManager()
            redis_client = cache._get_redis()

            pipe = redis_client.pipeline()
            pipe.incr(window_key)
            pipe.expire(window_key, window_duration)
            result = await pipe.execute()

            request_count = result[0]

            if request_count > limit:
                logger.warning(
                    "Rate limit exceeded",
                    client_ip=client_ip,
                    direct_ip=direct_ip,
                    path=request.url.path,
                    count=request_count,
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Rate limit exceeded. Try again later.",
                        }
                    },
                    headers={"Retry-After": str(window_duration)},
                )
        except Exception as e:
            logger.error("Rate limiter failed", error=str(e))

        return await call_next(request)


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Extracts tenant identity from authenticated JWTs and sets it in the request contextvar."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        tenant_id = None

        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ")[1]
            try:
                payload = verify_token(token, expected_type="access")
                tenant_str = payload.get("tenantId")
                if tenant_str:
                    uuid.UUID(tenant_str)  # strictly validate format
                    tenant_id = tenant_str
            except (ExpiredSignatureError, InvalidTokenError, ValueError, KeyError):
                # Don't fail the request here, let FastAPI auth dependencies handle 401s
                # if the route requires auth. Just leave tenant_id as None.
                pass

        set_tenant_context(tenant_id)
        if tenant_id:
            sentry_sdk.set_tag("tenant_id", tenant_id)

        try:
            return await call_next(request)
        finally:
            # Clear context so it doesn't leak to background tasks or subsequent requests in async workers
            set_tenant_context(None)
            sentry_sdk.set_tag("tenant_id", None)
