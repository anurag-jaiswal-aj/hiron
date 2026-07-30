"""Thin FastAPI router for Search domain per API Contract §CAND-7 & §SEARCH-1..4."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.search.schemas import (
    SavedSearchCreateRequest,
    SavedSearchListResponse,
    SavedSearchResponse,
    SavedSearchUpdateRequest,
    SemanticSearchCandidatesRequest,
    SemanticSearchCandidatesResponse,
)
from hiron.search.service import SearchService
from hiron.users.models import User

router = APIRouter(tags=["Semantic Search"])


def get_search_service() -> SearchService:
    """Dependency provider for SearchService."""
    return SearchService()


@router.post(
    "/search/candidates",
    response_model=SemanticSearchCandidatesResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Search Candidates (CAND-7)",
)
async def search_candidates_endpoint(
    request: SemanticSearchCandidatesRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: SearchService = Depends(get_search_service),
) -> SemanticSearchCandidatesResponse:
    """Execute semantic (natural language) search across candidate pool per API Contract §CAND-7."""
    return await service.search_candidates(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        query=request.query,
        filters=request.filters,
        limit=request.limit,
    )


@router.post(
    "/search/jobs/{job_id}/candidates",
    response_model=SemanticSearchCandidatesResponse,
    status_code=status.HTTP_200_OK,
    summary="Search Candidates by Job",
)
async def search_candidates_by_job_endpoint(
    job_id: uuid.UUID,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: SearchService = Depends(get_search_service),
) -> SemanticSearchCandidatesResponse:
    """Search candidates matching a job description via vector similarity."""
    return await service.search_candidates_by_job(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        job_id=job_id,
        limit=limit,
    )


@router.get(
    "/saved-searches",
    response_model=SavedSearchListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Saved Searches (SEARCH-1)",
)
async def list_saved_searches_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: SearchService = Depends(get_search_service),
) -> SavedSearchListResponse:
    """List saved search queries for current user and shared team searches per API Contract §SEARCH-1."""
    return await service.list_saved_searches(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.post(
    "/saved-searches",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Saved Search (SEARCH-2)",
)
async def create_saved_search_endpoint(
    request: SavedSearchCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: SearchService = Depends(get_search_service),
) -> SavedSearchResponse:
    """Save a semantic search query for reuse per API Contract §SEARCH-2."""
    return await service.create_saved_search(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        name=request.name,
        query_text=request.query_text,
        filters=request.filters,
        is_shared=request.is_shared,
    )


@router.patch(
    "/saved-searches/{search_id}",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Saved Search (SEARCH-3)",
)
async def update_saved_search_endpoint(
    search_id: uuid.UUID,
    request: SavedSearchUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: SearchService = Depends(get_search_service),
) -> SavedSearchResponse:
    """Update existing saved search per API Contract §SEARCH-3."""
    return await service.update_saved_search(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        search_id=search_id,
        name=request.name,
        query_text=request.query_text,
        filters=request.filters,
        is_shared=request.is_shared,
    )


@router.delete(
    "/saved-searches/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Saved Search (SEARCH-4)",
)
async def delete_saved_search_endpoint(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: SearchService = Depends(get_search_service),
) -> None:
    """Delete saved search per API Contract §SEARCH-4."""
    await service.delete_saved_search(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        search_id=search_id,
    )
