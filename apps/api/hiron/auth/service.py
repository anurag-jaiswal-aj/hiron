"""Authentication service providing core login, credential verification, token issuance, and rotation business logic."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.common.exceptions import HironException
from hiron.core.config import get_settings
from hiron.core.jwt import create_access_token, create_refresh_token, verify_token
from hiron.core.security import verify_password
from hiron.tokens.models import RefreshToken
from hiron.tokens.repository import RefreshTokenRepository
from hiron.users.models import User
from hiron.users.repository import UserRepository

logger = structlog.get_logger("hiron.api.auth.service")


class AuthenticationError(HironException):
    """Raised when authentication credentials (email/password) or refresh tokens are invalid."""

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
    """Application service boundary encapsulating authentication, credential verification, and token lifecycle workflows."""

    def __init__(
        self,
        user_repo: UserRepository | None = None,
        token_repo: RefreshTokenRepository | None = None,
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
            session=session,
            email=email,
            tenant_id=tenant_id,
        )

        if not user:
            logger.info(
                "Authentication failed: user not found", email=email, tenant_id=str(tenant_id)
            )
            raise AuthenticationError()

        if not user.is_active:
            logger.warning("Authentication failed: account is deactivated", user_id=str(user.id))
            raise AccountDisabledError()

        if not user.password_hash:
            # OAuth-only users do not have a password hash (§5.2)
            logger.info(
                "Authentication failed: OAuth-only user has no password set", user_id=str(user.id)
            )
            raise AuthenticationError()

        if not verify_password(password, user.password_hash):
            logger.info("Authentication failed: password mismatch", user_id=str(user.id))
            raise AuthenticationError()

        return user

    async def create_auth_tokens(
        self,
        session: AsyncSession,
        user: User,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str]:
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

        # 1. Create access token (15-min TTL)
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            role=user.role,
        )

        # 2. Create refresh token (7-day TTL)
        token_jti = str(uuid.uuid4())
        raw_refresh_token = create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            jti=token_jti,
        )

        # 3. Compute SHA-256 hash of raw refresh token (§16.1 & Database Design §5.3)
        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

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

        # 6. Commit transaction to persist refresh_token and last_login_at
        await session.commit()

        return access_token, raw_refresh_token

    async def rotate_refresh_token(
        self,
        session: AsyncSession,
        raw_refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str]:
        """Application service method handling single-use refresh token rotation per API Contract §6.1.

        Args:
            session: Active AsyncSession database handle.
            raw_refresh_token: Raw encoded JWT refresh token string.
            user_agent: Optional client browser user agent string.
            ip_address: Optional client IP address string.

        Returns:
            Tuple of (new_access_token_jwt, new_raw_refresh_token_jwt).

        Raises:
            AuthenticationError: On invalid signature, expired, revoked, or non-existent token.
            AccountDisabledError: If user account is deactivated.
        """
        try:
            payload = verify_token(raw_refresh_token, expected_type="refresh")
        except Exception as exc:
            logger.warning("Token refresh failed: invalid or expired JWT", error=str(exc))
            raise AuthenticationError("Invalid or expired refresh token") from exc

        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenantId"])
        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()

        # 1. Fetch token record from database
        stored_token = await self.token_repo.get_by_token_hash(session, token_hash)
        if (
            not stored_token
            or stored_token.is_revoked
            or stored_token.expires_at < datetime.now(UTC)
        ):
            logger.warning(
                "Token refresh failed: token revoked, missing, or expired in DB",
                token_hash=token_hash,
            )
            raise AuthenticationError("Invalid or expired refresh token")

        # 2. Single-use rotation: Revoke old refresh token (§5.3 & §16.1)
        await self.token_repo.revoke_by_token_hash(session, token_hash)

        # 3. Fetch user and verify active status
        user = await self.user_repo.get_by_id_and_tenant(session, user_id, tenant_id)
        if not user:
            raise AuthenticationError("User not found")
        if not user.is_active:
            raise AccountDisabledError()

        # 4. Issue rotated token pair (creates new token & commits session)
        return await self.create_auth_tokens(
            session=session,
            user=user,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def logout(self, session: AsyncSession, raw_refresh_token: str | None) -> None:
        """Application service method executing session revocation for logout per API Contract §6.1.

        Args:
            session: Active AsyncSession database handle.
            raw_refresh_token: Optional raw refresh token string to revoke.
        """
        if raw_refresh_token:
            token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
            await self.token_repo.revoke_by_token_hash(session, token_hash)
            await session.commit()
