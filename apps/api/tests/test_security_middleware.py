import json

import pytest
from httpx import ASGITransport, AsyncClient

from hiron.main import app


@pytest.mark.asyncio
async def test_security_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Docs endpoint should have different CSP
        response = await client.get("/docs")
        # Over HTTP, HSTS is NOT applied (except in production which this isn't)
        assert "Strict-Transport-Security" not in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "unsafe-inline" in response.headers["Content-Security-Policy"]

        # Try over HTTPS
        https_response = await client.get("https://test/docs")
        assert "Strict-Transport-Security" in https_response.headers

        # API endpoint should have strict CSP
        response = await client.get("/api/v1/health")
        assert response.headers["Content-Security-Policy"] == "default-src 'self'"


# Size limit tests
@pytest.mark.asyncio
async def test_size_limit_json_over():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"data": "x" * (1 * 1024 * 1024 + 10)}
        headers = {"Content-Length": str(len(json.dumps(payload)))}
        response = await client.post("/api/v1/auth/login", json=payload, headers=headers)
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


@pytest.mark.asyncio
async def test_size_limit_json_under():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"data": "x" * 10}
        headers = {"Content-Length": str(len(json.dumps(payload)))}
        response = await client.post("/api/v1/auth/login", json=payload, headers=headers)
        # Should reach FastAPI validation (422)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_size_limit_multipart_over():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Content-Length": str(11 * 1024 * 1024), "Content-Type": "multipart/form-data"}
        response = await client.post("/api/v1/resumes/upload", headers=headers)
        assert response.status_code == 413


@pytest.mark.asyncio
async def test_size_limit_multipart_under():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Content-Length": str(2 * 1024 * 1024), "Content-Type": "multipart/form-data"}
        response = await client.post("/api/v1/resumes/upload", headers=headers)
        # Auth dependency fails (401) or parsing fails (422) but NOT 413
        assert response.status_code != 413


@pytest.mark.asyncio
async def test_chunked_json_over():
    async def generate_large_body():
        for _ in range(2000):  # ~ 2MB
            yield b"x" * 1024

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            content=generate_large_body(),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413


@pytest.mark.asyncio
async def test_chunked_multipart_over():
    boundary = b"----WebKitFormBoundary7MA4YWxkTrZu0gW"

    async def generate_huge_body():
        yield b"--" + boundary + b"\r\n"
        yield b'Content-Disposition: form-data; name="file"; filename="big.txt"\r\n'
        yield b"Content-Type: text/plain\r\n\r\n"

        # yield 11MB of data
        chunk = b"x" * 1024 * 64
        for _ in range(11 * 1024 * 1024 // len(chunk) + 1):
            yield chunk

        yield b"\r\n--" + boundary + b"--\r\n"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/resumes/upload",
            content=generate_huge_body(),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
        )
        assert response.status_code == 413


@pytest.mark.asyncio
async def test_chunked_under():
    async def generate_small_body():
        for _ in range(10):  # ~ 10KB
            yield b"x" * 1024

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            content=generate_small_body(),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422  # Passed middleware


# Rate Limiting Tests

from hiron.core.cache import CacheManager


@pytest.fixture(autouse=True)
def clear_redis():
    """Clear rate limit keys before each test."""
    import asyncio

    async def _clear():
        cache = CacheManager()
        redis = cache._get_redis()
        # Mocking flush is safe in test DB
        keys = await redis.keys("rate_limit:ip:*")
        if keys:
            await redis.delete(*keys)

    asyncio.run(_clear())


@pytest.mark.asyncio
async def test_rate_limit_direct_untrusted(monkeypatch):
    import hiron.core.config

    settings = hiron.core.config.get_settings()
    monkeypatch.setattr(settings, "rate_limit_requests_per_minute", 2)
    monkeypatch.setattr(settings, "trusted_proxies", ["10.0.0.1"])

    async with AsyncClient(
        transport=ASGITransport(app=app, client=("192.168.1.1", 12345)), base_url="http://test"
    ) as client:
        # Client spoofing X-Forwarded-For should be ignored
        headers = {"X-Forwarded-For": "8.8.8.8"}
        res1 = await client.post("/api/v1/auth/login", headers=headers)
        res2 = await client.post("/api/v1/auth/login", headers=headers)
        res3 = await client.post("/api/v1/auth/login", headers=headers)

        assert res3.status_code == 429

        # Another request from same untrusted client with DIFFERENT spoofed IP should STILL be blocked
        headers2 = {"X-Forwarded-For": "4.4.4.4"}
        res4 = await client.post("/api/v1/auth/login", headers=headers2)
        assert res4.status_code == 429  # Same peer IP (192.168.1.1)


@pytest.mark.asyncio
async def test_rate_limit_trusted_proxy(monkeypatch):
    import hiron.core.config

    settings = hiron.core.config.get_settings()
    monkeypatch.setattr(settings, "rate_limit_requests_per_minute", 2)
    monkeypatch.setattr(settings, "trusted_proxies", ["10.0.0.1"])

    # Client IP is the proxy IP
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("10.0.0.1", 12345)), base_url="http://test"
    ) as client:
        # Valid forwarded IP
        headers = {"X-Forwarded-For": "8.8.8.8"}
        await client.post("/api/v1/auth/login", headers=headers)
        await client.post("/api/v1/auth/login", headers=headers)
        res3 = await client.post("/api/v1/auth/login", headers=headers)
        assert res3.status_code == 429

        # A DIFFERENT forwarded IP via the same trusted proxy SHOULD NOT be rate limited yet
        headers2 = {"X-Forwarded-For": "4.4.4.4"}
        res4 = await client.post("/api/v1/auth/login", headers=headers2)
        assert res4.status_code != 429


@pytest.mark.asyncio
async def test_rate_limit_redis_failopen(monkeypatch):
    import hiron.core.config

    settings = hiron.core.config.get_settings()
    monkeypatch.setattr(settings, "rate_limit_requests_per_minute", 1)

    # Mock redis to fail
    class FailingRedis:
        def pipeline(self):
            class Pipe:
                def incr(self, *args):
                    pass

                def expire(self, *args):
                    pass

                async def execute(self):
                    raise Exception("Redis down!")

            return Pipe()

    import hiron.security.middleware

    monkeypatch.setattr(
        hiron.security.middleware.CacheManager, "_get_redis", lambda self: FailingRedis()
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # All requests should pass even if Redis throws exceptions
        res1 = await client.post("/api/v1/auth/login")
        res2 = await client.post("/api/v1/auth/login")
        res3 = await client.post("/api/v1/auth/login")
        assert res3.status_code != 429
