"""Thin FastAPI router for Candidate Tags per API Contract §TAG-1..3."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.tags.schemas import AddTagRequest, TagListResponse, TagResponse
from hiron.tags.service import TagService
from hiron.users.models import User

router = APIRouter(tags=["Candidate Tags"])


def get_tag_service() -> TagService:
    """Dependency provider for TagService."""
    return TagService()


@router.get(
    "/candidates/{candidate_id}/tags",
    response_model=TagListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Tags for Candidate (TAG-1)",
)
async def list_candidate_tags_endpoint(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: TagService = Depends(get_tag_service),
) -> TagListResponse:
    """Get all tags attached to a candidate per §TAG-1."""
    return await service.list_candidate_tags(
        session=session,
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
    )


@router.post(
    "/candidates/{candidate_id}/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Tag (TAG-2)",
)
async def add_tag_endpoint(
    candidate_id: uuid.UUID,
    request: AddTagRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: TagService = Depends(get_tag_service),
) -> TagResponse:
    """Add a normalized tag to a candidate per §TAG-2 (returns 409 Conflict if duplicate)."""
    return await service.add_tag(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        candidate_id=candidate_id,
        tag_name=request.tag_name,
    )


@router.delete(
    "/candidates/{candidate_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Tag (TAG-3)",
)
async def remove_tag_endpoint(
    candidate_id: uuid.UUID,
    tag_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: TagService = Depends(get_tag_service),
) -> None:
    """Remove a tag from a candidate per §TAG-3."""
    await service.remove_tag(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        candidate_id=candidate_id,
        tag_id=tag_id,
    )
