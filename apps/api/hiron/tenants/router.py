"""FastAPI tenant router implementing CRUD endpoints per API Contract & Engineering Guidelines."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user, require_role
from hiron.common.schemas import ResponseEnvelope
from hiron.users.models import User
from hiron.core.database import get_db_session
from hiron.tenants.schemas import TenantCreateRequest, TenantResponse, TenantUpdateRequest
from hiron.tenants.service import TenantService

router = APIRouter()


def get_tenant_service() -> TenantService:
    """Dependency provider for TenantService."""
    return TenantService()


@router.post(
    "",
    response_model=ResponseEnvelope[TenantResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create tenant organization",
    dependencies=[Depends(require_role("org_admin"))],
)
async def create_tenant(
    request_data: TenantCreateRequest,
    current_user: Annotated[User, Depends(require_role("org_admin"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> ResponseEnvelope[TenantResponse]:
    """Create a new tenant organization. Requires org_admin role."""
    tenant = await tenant_service.create_tenant(
        session=db,
        user_id=current_user.id,
        name=request_data.name,
        slug=request_data.slug,
        plan=request_data.plan,
        settings=request_data.settings,
    )
    return ResponseEnvelope(data=TenantResponse.model_validate(tenant))


@router.get(
    "",
    response_model=ResponseEnvelope[list[TenantResponse]],
    status_code=status.HTTP_200_OK,
    summary="List active tenants",
    dependencies=[Depends(require_role("org_admin"))],
)
async def list_tenants(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
    offset: Annotated[int | None, Query(ge=0)] = None,
) -> ResponseEnvelope[list[TenantResponse]]:
    """List active tenant organizations. Requires org_admin role."""
    tenants = await tenant_service.list_active_tenants(session=db, limit=limit, offset=offset)
    return ResponseEnvelope(data=[TenantResponse.model_validate(t) for t in tenants])


@router.get(
    "/{tenant_id}",
    response_model=ResponseEnvelope[TenantResponse],
    status_code=status.HTTP_200_OK,
    summary="Get tenant by ID",
    dependencies=[Depends(get_current_user)],
)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> ResponseEnvelope[TenantResponse]:
    """Fetch tenant details by ID. Requires authentication."""
    tenant = await tenant_service.get_tenant_by_id(session=db, tenant_id=tenant_id)
    return ResponseEnvelope(data=TenantResponse.model_validate(tenant))


@router.patch(
    "/{tenant_id}",
    response_model=ResponseEnvelope[TenantResponse],
    status_code=status.HTTP_200_OK,
    summary="Update tenant organization",
    dependencies=[Depends(require_role("org_admin"))],
)
async def update_tenant(
    tenant_id: uuid.UUID,
    request_data: TenantUpdateRequest,
    current_user: Annotated[User, Depends(require_role("org_admin"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> ResponseEnvelope[TenantResponse]:
    """Update tenant organization attributes. Requires org_admin role."""
    tenant = await tenant_service.update_tenant(
        session=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        name=request_data.name,
        slug=request_data.slug,
        plan=request_data.plan,
        settings=request_data.settings,
        is_active=request_data.is_active,
    )
    return ResponseEnvelope(data=TenantResponse.model_validate(tenant))


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant organization",
    dependencies=[Depends(require_role("org_admin"))],
)
async def delete_tenant(
    tenant_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("org_admin"))],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> None:
    """Hard-delete tenant organization. Requires org_admin role."""
    await tenant_service.delete_tenant(session=db, tenant_id=tenant_id, user_id=current_user.id)
    return
