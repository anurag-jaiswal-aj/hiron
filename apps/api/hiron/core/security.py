"""Security utilities for password hashing, verification, and rehash checks per Engineering Guidelines §16."""

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from hiron.core.config import get_settings


@lru_cache
def get_password_hasher() -> PasswordHasher:
    """Return a cached PasswordHasher instance configured from application settings."""
    settings = get_settings()
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
        hash_len=settings.argon2_hash_len,
        salt_len=settings.argon2_salt_len,
    )


def hash_password(password: str) -> str:
    """Hash a plain text password using the Argon2id algorithm.

    Args:
        password: Plain text password string to hash.

    Returns:
        Encoded Argon2id hash string starting with '$argon2id$'.

    Raises:
        ValueError: If the password string is empty.
    """
    if not password:
        raise ValueError("Password string cannot be empty.")
    hasher = get_password_hasher()
    return hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text candidate password against an encoded Argon2id hash.

    Args:
        plain_password: Plain text password candidate.
        hashed_password: Encoded Argon2id hash string to compare against.

    Returns:
        True if candidate password matches the hash, False on mismatch or invalid hash format.
    """
    if not plain_password or not hashed_password:
        return False
    hasher = get_password_hasher()
    try:
        return hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if a password hash requires rehashing due to updated security parameters.

    Args:
        hashed_password: Encoded Argon2id hash string to check.

    Returns:
        True if the hash parameters differ from current configuration, False otherwise.
    """
    if not hashed_password:
        return False
    hasher = get_password_hasher()
    try:
        return hasher.check_needs_rehash(hashed_password)
    except InvalidHashError:
        return False
