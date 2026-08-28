"""Tests for password reset backend foundation."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.models import PasswordResetToken
from hiron.auth.service import AuthService, AuthenticationError, AccountDisabledError
from hiron.users.models import User
from hiron.core.security import verify_password


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService(
        user_repo=AsyncMock(),
        token_repo=AsyncMock(),
        reset_token_repo=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_generate_password_reset_token_success(auth_service: AuthService) -> None:
    session = AsyncMock(spec=AsyncSession)
    user = User(id=uuid.uuid4(), email="test@example.com", is_active=True, tenant_id=uuid.uuid4())
    auth_service.user_repo.get_by_email_and_tenant.return_value = user  # type: ignore

    token = await auth_service.generate_password_reset_token(session, user.email, user.tenant_id)
    assert token is not None
    assert len(token) >= 32
    auth_service.reset_token_repo.create.assert_called_once()  # type: ignore
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_generate_password_reset_token_not_found(auth_service: AuthService) -> None:
    session = AsyncMock(spec=AsyncSession)
    auth_service.user_repo.get_by_email_and_tenant.return_value = None  # type: ignore

    token = await auth_service.generate_password_reset_token(session, "notfound@example.com", uuid.uuid4())
    assert token is None
    auth_service.reset_token_repo.create.assert_not_called()  # type: ignore


@pytest.mark.asyncio
async def test_reset_password_success(auth_service: AuthService) -> None:
    session = AsyncMock(spec=AsyncSession)
    user = User(id=uuid.uuid4(), is_active=True, tenant_id=uuid.uuid4(), password_hash="old")
    stored_token = PasswordResetToken(user_id=user.id, used_at=None, expires_at=datetime.now(UTC) + timedelta(minutes=10))
    
    auth_service.reset_token_repo.get_by_token_hash.return_value = stored_token  # type: ignore
    auth_service.reset_token_repo.mark_used.return_value = True  # type: ignore
    session.get.return_value = user
    
    await auth_service.reset_password(session, "raw_token", "NewStrongPassword123!")
    
    assert verify_password("NewStrongPassword123!", user.password_hash or "")
    auth_service.token_repo.revoke_all_for_user.assert_called_once_with(session, user.id)  # type: ignore
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_expired(auth_service: AuthService) -> None:
    session = AsyncMock(spec=AsyncSession)
    stored_token = PasswordResetToken(user_id=uuid.uuid4(), used_at=None, expires_at=datetime.now(UTC) - timedelta(minutes=10))
    auth_service.reset_token_repo.get_by_token_hash.return_value = stored_token  # type: ignore
    
    with pytest.raises(AuthenticationError):
        await auth_service.reset_password(session, "raw_token", "new_pass")


@pytest.mark.asyncio
async def test_reset_password_used(auth_service: AuthService) -> None:
    session = AsyncMock(spec=AsyncSession)
    stored_token = PasswordResetToken(user_id=uuid.uuid4(), used_at=datetime.now(UTC), expires_at=datetime.now(UTC) + timedelta(minutes=10))
    auth_service.reset_token_repo.get_by_token_hash.return_value = stored_token  # type: ignore
    
    with pytest.raises(AuthenticationError):
        await auth_service.reset_password(session, "raw_token", "new_pass")
