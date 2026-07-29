"""Unit test suite for Argon2id password hashing, verification, and rehash security utilities."""

from argon2 import PasswordHasher
import pytest

from hiron.core.security import hash_password, needs_rehash, verify_password


def test_hash_password_returns_argon2id_format() -> None:
    """Verify hash_password generates a valid Argon2id hash string starting with $argon2id$."""
    raw_password = "CorrectHorseBatteryStaple123!"
    hashed = hash_password(raw_password)
    
    assert isinstance(hashed, str)
    assert hashed.startswith("$argon2id$")
    assert hashed != raw_password


def test_verify_password_matching() -> None:
    """Verify verify_password returns True for matching plain text and Argon2id hash."""
    raw_password = "SecureRecruiterPassword2026!"
    hashed = hash_password(raw_password)
    
    assert verify_password(raw_password, hashed) is True


def test_verify_password_non_matching() -> None:
    """Verify verify_password returns False for an incorrect plain text candidate."""
    raw_password = "CorrectPassword123!"
    wrong_password = "WrongPassword123!"
    hashed = hash_password(raw_password)
    
    assert verify_password(wrong_password, hashed) is False


def test_verify_password_invalid_hash_string() -> None:
    """Verify verify_password handles malformed hash strings gracefully returning False."""
    assert verify_password("AnyPassword123!", "invalid_hash_format") is False
    assert verify_password("AnyPassword123!", "$argon2id$v=19$m=4096,t=3,p=1$invalid") is False


def test_verify_password_empty_inputs() -> None:
    """Verify verify_password returns False when given empty inputs without raising exceptions."""
    hashed = hash_password("ValidPassword123!")
    
    assert verify_password("", hashed) is False
    assert verify_password("ValidPassword123!", "") is False
    assert verify_password("", "") is False


def test_hash_password_empty_raises_value_error() -> None:
    """Verify hash_password raises ValueError when passed an empty string."""
    with pytest.raises(ValueError, match="Password string cannot be empty"):
        hash_password("")


def test_needs_rehash_fresh_hash() -> None:
    """Verify newly hashed password with current settings does not require rehashing."""
    hashed = hash_password("FreshPassword123!")
    assert needs_rehash(hashed) is False
    assert needs_rehash("") is False


def test_needs_rehash_malformed_and_invalid_hashes() -> None:
    """Verify needs_rehash handles malformed and invalid hash strings returning False."""
    assert needs_rehash("not_a_valid_hash") is False
    assert needs_rehash("$argon2id$v=19$invalid_parameters") is False


def test_needs_rehash_detects_outdated_parameters() -> None:
    """Verify needs_rehash detects when a hash was created with outdated parameters."""
    # Construct a legacy hasher with different time_cost and memory_cost
    outdated_hasher = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    old_hash = outdated_hasher.hash("LegacyPassword123!")
    
    # Current settings require time_cost=3, memory_cost=65536, parallelism=4
    assert needs_rehash(old_hash) is True
