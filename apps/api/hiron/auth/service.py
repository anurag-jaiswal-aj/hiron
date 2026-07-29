"""Authentication service providing core login, credential verification, and token issuance business logic."""

from datetime import datetime, timedelta, timezone
import hashlib
from typing import Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from hiron.common.exceptions import HironException
from hiron.core.config import get_settings
from hiron.core.jwt import create_access_token, create_refresh_token
from hiron.core.security import verify_password
from hiron.tokens.models import RefreshToken
from hiron.tokens.repository import RefreshTokenRepository
from hiron.users.models import User
from hiron.users.repository import UserRepository

logger = structlog.get_logger("hiron.api.auth.service")


class AuthenticationError(HironException):
    """Raised when authentication credentials (email/password) are invalid or missing."""

    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(
            message=message,
            code="INVALID_CREDENTIALS",
            status_code=401,
        )


class AccountDisabledError(HironException):
    """Raised when an account is soft-deactivated."""

    def __init__(self, message: str = "Account is deactivated") -> None:
        super().__init__(
            message=message,
            code="ACCOUNT_DISABLED",
            status_code=403,
        )


class AuthService:
    """Core authentication business logic service."""

    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        token_repo: Optional[RefreshTokenRepository] = None,
    ) -> None:
        """Initialize AuthService with injected repositories."""
        self.user_repo = user_repo or UserRepository()
        self.token_repo = token_repo or RefreshTokenRepository()

    async def authenticate_user(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        tenant_id: uuid.UUID,
    ) -> User:
        """Authenticate user by email, password, and tenant_id per API Contract & Engineering Guidelines.

        Args:
            session: Active AsyncSession database handle.
            email: Candidate user email string.
            password: Candidate plain text password.
            tenant_id: Target tenant UUID context.

        Returns:
            Authenticated User entity.

        Raises:
            AuthenticationError: On wrong email, missing password hash (OAuth user), or password mismatch.
            AccountDisabledError: If user account is deactivated (is_active = False).
        """
        user = await self.user_repo.get_by_email_and_tenant(
            session=session, email=email, tenant_id=tenant_id
        )

        if not user:
            logger.info("Authentication failed: user not found", email=email, tenant_id=str(tenant_id))
            raise AuthenticationError()

        if not user.is_active:
            logger.warning("Authentication failed: account is deactivated", user_id=str(user.id))
            raise AccountDisabledError()

        if not user.password_hash:
            # OAuth-only users do not have a password hash (§5.2)
            logger.info("Authentication failed: OAuth-only user has no password set", user_id=str(user.id))
            raise AuthenticationError()

        if not verify_password(password, user.password_hash):
            logger.info("Authentication failed: password mismatch", user_id=str(user.id))
            raise AuthenticationError()

        return user

    async def create_auth_tokens(
        self,
        session: AsyncSession,
        user: User,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Issue access token and persisted refresh token for an authenticated user.

        Args:
            session: Active AsyncSession database handle.
            user: Authenticated User entity.
            user_agent: Optional client browser user agent string.
            ip_address: Optional client IP address string.

        Returns:
            Tuple of (access_token_jwt, raw_refresh_token_jwt).
        """
        settings = get_settings()

        # 1. Create access token (configured minutes TTL per Engineering Guidelines §16.1)
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            role=user.role,
        )

        # 2. Create refresh token (configured days TTL per Engineering Guidelines §16.1)
        token_jti = str(uuid.uuid4())
        raw_refresh_token = create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            jti=token_jti,
        )

        # 3. Compute SHA-256 hash of raw refresh token (§16.1 & Database Design §5.3)
        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

        # 4. Create and persist RefreshToken entity
        refresh_token_entity = RefreshToken(
            user_id=user.id,
            tenant_id=user.tenant_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.token_repo.create(session=session, token=refresh_token_entity)

        # 5. Update user last_login_at timestamp via Repository boundary (§5.2)
        await self.user_repo.update_last_login(session=session, user_id=user.id)

        return access_token, raw_refresh_token
