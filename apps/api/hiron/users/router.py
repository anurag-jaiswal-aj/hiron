"""FastAPI user management router implementing CRUD endpoints per API Contract & Engineering Guidelines."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user, require_role
from hiron.common.schemas import ResponseEnvelope
from hiron.core.database import get_db_session
from hiron.users.models import User
from hiron.users.schemas import UserCreateRequest, UserResponse, UserUpdateRequest
from hiron.users.service import UserService

router = APIRouter()


def get_user_service() -> UserService:
    """Dependency provider for UserService."""
    return UserService()


@router.get(
    "",
    response_model=ResponseEnvelope[list[UserResponse]],
    status_code=status.HTTP_200_OK,
    summary="List users in organization",
    dependencies=[Depends(get_current_user)],
)
async def list_users(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    role: Annotated[str | None, Query(description="Filter by user role")] = None,
    is_active: Annotated[
        bool | None, Query(alias="isActive", description="Filter active/deactivated users")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> ResponseEnvelope[list[UserResponse]]:
    """List all users in the authenticated user's organization per API Contract §USER-1."""
    users, _total = await user_service.list_users(
        session=db,
        tenant_id=current_user.tenant_id,
        role=role,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return ResponseEnvelope(data=[UserResponse.model_validate(u) for u in users])


@router.get(
    "/{user_id}",
    response_model=ResponseEnvelope[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user profile by ID",
    dependencies=[Depends(get_current_user)],
)
async def get_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ResponseEnvelope[UserResponse]:
    """Fetch specific user profile within the authenticated tenant per API Contract §USER-2."""
    user = await user_service.get_user_by_id(
        session=db,
        user_id=user_id,
        tenant_id=current_user.tenant_id,
    )
    return ResponseEnvelope(data=UserResponse.model_validate(user))


@router.post(
    "",
    response_model=ResponseEnvelope[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create or invite new user",
    dependencies=[Depends(require_role("org_admin"))],
)
@router.post(
    "/invite",
    response_model=ResponseEnvelope[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Invite new user to tenant",
    dependencies=[Depends(require_role("org_admin"))],
)
async def create_user(
    request_data: UserCreateRequest,
    current_user: Annotated[User, Depends(require_role("org_admin"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ResponseEnvelope[UserResponse]:
    """Create/invite a new user to the organization per API Contract §USER-3. Requires org_admin role."""
    user = await user_service.create_user(
        session=db,
        tenant_id=current_user.tenant_id,
        email=request_data.email,
        full_name=request_data.full_name,
        role=request_data.role,
        password=request_data.password,
    )
    return ResponseEnvelope(data=UserResponse.model_validate(user))


@router.patch(
    "/{user_id}",
    response_model=ResponseEnvelope[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update user profile or role",
    dependencies=[Depends(get_current_user)],
)
async def update_user(
    user_id: uuid.UUID,
    request_data: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ResponseEnvelope[UserResponse]:
    """Update user profile or role per API Contract §USER-4."""
    user = await user_service.update_user(
        session=db,
        user_id=user_id,
        tenant_id=current_user.tenant_id,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
        full_name=request_data.full_name,
        role=request_data.role,
        is_active=request_data.is_active,
    )
    return ResponseEnvelope(data=UserResponse.model_validate(user))


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user from organization",
    dependencies=[Depends(require_role("org_admin"))],
)
async def delete_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("org_admin"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    """Delete a user from the organization. Requires org_admin role."""
    await user_service.delete_user(
        session=db,
        user_id=user_id,
        tenant_id=current_user.tenant_id,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )


@router.post(
    "/{user_id}/deactivate",
    response_model=ResponseEnvelope[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Deactivate user (soft delete)",
    dependencies=[Depends(require_role("org_admin"))],
)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("org_admin"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ResponseEnvelope[UserResponse]:
    """Deactivate a user and revoke all active refresh tokens per API Contract §USER-5. Requires org_admin role."""
    user = await user_service.deactivate_user(
        session=db,
        user_id=user_id,
        tenant_id=current_user.tenant_id,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )
    return ResponseEnvelope(data=UserResponse.model_validate(user))


@router.post(
    "/{user_id}/reactivate",
    response_model=ResponseEnvelope[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Reactivate user",
    dependencies=[Depends(require_role("org_admin"))],
)
async def reactivate_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("org_admin"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ResponseEnvelope[UserResponse]:
    """Reactivate a previously deactivated user per API Contract §USER-6. Requires org_admin role."""
    user = await user_service.reactivate_user(
        session=db,
        user_id=user_id,
        tenant_id=current_user.tenant_id,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )
    return ResponseEnvelope(data=UserResponse.model_validate(user))
