"""Unit tests for opaque cursor encoding and decoding utilities."""

import pytest

from hiron.common.exceptions import ValidationException
from hiron.common.pagination import decode_cursor, encode_cursor


def test_encode_and_decode_cursor_roundtrip() -> None:
    """Verify encoding a payload and decoding it produces the exact dictionary."""
    payload = {"offset": 20, "id": "550e8400-e29b-41d4-a716-446655440000"}
    cursor = encode_cursor(payload)

    assert isinstance(cursor, str)
    assert len(cursor) > 0

    decoded = decode_cursor(cursor)
    assert decoded == payload


def test_decode_cursor_invalid_string_raises_validation_exception() -> None:
    """Verify invalid base64 or non-JSON strings raise ValidationException."""
    with pytest.raises(ValidationException, match="Invalid pagination cursor"):
        decode_cursor("not_valid_base64_json!!!")


def test_decode_cursor_empty_string_raises_validation_exception() -> None:
    """Verify empty cursor string raises ValidationException."""
    with pytest.raises(ValidationException, match="cannot be empty"):
        decode_cursor("")
