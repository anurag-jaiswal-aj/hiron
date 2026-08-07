"""FastAPI API Router exposing Job endpoints per API Contract §7."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.common.schemas import PaginationMeta, ResponseEnvelope
from hiron.core.database import get_db_session
from hiron.jobs.models import Job
from hiron.jobs.repository import JobRepository
from hiron.jobs.schemas import (
    JobCloseRequest,
    JobCreateRequest,
    JobCreatorResponse,
    JobListItemResponse,
    JobListResponse,
    JobResponse,
    JobUpdateRequest,
    PipelineStageCreateRequest,
    PipelineStageResponse,
    PipelineStagesReorderRequest,
    PipelineStageUpdateRequest,
)
from hiron.jobs.service import JobService
from hiron.users.models import User

router = APIRouter(tags=["Jobs"])


def get_job_service() -> JobService:
    """Dependency provider for JobService instance."""
    return JobService(job_repo=JobRepository())


def _to_job_response(job: Job) -> JobResponse:
    """Convert Job ORM model entity into JobResponse DTO."""
    creator_resp = None
    if job.creator:
        creator_resp = JobCreatorResponse(
            id=job.creator.id,
            full_name=job.creator.full_name,
        )

    stages_resp = [
        PipelineStageResponse(
            id=stage.id,
            name=stage.name,
            position=stage.position,
            is_terminal=stage.is_terminal,
            stage_type=stage.stage_type,
            candidate_count=0,
        )
        for stage in getattr(job, "pipeline_stages", [])
    ]

    return JobResponse(
        id=job.id,
        title=job.title,
        description=job.description,
        department=job.department,
        location=job.location,
        employment_type=job.employment_type,
        experience_years_min=job.experience_years_min,
        experience_years_max=job.experience_years_max,
        required_skills=job.required_skills or [],
        preferred_skills=job.preferred_skills or [],
        extracted_requirements=job.extracted_requirements,
        status=job.status,
        is_archived=bool(job.is_archived) if job.is_archived is not None else False,
        candidate_count=0,
        pipeline_stages=stages_resp,
        created_by=creator_resp,
        opened_at=job.opened_at,
        closed_at=job.closed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("", response_model=ResponseEnvelope[JobListResponse])
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
    status: Annotated[str | None, Query(description="Filter status (comma-separated)")] = None,
    department: Annotated[str | None, Query(description="Filter department")] = None,
    q: Annotated[str | None, Query(description="Full-text search query")] = None,
    sort: Annotated[str, Query(description="Sort field and direction")] = "createdAt:desc",
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset cursor")] = 0,
    cursor: Annotated[str | None, Query(description="Opaque pagination cursor")] = None,
) -> ResponseEnvelope[JobListResponse]:
    """List organization jobs with optional filtering, search, sorting, and cursor pagination per §JOB-1."""
    jobs, total_count, next_cursor = await job_service.list_jobs(
        session=session,
        tenant_id=current_user.tenant_id,
        status=status,
        department=department,
        q=q,
        include_archived=False,
        sort=sort,
        limit=limit,
        offset=offset,
        cursor=cursor,
    )

    items = [
        JobListItemResponse(
            id=j.id,
            title=j.title,
            department=j.department,
            location=j.location,
            status=j.status,
            employment_type=j.employment_type,
            candidate_count=0,
            opened_at=j.opened_at,
            created_at=j.created_at,
        )
        for j in jobs
    ]

    return ResponseEnvelope(
        data=JobListResponse(
            data=items,
            pagination=PaginationMeta(
                has_more=next_cursor is not None,
                next_cursor=next_cursor,
                total_count=total_count,
            ),
        )
    )


@router.get("/{job_id}", response_model=ResponseEnvelope[JobResponse])
async def get_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> ResponseEnvelope[JobResponse]:
    """Fetch detailed job information including pipeline stages per §JOB-2."""
    job = await job_service.get_job_by_id(
        session=session,
        job_id=job_id,
        tenant_id=current_user.tenant_id,
    )
    return ResponseEnvelope(data=_to_job_response(job))


@router.post("", response_model=ResponseEnvelope[JobResponse], status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> ResponseEnvelope[JobResponse]:
    """Create a new job and auto-generate default pipeline stages per §JOB-3."""
    created = await job_service.create_job(
        session=session,
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        current_user_role=current_user.role,
        title=payload.title,
        description=payload.description,
        department=payload.department,
        location=payload.location,
        employment_type=payload.employment_type,
        experience_years_min=payload.experience_years_min,
        experience_years_max=payload.experience_years_max,
        required_skills=payload.required_skills,
        preferred_skills=payload.preferred_skills,
    )

    # Re-fetch with loaded relationships
    job = await job_service.get_job_by_id(session, created.id, current_user.tenant_id)
    return ResponseEnvelope(data=_to_job_response(job))


@router.patch("/{job_id}", response_model=ResponseEnvelope[JobResponse])
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> ResponseEnvelope[JobResponse]:
    """Update existing job attributes per §JOB-4."""
    updated = await job_service.update_job(
        session=session,
        job_id=job_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
        title=payload.title,
        description=payload.description,
        department=payload.department,
        location=payload.location,
        employment_type=payload.employment_type,
        experience_years_min=payload.experience_years_min,
        experience_years_max=payload.experience_years_max,
        required_skills=payload.required_skills,
        preferred_skills=payload.preferred_skills,
    )
    job = await job_service.get_job_by_id(session, updated.id, current_user.tenant_id)
    return ResponseEnvelope(data=_to_job_response(job))


@router.post("/{job_id}/open", response_model=ResponseEnvelope[JobResponse])
async def open_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> ResponseEnvelope[JobResponse]:
    """Transition job to open status per §JOB-6."""
    updated = await job_service.open_job(
        session=session,
        job_id=job_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
    )
    job = await job_service.get_job_by_id(session, updated.id, current_user.tenant_id)
    return ResponseEnvelope(data=_to_job_response(job))


@router.post("/{job_id}/pause", response_model=ResponseEnvelope[JobResponse])
async def pause_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> ResponseEnvelope[JobResponse]:
    """Pause an open job."""
    updated = await job_service.pause_job(
        session=session,
        job_id=job_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
    )
    job = await job_service.get_job_by_id(session, updated.id, current_user.tenant_id)
    return ResponseEnvelope(data=_to_job_response(job))


@router.post("/{job_id}/close", response_model=ResponseEnvelope[JobResponse])
async def close_job(
    job_id: uuid.UUID,
    _payload: JobCloseRequest | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,  # type: ignore[assignment]
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
    job_service: Annotated[JobService, Depends(get_job_service)] = None,  # type: ignore[assignment]
) -> ResponseEnvelope[JobResponse]:
    """Close job per §JOB-7."""
    updated = await job_service.close_job(
        session=session,
        job_id=job_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
    )
    job = await job_service.get_job_by_id(session, updated.id, current_user.tenant_id)
    return ResponseEnvelope(data=_to_job_response(job))


@router.post("/{job_id}/archive", response_model=ResponseEnvelope[JobResponse])
async def archive_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> ResponseEnvelope[JobResponse]:
    """Soft-delete / archive job per §JOB-5."""
    updated = await job_service.archive_job(
        session=session,
        job_id=job_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
    )
    job = await job_service.get_job_by_id(session, updated.id, current_user.tenant_id)
    return ResponseEnvelope(data=_to_job_response(job))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> None:
    """Hard-delete job entity."""
    await job_service.job_repo.delete_job(
        session=session,
        job_id=job_id,
        tenant_id=current_user.tenant_id,
    )


# ------------------------------------------------------------------------------
# Pipeline Stage Endpoints (§Phase 3.4)
# ------------------------------------------------------------------------------


@router.get("/{job_id}/stages", response_model=ResponseEnvelope[list[PipelineStageResponse]])
async def list_job_pipeline_stages(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> ResponseEnvelope[list[PipelineStageResponse]]:
    """List pipeline stages for a job."""
    stages = await job_service.list_pipeline_stages(
        session=session,
        job_id=job_id,
        tenant_id=current_user.tenant_id,
    )
    res = [
        PipelineStageResponse(
            id=s.id,
            name=s.name,
            position=s.position,
            is_terminal=s.is_terminal,
            stage_type=s.stage_type,
            candidate_count=0,
        )
        for s in stages
    ]
    return ResponseEnvelope(data=res)


@router.post(
    "/{job_id}/stages",
    response_model=ResponseEnvelope[PipelineStageResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_job_pipeline_stage(
    job_id: uuid.UUID,
    payload: PipelineStageCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> ResponseEnvelope[PipelineStageResponse]:
    """Create a new custom pipeline stage for a job."""
    stage = await job_service.create_pipeline_stage(
        session=session,
        job_id=job_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
        name=payload.name,
        position=payload.position,
        is_terminal=payload.is_terminal,
        stage_type=payload.stage_type,
    )
    return ResponseEnvelope(
        data=PipelineStageResponse(
            id=stage.id,
            name=stage.name,
            position=stage.position,
            is_terminal=stage.is_terminal,
            stage_type=stage.stage_type,
            candidate_count=0,
        )
    )


@router.patch("/{job_id}/stages/{stage_id}", response_model=ResponseEnvelope[PipelineStageResponse])
async def update_job_pipeline_stage(
    job_id: uuid.UUID,
    stage_id: uuid.UUID,
    payload: PipelineStageUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> ResponseEnvelope[PipelineStageResponse]:
    """Update pipeline stage attributes."""
    stage = await job_service.update_pipeline_stage(
        session=session,
        job_id=job_id,
        stage_id=stage_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
        name=payload.name,
        position=payload.position,
        is_terminal=payload.is_terminal,
        stage_type=payload.stage_type,
    )
    return ResponseEnvelope(
        data=PipelineStageResponse(
            id=stage.id,
            name=stage.name,
            position=stage.position,
            is_terminal=stage.is_terminal,
            stage_type=stage.stage_type,
            candidate_count=0,
        )
    )


@router.delete("/{job_id}/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_pipeline_stage(
    job_id: uuid.UUID,
    stage_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> None:
    """Delete custom pipeline stage."""
    await job_service.delete_pipeline_stage(
        session=session,
        job_id=job_id,
        stage_id=stage_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
    )


@router.put(
    "/{job_id}/stages/reorder", response_model=ResponseEnvelope[list[PipelineStageResponse]]
)
async def reorder_job_pipeline_stages(
    job_id: uuid.UUID,
    payload: PipelineStagesReorderRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> ResponseEnvelope[list[PipelineStageResponse]]:
    """Reorder pipeline stages for a job."""
    stage_orders = [
        {"stage_id": item.stage_id, "position": item.position} for item in payload.stages
    ]
    stages = await job_service.reorder_pipeline_stages(
        session=session,
        job_id=job_id,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
        stage_orders=stage_orders,
    )
    res = [
        PipelineStageResponse(
            id=s.id,
            name=s.name,
            position=s.position,
            is_terminal=s.is_terminal,
            stage_type=s.stage_type,
            candidate_count=0,
        )
        for s in stages
    ]
    return ResponseEnvelope(data=res)
