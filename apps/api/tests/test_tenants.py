"""Unit tests verifying Tenant ORM model mapping and constraint definitions."""

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint

from hiron.common.models import BaseModel
from hiron.tenants.models import Tenant


def test_tenant_model_inheritance() -> None:
    """Verify Tenant inherits from BaseModel and contains all required columns per Database Design §5.1."""
    assert issubclass(Tenant, BaseModel)
    assert hasattr(Tenant, "id")
    assert hasattr(Tenant, "name")
    assert hasattr(Tenant, "slug")
    assert hasattr(Tenant, "plan")
    assert hasattr(Tenant, "settings")
    assert hasattr(Tenant, "is_active")
    assert hasattr(Tenant, "created_at")
    assert hasattr(Tenant, "updated_at")


def test_tenant_tablename() -> None:
    """Verify table name matches Database Design §5.1."""
    assert Tenant.__tablename__ == "tenants"


def test_tenant_constraints() -> None:
    """Verify unique and check constraints defined on Tenant table."""
    constraints = Tenant.__table_args__
    constraint_names = [getattr(c, "name", None) for c in constraints if hasattr(c, "name")]
    
    assert "uq_tenants_slug" in constraint_names
    assert "ck_tenants_plan" in constraint_names
    assert "ck_tenants_slug_format" in constraint_names
