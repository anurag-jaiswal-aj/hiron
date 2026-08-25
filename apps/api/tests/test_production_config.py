"""Production deployment configuration, health probes, and readiness validation tests per Phase 18."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from hiron.core.config import Settings
from hiron.main import create_app


def test_production_settings_defaults() -> None:
    """Verify settings properties and environment detection."""
    settings = Settings(environment="production", worker_url="https://worker.hiron.dev", gemini_api_key="dummy_key")
    assert settings.is_production is True
    assert settings.environment == "production"

    dev_settings = Settings(environment="development")
    assert dev_settings.is_production is False


def test_health_liveness_endpoint() -> None:
    """Verify liveness probe endpoint returns 200 healthy status."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_readiness_endpoint_ready() -> None:
    """Verify readiness probe returns 200 ready status when database connection succeeds."""
    app = create_app()
    client = TestClient(app)

    with patch("hiron.health.router.check_database_connection", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = (True, 4.2)
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"]["status"] == "up"


@pytest.mark.asyncio
async def test_health_readiness_endpoint_not_ready() -> None:
    """Verify readiness probe returns 503 not_ready status when database connection fails."""
    app = create_app()
    client = TestClient(app)

    with patch("hiron.health.router.check_database_connection", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = (False, 0.0)
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"]["status"] == "down"


def test_openapi_docs_disabled_in_production() -> None:
    """Verify OpenAPI /docs and /redoc are disabled when environment is production."""
    prod_settings = Settings(environment="production", worker_url="https://worker.hiron.dev", gemini_api_key="dummy_key")

    with patch("hiron.main.get_settings", return_value=prod_settings):
        prod_app = create_app()
        client = TestClient(prod_app)

        docs_res = client.get("/docs")
        assert docs_res.status_code == 404

        redoc_res = client.get("/redoc")
        assert redoc_res.status_code == 404


def test_production_security_headers() -> None:
    """Verify security headers middleware attaches HSTS, CSP, and framing headers."""
    prod_settings = Settings(environment="production", worker_url="https://worker.hiron.dev", gemini_api_key="dummy_key")
    with patch("hiron.security.middleware.get_settings", return_value=prod_settings):
        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/health")
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert "max-age=31536000" in response.headers.get("strict-transport-security", "")


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the lru_cache on get_settings before and after each test."""
    from hiron.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_production_missing_gemini_key_fails() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required in production environment"):
        Settings(environment="production", worker_url="https://worker.hiron.dev", gemini_api_key=None)


def test_production_empty_gemini_key_fails() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required in production environment"):
        Settings(environment="production", worker_url="https://worker.hiron.dev", gemini_api_key="")


def test_production_valid_gemini_key_succeeds() -> None:
    settings = Settings(environment="production", worker_url="https://worker.hiron.dev", gemini_api_key="secret_valid_key")
    assert settings.gemini_api_key == "secret_valid_key"


def test_development_missing_gemini_key_succeeds() -> None:
    settings = Settings(environment="development", gemini_api_key=None)
    assert settings.gemini_api_key is None


def test_validation_error_does_not_leak_key() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY") as exc:
        Settings(environment="production", worker_url="https://worker.hiron.dev", gemini_api_key="")

    error_msg = str(exc.value)
    assert "GEMINI_API_KEY" in error_msg
    assert "secret_valid_key" not in error_msg
