"""Integration tests for SecurityHeadersMiddleware and RequestSizeLimitMiddleware."""

from fastapi.testclient import TestClient

from hiron.main import create_app

app = create_app()
client = TestClient(app)


def test_security_headers_present_on_all_responses() -> None:
    """Verify security headers are included on API responses."""
    # Test HTTP -> NO HSTS (unless production)
    response = client.get("/api/v1/health")
    assert "Strict-Transport-Security" not in response.headers

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Content-Security-Policy") == "default-src 'self'"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    # Test HTTPS -> HSTS present
    https_response = client.get("https://testserver/api/v1/health")
    assert (
        https_response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    )


def test_request_size_limit_rejects_oversized_payload() -> None:
    """Verify RequestSizeLimitMiddleware returns 413 for oversized headers/bodies."""
    # 2 MB payload (limit for standard JSON is 1 MB)
    large_payload = "a" * (2 * 1024 * 1024)

    response = client.post(
        "/api/v1/auth/login",
        content=large_payload.encode("utf-8"),
        headers={"Content-Length": str(len(large_payload)), "Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
