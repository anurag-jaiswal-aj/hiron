"""FastAPI Thin API router for Candidate Management per API Contract §CAND-1 through §CAND-6."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.candidates.schemas import (
    AddCandidateToJobRequest,
    CandidateAssociatedJobResponse,
    CandidateCreateRequest,
    CandidateListItemResponse,
    CandidateListResponse,
    CandidateResponse,
    CandidateUpdateRequest,
    JobCandidateResponse,
    StageSummaryResponse,
)
from hiron.candidates.service import CandidateService
from hiron.common.schemas import PaginationMeta, ResponseEnvelope
from hiron.core.database import get_db_session
from hiron.users.models import User

router = APIRouter(tags=["candidates"])
jobs_candidate_router = APIRouter(tags=["candidates"])


def get_candidate_service() -> CandidateService:
    """Dependency provider for CandidateService instance."""
    return CandidateService()


@router.get("", response_model=ResponseEnvelope[CandidateListResponse])
async def list_candidates(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    candidate_service: Annotated[CandidateService, Depends(get_candidate_service)],
    q: Annotated[str | None, Query(description="Full-text search query")] = None,
    skills: Annotated[str | None, Query(description="Comma-separated skills filter")] = None,
    location: Annotated[str | None, Query(description="Location filter")] = None,
    experience_min: Annotated[
        int | None, Query(alias="experienceMin", ge=0, description="Min experience years")
    ] = None,
    experience_max: Annotated[
        int | None, Query(alias="experienceMax", ge=0, description="Max experience years")
    ] = None,
    source: Annotated[str | None, Query(description="Candidate source filter")] = None,
    tag: Annotated[str | None, Query(description="Filter by tag name")] = None,
    sort: Annotated[str, Query(description="Sort field and direction")] = "createdAt:desc",
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset cursor")] = 0,
    cursor: Annotated[str | None, Query(description="Opaque pagination cursor")] = None,
) -> ResponseEnvelope[CandidateListResponse]:
    """List tenant candidates per API Contract §CAND-1."""
    candidates, total_count, next_cursor = await candidate_service.list_candidates(
        session=session,
        tenant_id=current_user.tenant_id,
        q=q,
        skills=skills,
        location=location,
        experience_min=experience_min,
        experience_max=experience_max,
        source=source,
        tag=tag,
        sort=sort,
        limit=limit,
        offset=offset,
        cursor=cursor,
    )

    items = [
        CandidateListItemResponse(
            id=c.id,
            full_name=c.full_name,
            email=c.email,
            current_title=c.current_title,
            current_company=c.current_company,
            location=c.location,
            total_experience_years=c.total_experience_years,
            skills=c.skills or [],
            source=c.source or "upload",
            is_archived=bool(c.is_archived),
            created_at=c.created_at,
        )
        for c in candidates
    ]

    return ResponseEnvelope(
        data=CandidateListResponse(
            data=items,
            pagination=PaginationMeta(
                has_more=next_cursor is not None,
                next_cursor=next_cursor,
                total_count=total_count,
            ),
        )
    )


@router.post(
    "", response_model=ResponseEnvelope[CandidateResponse], status_code=status.HTTP_201_CREATED
)
async def create_candidate(
    body: CandidateCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    candidate_service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> ResponseEnvelope[CandidateResponse]:
    """Create candidate profile manually per API Contract §CAND-3."""
    candidate = await candidate_service.create_candidate(
        session=session,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        location=body.location,
        linkedin_url=body.linkedin_url,
        summary=body.summary,
        current_title=body.current_title,
        current_company=body.current_company,
        skills=body.skills,
        total_experience_years=body.total_experience_years,
        source=body.source,
    )

    return ResponseEnvelope(
        data=CandidateResponse(
            id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            phone=candidate.phone,
            location=candidate.location,
            linkedin_url=candidate.linkedin_url,
            summary=candidate.summary,
            skills=candidate.skills or [],
            total_experience_years=candidate.total_experience_years,
            current_title=candidate.current_title,
            current_company=candidate.current_company,
            source=candidate.source or "upload",
            is_archived=candidate.is_archived,
            jobs=[],
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )
    )


@router.get("/{candidate_id}", response_model=ResponseEnvelope[CandidateResponse])
async def get_candidate(
    candidate_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    candidate_service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> ResponseEnvelope[CandidateResponse]:
    """Get full candidate profile including job associations per API Contract §CAND-2."""
    candidate = await candidate_service.get_candidate_by_id(
        session=session,
        candidate_id=candidate_id,
        tenant_id=current_user.tenant_id,
    )

    jobs = [
        CandidateAssociatedJobResponse(
            job_id=ja.job_id,
            job_title=ja.job.title if ja.job else "Unknown Job",
            current_stage=ja.current_stage.name if ja.current_stage else "Applied",
            is_shortlisted=ja.is_shortlisted,
        )
        for ja in candidate.job_associations
        if not ja.is_archived
    ]

    return ResponseEnvelope(
        data=CandidateResponse(
            id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            phone=candidate.phone,
            location=candidate.location,
            linkedin_url=candidate.linkedin_url,
            summary=candidate.summary,
            skills=candidate.skills or [],
            total_experience_years=candidate.total_experience_years,
            current_title=candidate.current_title,
            current_company=candidate.current_company,
            source=candidate.source or "upload",
            is_archived=candidate.is_archived,
            jobs=jobs,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )
    )


@router.patch("/{candidate_id}", response_model=ResponseEnvelope[CandidateResponse])
async def update_candidate(
    candidate_id: uuid.UUID,
    body: CandidateUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    candidate_service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> ResponseEnvelope[CandidateResponse]:
    """Update candidate profile fields per API Contract §CAND-4."""
    candidate = await candidate_service.update_candidate(
        session=session,
        candidate_id=candidate_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        location=body.location,
        linkedin_url=body.linkedin_url,
        summary=body.summary,
        current_title=body.current_title,
        current_company=body.current_company,
        skills=body.skills,
        total_experience_years=body.total_experience_years,
    )

    jobs = [
        CandidateAssociatedJobResponse(
            job_id=ja.job_id,
            job_title=ja.job.title if ja.job else "Unknown Job",
            current_stage=ja.current_stage.name if ja.current_stage else "Applied",
            is_shortlisted=ja.is_shortlisted,
        )
        for ja in candidate.job_associations
        if not ja.is_archived
    ]

    return ResponseEnvelope(
        data=CandidateResponse(
            id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            phone=candidate.phone,
            location=candidate.location,
            linkedin_url=candidate.linkedin_url,
            summary=candidate.summary,
            skills=candidate.skills or [],
            total_experience_years=candidate.total_experience_years,
            current_title=candidate.current_title,
            current_company=candidate.current_company,
            source=candidate.source or "upload",
            is_archived=candidate.is_archived,
            jobs=jobs,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )
    )


@router.post("/{candidate_id}/archive", response_model=ResponseEnvelope[CandidateResponse])
async def archive_candidate(
    candidate_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    candidate_service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> ResponseEnvelope[CandidateResponse]:
    """Soft-delete a candidate profile per API Contract §CAND-5."""
    candidate = await candidate_service.archive_candidate(
        session=session,
        candidate_id=candidate_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
    )

    return ResponseEnvelope(
        data=CandidateResponse(
            id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            phone=candidate.phone,
            location=candidate.location,
            linkedin_url=candidate.linkedin_url,
            summary=candidate.summary,
            skills=candidate.skills or [],
            total_experience_years=candidate.total_experience_years,
            current_title=candidate.current_title,
            current_company=candidate.current_company,
            source=candidate.source or "upload",
            is_archived=candidate.is_archived,
            jobs=[],
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )
    )


@jobs_candidate_router.post(
    "/{job_id}/candidates",
    response_model=ResponseEnvelope[JobCandidateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_candidate_to_job(
    job_id: uuid.UUID,
    body: AddCandidateToJobRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    candidate_service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> ResponseEnvelope[JobCandidateResponse]:
    """Associate a candidate with a job and place in initial pipeline stage per API Contract §CAND-6."""
    job_candidate = await candidate_service.add_candidate_to_job(
        session=session,
        job_id=job_id,
        candidate_id=body.candidate_id,
        tenant_id=current_user.tenant_id,
        added_by_user_id=current_user.id,
        current_user_role=current_user.role,
    )

    stage_summary = StageSummaryResponse(
        id=job_candidate.current_stage.id,
        name=job_candidate.current_stage.name,
        position=job_candidate.current_stage.position,
    )

    return ResponseEnvelope(
        data=JobCandidateResponse(
            id=job_candidate.id,
            job_id=job_candidate.job_id,
            candidate_id=job_candidate.candidate_id,
            current_stage=stage_summary,
            is_shortlisted=job_candidate.is_shortlisted,
            created_at=job_candidate.created_at,
        )
    )
