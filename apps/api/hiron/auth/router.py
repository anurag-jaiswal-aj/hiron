"""FastAPI authentication router implementing login, refresh, and logout endpoints per API Contract §6.1."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.auth.schemas import LoginData, LoginRequest, RefreshTokenData, UserAuthPayload
from hiron.auth.service import AuthService
from hiron.common.exceptions import ValidationException
from hiron.common.schemas import ResponseEnvelope
from hiron.core.config import get_settings
from hiron.core.database import get_db_session
from hiron.users.models import User

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

