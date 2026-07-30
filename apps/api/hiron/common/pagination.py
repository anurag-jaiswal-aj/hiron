"""Opaque Base64 cursor encoding and decoding utilities per API Contract §9."""

import base64
import json
from typing import Any

from hiron.common.exceptions import ValidationException


def encode_cursor(payload: dict[str, Any]) -> str:
    """Encode dictionary payload into a URL-safe Base64 opaque cursor string."""
    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("utf-8")


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode a URL-safe Base64 opaque cursor string into a payload dictionary."""
    if not cursor or not cursor.strip():
        raise ValidationException("Pagination cursor cannot be empty")

    try:
        json_bytes = base64.urlsafe_b64decode(cursor.strip().encode("utf-8"))
        payload = json.loads(json_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValidationException("Invalid pagination cursor format")
        return payload
    except Exception as exc:
        raise ValidationException("Invalid pagination cursor provided") from exc
