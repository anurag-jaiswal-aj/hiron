"""Utilities for generating and sanitizing audit logs."""

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import inspect

# Case-insensitive secret keywords for redaction
REDACTION_KEYS = {
    "password",
    "hashed_password",
    "password_hash",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "cookie",
    "jwt",
    "private_key",
    "secret",
    "client_secret",
    "api_key",
    "database_url",
}


def sanitize_audit_payload(payload: Any) -> Any:
    """Recursively redact sensitive keys from dictionary payloads."""
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            k_lower = str(k).lower()
            # Exact match is safer to avoid redacting lists named "list_of_secrets"
            if k_lower in REDACTION_KEYS:
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = sanitize_audit_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_audit_payload(item) for item in payload]
    return payload


def serialize_for_audit(val: Any) -> Any:
    """Safely convert common Python/SQLAlchemy types to JSON-serializable primitives."""
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, Enum):
        return val.value
    # Assume primitives like str, int, bool, float, or already dict/list are fine
    return val


def extract_model_changes(instance: Any, operation: str) -> dict[str, Any] | None:
    """Extract before/after state from a SQLAlchemy model instance before flush.
    
    Args:
        instance: The SQLAlchemy model object.
        operation: 'create', 'update', or 'delete'.
        
    Returns:
        dict with 'before' and/or 'after' keys containing serialized states.
    """
    state = inspect(instance)
    if not state:
        return None

    changes: dict[str, Any] = {}

    if operation == "create":
        after = {}
        for attr in state.mapper.column_attrs:
            val = getattr(instance, attr.key, None)
            after[attr.key] = serialize_for_audit(val)
        changes["after"] = after

    elif operation == "delete":
        before = {}
        for attr in state.mapper.column_attrs:
            # For delete, we capture the current state
            val = getattr(instance, attr.key, None)
            before[attr.key] = serialize_for_audit(val)
        changes["before"] = before

    elif operation == "update":
        before = {}
        after = {}
        for attr in state.attrs:
            # We only want column changes, not relationship changes
            if attr.key not in state.mapper.column_attrs.keys():
                continue
            history = attr.history
            if history.has_changes():
                old_val = history.deleted[0] if history.deleted else None
                new_val = history.added[0] if history.added else getattr(instance, attr.key, None)
                
                before[attr.key] = serialize_for_audit(old_val)
                after[attr.key] = serialize_for_audit(new_val)
        
        if before or after:
            changes["before"] = before
            changes["after"] = after
        else:
            return None # No changes to columns

    return changes
