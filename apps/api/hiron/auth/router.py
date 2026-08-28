"""FastAPI authentication router implementing login, refresh, and logout endpoints per API Contract §6.1."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.auth.schemas import (
    LoginData,
    LoginRequest,
    RefreshTokenData,
    UserAuthPayload,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageData,
)
from hiron.auth.service import AuthService
from hiron.common.exceptions import ValidationException
from hiron.common.schemas import ResponseEnvelope
from hiron.core.cache import app_cache
from hiron.core.config import get_settings
from hiron.core.database import get_db_session
from hiron.users.models import User
from hiron.common.exceptions import RateLimitExceededException
from hiron.core.qstash_client import qstash_publisher
import time

router = APIRouter()


def get_auth_service() -> AuthService:
    """Dependency provider for AuthService application boundary."""
    return AuthService()


@router.post(
    "/login",
    response_model=ResponseEnvelope[LoginData],
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue tokens",
)
async def login(
    request_data: LoginRequest,
    response: Response,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ResponseEnvelope[LoginData]:
    """Authenticate user with email/password and issue JWT access token + httpOnly refresh token cookie per API Contract §6.1."""
    settings = get_settings()

    user = await auth_service.authenticate_user(
        session=db,
        email=request_data.email,
        password=request_data.password,
        tenant_id=request_data.tenant_id,
    )

    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    access_token, raw_refresh_token = await auth_service.create_auth_tokens(
        session=db,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Manage session cookie
    response.set_cookie(
        key="refreshToken",
        value=raw_refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )

    login_data = LoginData(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserAuthPayload.model_validate(user),
    )
    return ResponseEnvelope(data=login_data)


@router.post(
    "/refresh",
    response_model=ResponseEnvelope[RefreshTokenData],
    status_code=status.HTTP_200_OK,
    summary="Exchange refresh token for rotated token pair",
)
async def refresh_token(
    response: Response,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refreshToken: Annotated[str | None, Cookie()] = None,
) -> ResponseEnvelope[RefreshTokenData]:
    """Exchange valid httpOnly refresh token for a rotated access token + refresh token pair per API Contract §6.1."""
    if not refreshToken:
        raise ValidationException("Missing required refreshToken cookie")

    settings = get_settings()
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    new_access_token, new_raw_refresh_token = await auth_service.rotate_refresh_token(
        session=db,
        raw_refresh_token=refreshToken,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Manage rotated session cookie
    response.set_cookie(
        key="refreshToken",
        value=new_raw_refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )

    refresh_data = RefreshTokenData(
        access_token=new_access_token,
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )
    return ResponseEnvelope(data=refresh_data)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke refresh token and clear session cookie",
)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refreshToken: Annotated[str | None, Cookie()] = None,
) -> None:
    """Revoke active refresh token and delete session cookie per API Contract §6.1."""
    await auth_service.logout(session=db, raw_refresh_token=refreshToken)
    response.delete_cookie(key="refreshToken", path="/api/v1/auth")
    return


@router.get(
    "/me",
    response_model=ResponseEnvelope[UserAuthPayload],
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[UserAuthPayload]:
    """Return currently authenticated user profile per API Contract §AUTH-4."""
    return ResponseEnvelope(data=UserAuthPayload.model_validate(current_user))


@router.post(
    "/forgot-password",
    response_model=ResponseEnvelope[MessageData],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a password reset link",
)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ResponseEnvelope[MessageData]:
    """Request a password reset token for the given email and tenant."""
    import structlog
    logger = structlog.get_logger("hiron.api.auth.router")
    settings = get_settings()

    # Account-level rate limiting
    normalized_email = request_data.email.lower().strip()
    window_duration = 900  # 15 minutes
    window_time = int(time.time() / window_duration)
    email_key = f"rate_limit:forgot_pwd:email:{normalized_email}:{window_time}"

    redis_client = app_cache._get_redis()
    pipe = redis_client.pipeline()
    pipe.incr(email_key)
    pipe.expire(email_key, window_duration)
    try:
        result = await pipe.execute()
        if result[0] > 5:
            raise RateLimitExceededException()
    except Exception as e:
        if isinstance(e, RateLimitExceededException):
            raise
        # Log failure but allow request if Redis fails, to prevent outages
        # RateLimitMiddleware does the same.
        logger.error("Account rate limiter failed", error=str(e))

    # Publish webhook payload instead of synchronous token generation
    if not settings.qstash_webhook_url:
        logger.error("qstash_webhook_url is required to publish password reset emails")
        raise HTTPException(status_code=500, detail="QStash webhook URL not configured")

    payload = {"email": normalized_email, "tenant_id": str(request_data.tenant_id)}

    webhook_url = (
        f"{settings.qstash_webhook_url.rstrip('/')}/api/v1/webhooks/qstash/auth/forgot-password"
    )
    try:
        await qstash_publisher.publish(
            url=webhook_url,
            payload=payload,
            deduplication_id=f"forgot-password-{normalized_email}-{window_time}",
        )
    except Exception as e:
        logger.error("Failed to publish forgot password webhook", error=str(e))
        # Depending on convention, we return 500 if we cannot publish to QStash
        raise HTTPException(status_code=500, detail="Failed to enqueue forgot password request") from e

    return ResponseEnvelope(
        data=MessageData(
            message="If an account exists for that email, a password reset link has been sent."
        )
    )


@router.post(
    "/reset-password",
    response_model=ResponseEnvelope[MessageData],
    status_code=status.HTTP_200_OK,
    summary="Reset password using a valid token",
)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ResponseEnvelope[MessageData]:
    """Validate reset token and update password."""
    await auth_service.reset_password(
        session=db,
        token=request_data.token,
        new_password=request_data.new_password,
    )

    return ResponseEnvelope(
        data=MessageData(
            message="Password has been reset successfully. Please log in with your new password."
        )
    )
