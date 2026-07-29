"""JWT token creation, decoding, verification, and RSA key management per API Contract §4 & Engineering Guidelines §16.1."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Union
import uuid

from cryptography.hazmat.primitives import serialization
import jwt
from jwt.exceptions import InvalidTokenError
import structlog

from hiron.core.config import get_settings

logger = structlog.get_logger("hiron.api.jwt")

# ==============================================================================
# 1. RSA KEY MANAGEMENT & CACHING
# ==============================================================================

@lru_cache
def load_private_key() -> str:
    """Load and validate RSA private key PEM string from configured file path.

    Returns:
        Validated RSA private key PEM string.

    Raises:
        FileNotFoundError: If the configured private key file does not exist.
        ValueError: If the private key path/file is empty or has invalid PEM format.
    """
    settings = get_settings()
    if not settings.jwt_private_key_path:
        raise ValueError("JWT private key path is not configured.")
    
    key_path = Path(settings.jwt_private_key_path)
    if not key_path.exists() or not key_path.is_file():
        raise FileNotFoundError(f"JWT private key file not found at path: {key_path}")
    
    content = key_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"JWT private key file is empty at path: {key_path}")
    
    try:
        serialization.load_pem_private_key(content.encode("utf-8"), password=None)
    except Exception as exc:
        raise ValueError(f"Invalid RSA private key PEM format at path '{key_path}': {exc}") from exc
    
    return content


@lru_cache
def load_public_key() -> str:
    """Load and validate RSA public key PEM string from configured file path.

    Returns:
        Validated RSA public key PEM string.

    Raises:
        FileNotFoundError: If the configured public key file does not exist.
        ValueError: If the public key path/file is empty or has invalid PEM format.
    """
    settings = get_settings()
    if not settings.jwt_public_key_path:
        raise ValueError("JWT public key path is not configured.")
    
    key_path = Path(settings.jwt_public_key_path)
    if not key_path.exists() or not key_path.is_file():
        raise FileNotFoundError(f"JWT public key file not found at path: {key_path}")
    
    content = key_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"JWT public key file is empty at path: {key_path}")
    
    try:
        serialization.load_pem_public_key(content.encode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid RSA public key PEM format at path '{key_path}': {exc}") from exc
    
    return content


# ==============================================================================
# 2. JWT TOKEN CREATION UTILITIES
# ==============================================================================

def create_access_token(
    user_id: Union[str, uuid.UUID],
    tenant_id: Union[str, uuid.UUID],
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed RS256 JWT access token per API Contract §4."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    
    if expires_delta is not None:
        expire_time = now + expires_delta
    else:
        expire_time = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "tenantId": str(tenant_id),
        "email": email,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire_time.timestamp()),
    }

    private_key_pem = load_private_key()
    return jwt.encode(payload, private_key_pem, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: Union[str, uuid.UUID],
    tenant_id: Union[str, uuid.UUID],
    jti: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed RS256 JWT refresh token per API Contract §4 & Database Design §5.3."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    
    if expires_delta is not None:
        expire_time = now + expires_delta
    else:
        expire_time = now + timedelta(days=settings.refresh_token_expire_days)

    token_jti = jti or str(uuid.uuid4())

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "tenantId": str(tenant_id),
        "type": "refresh",
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(expire_time.timestamp()),
    }

    private_key_pem = load_private_key()
    return jwt.encode(payload, private_key_pem, algorithm=settings.jwt_algorithm)


# ==============================================================================
# 3. JWT TOKEN DECODING & VERIFICATION UTILITIES
# ==============================================================================

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify an RS256 JWT token using the RSA public key."""
    settings = get_settings()
    public_key_pem = load_public_key()
    
    return jwt.decode(
        token,
        public_key_pem,
        algorithms=[settings.jwt_algorithm],
        options={"verify_exp": True, "require": ["sub", "tenantId", "type", "exp", "iat"]},
    )


def verify_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """Verify an RS256 JWT token signature, expiration, and required claim payload."""
    payload = decode_token(token)
    
    token_type = payload.get("type")
    if token_type != expected_type:
        logger.warning(
            "JWT token type mismatch",
            expected_type=expected_type,
            actual_type=token_type,
            user_id=payload.get("sub"),
        )
        raise InvalidTokenError(f"Invalid token type: expected '{expected_type}', got '{token_type}'")

    if expected_type == "access":
        for required_claim in ("email", "role"):
            if not payload.get(required_claim):
                raise InvalidTokenError(f"Missing required access claim: '{required_claim}'")

    return payload
