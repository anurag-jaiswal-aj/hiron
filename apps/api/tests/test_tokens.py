"""Unit tests verifying RefreshToken ORM model mapping, foreign keys, indexes, and constraints."""

from hiron.common.models import BaseModel
from hiron.tokens.models import RefreshToken


def test_refresh_token_model_inheritance() -> None:
    """Verify RefreshToken inherits from BaseModel and contains all required columns per Database Design §5.3."""
    assert issubclass(RefreshToken, BaseModel)
    assert hasattr(RefreshToken, "id")
    assert hasattr(RefreshToken, "user_id")
    assert hasattr(RefreshToken, "tenant_id")
    assert hasattr(RefreshToken, "token_hash")
    assert hasattr(RefreshToken, "expires_at")
    assert hasattr(RefreshToken, "is_revoked")
    assert hasattr(RefreshToken, "user_agent")
    assert hasattr(RefreshToken, "ip_address")
    assert hasattr(RefreshToken, "created_at")
    assert hasattr(RefreshToken, "updated_at")


def test_refresh_token_tablename() -> None:
    """Verify table name matches Database Design §5.3."""
    assert RefreshToken.__tablename__ == "refresh_tokens"


def test_refresh_token_foreign_keys_definition() -> None:
    """Verify foreign keys reference users.id and tenants.id with ON DELETE CASCADE per Database Design §5.3."""
    fk_targets = {
        fk.name: (fk.target_fullname, fk.ondelete) for fk in RefreshToken.__table__.foreign_keys
    }

    assert "fk_refresh_tokens_user_id_users" in fk_targets
    assert fk_targets["fk_refresh_tokens_user_id_users"] == ("users.id", "CASCADE")

    assert "fk_refresh_tokens_tenant_id_tenants" in fk_targets
    assert fk_targets["fk_refresh_tokens_tenant_id_tenants"] == ("tenants.id", "CASCADE")


def test_refresh_token_indexes_definition() -> None:
    """Verify required indexes are defined on RefreshToken table per Database Design §5.3."""
    index_names = [idx.name for idx in RefreshToken.__table__.indexes]
    assert "ix_refresh_tokens_token_hash" in index_names
    assert "ix_refresh_tokens_user_id" in index_names
    assert "ix_refresh_tokens_expires_at" in index_names


def test_refresh_token_constraints_definition() -> None:
    """Verify unique constraint defined on RefreshToken table per Database Design §5.3."""
    constraints = RefreshToken.__table_args__
    constraint_names = [getattr(c, "name", None) for c in constraints if hasattr(c, "name")]

    assert "uq_refresh_tokens_token_hash" in constraint_names
