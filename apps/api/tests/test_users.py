"""Unit tests verifying User ORM model mapping, foreign keys, indexes, and constraints."""

import pytest
from sqlalchemy import Index

from hiron.common.models import BaseModel
from hiron.users.models import User


def test_user_model_inheritance() -> None:
    """Verify User inherits from BaseModel and contains all required columns per Database Design §5.2."""
    assert issubclass(User, BaseModel)
    assert hasattr(User, "id")
    assert hasattr(User, "tenant_id")
    assert hasattr(User, "email")
    assert hasattr(User, "full_name")
    assert hasattr(User, "password_hash")
    assert hasattr(User, "role")
    assert hasattr(User, "avatar_url")
    assert hasattr(User, "is_active")
    assert hasattr(User, "is_email_verified")
    assert hasattr(User, "last_login_at")
    assert hasattr(User, "created_at")
    assert hasattr(User, "updated_at")


def test_user_tablename() -> None:
    """Verify table name matches Database Design §5.2."""
    assert User.__tablename__ == "users"


def test_user_foreign_key_definition() -> None:
    """Verify foreign key references tenants.id with ON DELETE CASCADE per Database Design §5.2 & §7."""
    foreign_keys = list(User.__table__.foreign_keys)
    assert len(foreign_keys) == 1
    
    fk = foreign_keys[0]
    assert fk.name == "fk_users_tenant_id_tenants"
    assert fk.target_fullname == "tenants.id"
    assert fk.ondelete == "CASCADE"


def test_user_indexes_definition() -> None:
    """Verify required indexes are defined on User table per Database Design §5.2."""
    index_names = [idx.name for idx in User.__table__.indexes]
    assert "ix_users_tenant_id" in index_names
    assert "ix_users_tenant_id_email" in index_names
    assert "ix_users_tenant_id_role" in index_names


def test_user_constraints_definition() -> None:
    """Verify unique and check constraints defined on User table per Database Design §5.2."""
    constraints = User.__table_args__
    constraint_names = [getattr(c, "name", None) for c in constraints if hasattr(c, "name")]
    
    assert "uq_users_tenant_id_email" in constraint_names
    assert "ck_users_role" in constraint_names
    assert "ck_users_email_format" in constraint_names
