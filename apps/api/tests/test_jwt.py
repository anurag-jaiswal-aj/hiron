"""Unit test suite for RS256 JWT creation, verification, decoding, and RSA key file management."""

import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from jwt.exceptions import InvalidTokenError

from hiron.core.config import get_settings
from hiron.core.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    load_private_key,
    load_public_key,
    verify_token,
)


def test_load_private_key_success() -> None:
    """Verify load_private_key reads and caches private key from configured file path."""
    content = load_private_key()
    assert content.startswith("-----BEGIN PRIVATE KEY-----")


def test_load_public_key_success() -> None:
    """Verify load_public_key reads and caches public key from configured file path."""
    content = load_public_key()
    assert content.startswith("-----BEGIN PUBLIC KEY-----")


def test_load_private_key_env_var_success(
    monkeypatch: pytest.MonkeyPatch, session_rsa_keys: tuple[Path, Path]
) -> None:
    """Verify load_private_key prioritizes jwt_private_key_content if provided."""
    priv_file, _ = session_rsa_keys
    pem_content = priv_file.read_text(encoding="utf-8")

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_private_key_content", pem_content)

    # Intentionally break the file path to ensure it's not being used
    monkeypatch.setattr(settings, "jwt_private_key_path", "/nonexistent/path")

    load_private_key.cache_clear()
    content = load_private_key()
    assert content == pem_content.strip()


def test_load_public_key_env_var_success(
    monkeypatch: pytest.MonkeyPatch, session_rsa_keys: tuple[Path, Path]
) -> None:
    """Verify load_public_key prioritizes jwt_public_key_content if provided."""
    _, pub_file = session_rsa_keys
    pem_content = pub_file.read_text(encoding="utf-8")

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_public_key_content", pem_content)

    # Intentionally break the file path to ensure it's not being used
    monkeypatch.setattr(settings, "jwt_public_key_path", "/nonexistent/path")

    load_public_key.cache_clear()
    content = load_public_key()
    assert content == pem_content.strip()


def test_load_key_from_env_var_with_escaped_newlines(
    monkeypatch: pytest.MonkeyPatch, session_rsa_keys: tuple[Path, Path]
) -> None:
    """Verify load_private_key correctly normalizes escaped \\n newlines from env variables."""
    priv_file, _ = session_rsa_keys
    pem_content = priv_file.read_text(encoding="utf-8")
    escaped_pem = pem_content.replace("\n", "\\n")

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_private_key_content", escaped_pem)

    load_private_key.cache_clear()
    content = load_private_key()
    assert content == pem_content.strip()
    assert "\\n" not in content


def test_load_private_key_missing_file_raises_file_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify load_private_key raises FileNotFoundError when configured file is missing."""
    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_private_key_path", "/nonexistent/path/private.pem")
    load_private_key.cache_clear()

    with pytest.raises(FileNotFoundError, match="JWT private key file not found"):
        load_private_key()


def test_load_public_key_missing_file_raises_file_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify load_public_key raises FileNotFoundError when configured file is missing."""
    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_public_key_path", "/nonexistent/path/public.pem")
    load_public_key.cache_clear()

    with pytest.raises(FileNotFoundError, match="JWT public key file not found"):
        load_public_key()


def test_load_key_empty_file_raises_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify load_private_key raises ValueError when key file is empty."""
    empty_file = tmp_path / "empty_key.pem"
    empty_file.write_text("")

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_private_key_path", str(empty_file))
    load_private_key.cache_clear()

    with pytest.raises(ValueError, match="is empty"):
        load_private_key()


def test_missing_key_configuration_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify missing both file path and env var raises clear ValueError."""
    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_private_key_path", None)
    monkeypatch.setattr(settings, "jwt_private_key_content", None)

    load_private_key.cache_clear()
    with pytest.raises(ValueError, match="path is not configured and no content provided"):
        load_private_key()


def test_invalid_private_pem_content_raises_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify invalid private PEM content immediately raises ValueError during loader execution."""
    invalid_file = tmp_path / "invalid_private.pem"
    invalid_file.write_text("NOT_A_VALID_PRIVATE_PEM")

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_private_key_path", str(invalid_file))
    load_private_key.cache_clear()

    with pytest.raises(ValueError, match="Invalid RSA private key PEM format"):
        load_private_key()


def test_invalid_public_pem_content_raises_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify invalid public PEM content immediately raises ValueError during loader execution."""
    invalid_file = tmp_path / "invalid_public.pem"
    invalid_file.write_text("NOT_A_VALID_PUBLIC_PEM")

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_public_key_path", str(invalid_file))
    load_public_key.cache_clear()

    with pytest.raises(ValueError, match="Invalid RSA public key PEM format"):
        load_public_key()


def test_create_access_token_exact_claims_and_casing() -> None:
    """Verify access token claims match API Contract §4 exactly (sub, tenantId, email, role, type, iat, exp)."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    email = "jane@acme.com"
    role = "recruiter"

    token = create_access_token(user_id=user_id, tenant_id=tenant_id, email=email, role=role)
    payload = decode_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["tenantId"] == str(tenant_id)
    assert payload["email"] == email
    assert payload["role"] == role
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload


def test_create_refresh_token_claims_and_casing() -> None:
    """Verify refresh token claims match API Contract §4 & Database Design §5.3."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    jti = str(uuid.uuid4())

    token = create_refresh_token(user_id=user_id, tenant_id=tenant_id, jti=jti)
    payload = decode_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["tenantId"] == str(tenant_id)
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti
    assert "iat" in payload
    assert "exp" in payload


def test_verify_token_success() -> None:
    """Verify verify_token validates signature and expected type."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        email="admin@acme.com",
        role="org_admin",
    )

    verified = verify_token(token, expected_type="access")
    assert verified["sub"] == str(user_id)
    assert verified["tenantId"] == str(tenant_id)


def test_verify_token_expired_raises_invalid_token_error() -> None:
    """Verify verify_token raises ExpiredSignatureError (subclass of InvalidTokenError) on expired token."""
    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@acme.com",
        role="recruiter",
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(InvalidTokenError):
        verify_token(token, expected_type="access")


def test_verify_token_wrong_type_raises_invalid_token_error() -> None:
    """Verify verify_token raises InvalidTokenError on wrong token type."""
    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@acme.com",
        role="recruiter",
    )

    with pytest.raises(InvalidTokenError, match="Invalid token type"):
        verify_token(token, expected_type="refresh")
