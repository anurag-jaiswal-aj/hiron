"""Unit test suite for RS256 JWT creation, verification, decoding, and RSA key file management."""

from datetime import timedelta
from pathlib import Path
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
import pytest

from hiron.core.config import get_settings
from hiron.core.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    load_private_key,
    load_public_key,
    verify_token,
)


@pytest.fixture
def rsa_key_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Generate temporary RSA key files and patch settings to point to them."""
    private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    priv_pem = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = private_key_obj.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    priv_file = tmp_path / "test_rsa_private.pem"
    pub_file = tmp_path / "test_rsa_public.pem"

    priv_file.write_bytes(priv_pem)
    pub_file.write_bytes(pub_pem)

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_private_key_path", str(priv_file))
    monkeypatch.setattr(settings, "jwt_public_key_path", str(pub_file))

    # Clear LRU cache before and after test
    load_private_key.cache_clear()
    load_public_key.cache_clear()

    yield priv_file, pub_file

    load_private_key.cache_clear()
    load_public_key.cache_clear()


def test_load_private_key_success(rsa_key_files: tuple[Path, Path]) -> None:
    """Verify load_private_key reads and caches private key from configured file path."""
    content = load_private_key()
    assert content.startswith("-----BEGIN PRIVATE KEY-----")


def test_load_public_key_success(rsa_key_files: tuple[Path, Path]) -> None:
    """Verify load_public_key reads and caches public key from configured file path."""
    content = load_public_key()
    assert content.startswith("-----BEGIN PUBLIC KEY-----")


def test_load_private_key_missing_file_raises_file_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify load_private_key raises FileNotFoundError when configured file is missing."""
    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_private_key_path", "/nonexistent/path/private.pem")
    load_private_key.cache_clear()

    with pytest.raises(FileNotFoundError, match="JWT private key file not found"):
        load_private_key()


def test_load_public_key_missing_file_raises_file_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify load_public_key raises FileNotFoundError when configured file is missing."""
    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_public_key_path", "/nonexistent/path/public.pem")
    load_public_key.cache_clear()

    with pytest.raises(FileNotFoundError, match="JWT public key file not found"):
        load_public_key()


def test_load_key_empty_file_raises_value_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify load_private_key raises ValueError when key file is empty."""
    empty_file = tmp_path / "empty_key.pem"
    empty_file.write_text("")

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_private_key_path", str(empty_file))
    load_private_key.cache_clear()

    with pytest.raises(ValueError, match="is empty"):
        load_private_key()


def test_invalid_private_pem_content_raises_value_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify invalid private PEM content immediately raises ValueError during loader execution."""
    invalid_file = tmp_path / "invalid_private.pem"
    invalid_file.write_text("NOT_A_VALID_PRIVATE_PEM")

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_private_key_path", str(invalid_file))
    load_private_key.cache_clear()

    with pytest.raises(ValueError, match="Invalid RSA private key PEM format"):
        load_private_key()


def test_invalid_public_pem_content_raises_value_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify invalid public PEM content immediately raises ValueError during loader execution."""
    invalid_file = tmp_path / "invalid_public.pem"
    invalid_file.write_text("NOT_A_VALID_PUBLIC_PEM")

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_public_key_path", str(invalid_file))
    load_public_key.cache_clear()

    with pytest.raises(ValueError, match="Invalid RSA public key PEM format"):
        load_public_key()


def test_create_access_token_exact_claims_and_casing(rsa_key_files: tuple[Path, Path]) -> None:
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


def test_create_refresh_token_claims_and_casing(rsa_key_files: tuple[Path, Path]) -> None:
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


def test_verify_token_success(rsa_key_files: tuple[Path, Path]) -> None:
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


def test_verify_token_expired_raises_invalid_token_error(rsa_key_files: tuple[Path, Path]) -> None:
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


def test_verify_token_wrong_type_raises_invalid_token_error(rsa_key_files: tuple[Path, Path]) -> None:
    """Verify verify_token raises InvalidTokenError on wrong token type."""
    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@acme.com",
        role="recruiter",
    )

    with pytest.raises(InvalidTokenError, match="Invalid token type"):
        verify_token(token, expected_type="refresh")
