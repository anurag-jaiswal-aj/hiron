"""Unit tests for audit utilities."""

import datetime
import uuid
from decimal import Decimal
from enum import Enum

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

from hiron.audit.utils import extract_model_changes, sanitize_audit_payload, serialize_for_audit

Base = declarative_base()


class DummyEnum(Enum):
    OPEN = "open"
    CLOSED = "closed"


class DummyModel(Base):
    __tablename__ = "dummy"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    status = Column(String)


def test_sanitize_audit_payload():
    """Test recursive redaction of sensitive keys."""
    payload = {
        "public_data": "ok",
        "PASSWORD": "secret_password",
        "nested": {
            "token": "secret_token",
            "api_KEY": "secret_api_key",
            "safe_field": 123,
            "list_of_secrets": [{"refresh_token": "secret_rt"}, {"public": "ok"}],
        },
        "DATABASE_URL": "postgres://secret",
    }

    sanitized = sanitize_audit_payload(payload)

    assert sanitized["public_data"] == "ok"
    assert sanitized["PASSWORD"] == "***REDACTED***"
    assert sanitized["nested"]["token"] == "***REDACTED***"
    assert sanitized["nested"]["api_KEY"] == "***REDACTED***"
    assert sanitized["nested"]["safe_field"] == 123
    assert sanitized["nested"]["list_of_secrets"][0]["refresh_token"] == "***REDACTED***"
    assert sanitized["nested"]["list_of_secrets"][1]["public"] == "ok"
    assert sanitized["DATABASE_URL"] == "***REDACTED***"


def test_serialize_for_audit():
    """Test safe serialization of types."""
    assert serialize_for_audit(None) is None
    
    val_uuid = uuid.uuid4()
    assert serialize_for_audit(val_uuid) == str(val_uuid)
    
    val_dt = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
    assert serialize_for_audit(val_dt) == "2023-01-01T12:00:00+00:00"
    
    assert serialize_for_audit(Decimal("10.5")) == 10.5
    
    assert serialize_for_audit(DummyEnum.OPEN) == "open"
    
    assert serialize_for_audit({"foo": "bar"}) == {"foo": "bar"}
    assert serialize_for_audit([1, 2, 3]) == [1, 2, 3]
    assert serialize_for_audit(42) == 42


def test_extract_model_changes_create():
    """Test extracting changes for a newly created model."""
    instance = DummyModel(id=1, name="Test", status="open")
    
    # Needs to be attached to a session or properly mapped to have state initialized
    # For a detached object, inspect() might not show it as added, but column_attrs are available.
    changes = extract_model_changes(instance, "create")
    assert changes is not None
    assert "after" in changes
    assert changes["after"]["id"] == 1
    assert changes["after"]["name"] == "Test"
    assert changes["after"]["status"] == "open"


def test_extract_model_changes_delete():
    """Test extracting changes for a deleted model."""
    instance = DummyModel(id=1, name="Test", status="open")
    
    changes = extract_model_changes(instance, "delete")
    assert changes is not None
    assert "before" in changes
    assert changes["before"]["id"] == 1
    assert changes["before"]["name"] == "Test"

def test_extract_model_changes_update():
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine
    
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        instance = DummyModel(id=1, name="Test", status="open")
        session.add(instance)
        session.commit()
        
        _ = instance.status # Trigger load
        instance.status = "closed"
        changes = extract_model_changes(instance, "update")
        
        assert changes is not None
        assert changes["before"] == {"status": "open"}
        assert changes["after"] == {"status": "closed"}
