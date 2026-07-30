"""Job domain service managing business logic, field validations, status transitions, and pipeline stage generation."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.jobs.exceptions import (
    InsufficientJobPermissionsError,
    InvalidJobDataError,
    InvalidJobStatusTransitionError,
    JobNotFoundError,
)
from hiron.jobs.models import Job, PipelineStage
from hiron.jobs.repository import JobRepository

logger = structlog.get_logger("hiron.api.jobs.service")

ALLOWED_EMPLOYMENT_TYPES = {"full_time", "part_time", "contract", "internship"}
ALLOWED_JOB_STATUSES = {"draft", "open", "paused", "closed", "archived"}
MANAGEMENT_ROLES = {"org_admin", "recruiter"}

DEFAULT_PIPELINE_STAGES = [
    {"name": "Applied", "position": 1, "is_terminal": False, "stage_type": "active"},
    {"name": "Screening", "position": 2, "is_terminal": False, "stage_type": "active"},
    {"name": "Interview", "position": 3, "is_terminal": False, "stage_type": "active"},
    {"name": "Offer", "position": 4, "is_terminal": False, "stage_type": "active"},
    {"name": "Hired", "position": 5, "is_terminal": True, "stage_type": "hired"},
    {"name": "Rejected", "position": 6, "is_terminal": True, "stage_type": "rejected"},
]


class JobService:
    """Core domain service for Job business logic and orchestration."""

    def __init__(self, job_repo: JobRepository | None = None) -> None:
        """Initialize JobService with injected repository."""
        self.job_repo = job_repo or JobRepository()

    def _validate_role_permission(self, current_user_role: str, action: str) -> None:
        """Verify requesting user has appropriate management role."""
        if current_user_role not in MANAGEMENT_ROLES:
            raise InsufficientJobPermissionsError(f"Only org_admin or recruiter can {action} jobs")

    def _validate_job_fields(
        self,
        title: str | None = None,
        description: str | None = None,
        employment_type: str | None = None,
        experience_years_min: int | None = None,
        experience_years_max: int | None = None,
    ) -> None:
        """Validate job fields against business constraints."""
        if title is not None:
            clean_title = title.strip()
            if not clean_title or len(clean_title) > 200:
                raise InvalidJobDataError("Job title must be between 1 and 200 characters")

        if description is not None:
            clean_desc = description.strip()
            if not clean_desc or len(clean_desc) > 10000:
                raise InvalidJobDataError("Job description must be between 1 and 10,000 characters")

        if employment_type is not None and employment_type not in ALLOWED_EMPLOYMENT_TYPES:
            raise InvalidJobDataError(
                f"Invalid employment type '{employment_type}'. Allowed: {', '.join(sorted(ALLOWED_EMPLOYMENT_TYPES))}"
            )

        if experience_years_min is not None and (
            experience_years_min < 0 or experience_years_min > 50
        ):
            raise InvalidJobDataError("Minimum experience years must be between 0 and 50")

        if experience_years_max is not None and (
            experience_years_max < 0 or experience_years_max > 50
        ):
            raise InvalidJobDataError("Maximum experience years must be between 0 and 50")

        if (
            experience_years_min is not None
            and experience_years_max is not None
            and experience_years_max < experience_years_min
        ):
            raise InvalidJobDataError(
                "Maximum experience years must be greater than or equal to minimum experience years"
            )

    async def create_job(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        created_by: uuid.UUID,
        current_user_role: str,
        title: str,
        description: str,
        department: str | None = None,
        location: str | None = None,
        employment_type: str | None = None,
        experience_years_min: int | None = None,
        experience_years_max: int | None = None,
        required_skills: list[str] | None = None,
        preferred_skills: list[str] | None = None,
        status: str = "draft",
    ) -> Job:
        """Create a new job and auto-generate default pipeline stages per API Contract §JOB-3."""
        self._validate_role_permission(current_user_role, "create")
        self._validate_job_fields(
            title=title,
            description=description,
            employment_type=employment_type,
            experience_years_min=experience_years_min,
            experience_years_max=experience_years_max,
        )

        if status not in ALLOWED_JOB_STATUSES:
            raise InvalidJobDataError(f"Invalid job status '{status}'")

        job = Job(
            tenant_id=tenant_id,
            created_by=created_by,
            title=title.strip(),
            description=description.strip(),
            department=department.strip() if department else None,
            location=location.strip() if location else None,
            employment_type=employment_type,
            experience_years_min=experience_years_min,
            experience_years_max=experience_years_max,
            required_skills=required_skills or [],
            preferred_skills=preferred_skills or [],
            status=status,
            is_archived=False,
            opened_at=datetime.now(UTC) if status == "open" else None,
        )
        created_job = await self.job_repo.create_job(session, job)

        # Generate default pipeline stages
        stages = [
            PipelineStage(
                tenant_id=tenant_id,
                job_id=created_job.id,
                name=cfg["name"],
                position=cfg["position"],
                is_terminal=cfg["is_terminal"],
                stage_type=cfg["stage_type"],
            )
            for cfg in DEFAULT_PIPELINE_STAGES
        ]
        await self.job_repo.create_pipeline_stages(session, stages)

        logger.info(
            "Job created with default pipeline stages",
            job_id=str(created_job.id),
            tenant_id=str(tenant_id),
        )
        return created_job

    async def get_job_by_id(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Job:
        """Fetch job details by ID or raise JobNotFoundError per API Contract §JOB-2."""
        job = await self.job_repo.get_job_by_id(session, job_id, tenant_id)
        if not job:
            raise JobNotFoundError()
        return job

    async def list_jobs(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        status: str | list[str] | None = None,
        department: str | None = None,
        q: str | None = None,
        include_archived: bool = False,
        sort: str = "createdAt:desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Job], int]:
        """List tenant jobs per API Contract §JOB-1."""
        return await self.job_repo.list_jobs(
            session=session,
            tenant_id=tenant_id,
            status=status,
            department=department,
            q=q,
            include_archived=include_archived,
            sort=sort,
            limit=limit,
            offset=offset,
        )

    def _build_update_dictionary(
        self,
        title: str | None,
        description: str | None,
        department: str | None,
        location: str | None,
        employment_type: str | None,
        experience_years_min: int | None,
        experience_years_max: int | None,
        required_skills: list[str] | None,
        preferred_skills: list[str] | None,
    ) -> dict[str, Any]:
        """Construct dictionary of job fields to update."""
        updates: dict[str, Any] = {}
        if title is not None:
            updates["title"] = title.strip()
        if description is not None:
            updates["description"] = description.strip()
        if department is not None:
            updates["department"] = department.strip()
        if location is not None:
            updates["location"] = location.strip()
        if employment_type is not None:
            updates["employment_type"] = employment_type
        if experience_years_min is not None:
            updates["experience_years_min"] = experience_years_min
        if experience_years_max is not None:
            updates["experience_years_max"] = experience_years_max
        if required_skills is not None:
            updates["required_skills"] = required_skills
        if preferred_skills is not None:
            updates["preferred_skills"] = preferred_skills
        return updates

    async def update_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_role: str,
        title: str | None = None,
        description: str | None = None,
        department: str | None = None,
        location: str | None = None,
        employment_type: str | None = None,
        experience_years_min: int | None = None,
        experience_years_max: int | None = None,
        required_skills: list[str] | None = None,
        preferred_skills: list[str] | None = None,
    ) -> Job:
        """Update job attributes per API Contract §JOB-4."""
        self._validate_role_permission(current_user_role, "update")
        target_job = await self.get_job_by_id(session, job_id, tenant_id)

        self._validate_job_fields(
            title=title,
            description=description,
            employment_type=employment_type,
            experience_years_min=experience_years_min
            if experience_years_min is not None
            else target_job.experience_years_min,
            experience_years_max=experience_years_max
            if experience_years_max is not None
            else target_job.experience_years_max,
        )

        updates = self._build_update_dictionary(
            title,
            description,
            department,
            location,
            employment_type,
            experience_years_min,
            experience_years_max,
            required_skills,
            preferred_skills,
        )

        if not updates:
            return target_job

        updated = await self.job_repo.update_job(session, job_id, tenant_id, **updates)
        if not updated:
            raise JobNotFoundError()

        logger.info("Job updated successfully", job_id=str(job_id), tenant_id=str(tenant_id))
        return updated

    async def open_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_role: str,
    ) -> Job:
        """Transition job to 'open' status per API Contract §JOB-6."""
        self._validate_role_permission(current_user_role, "open")
        target_job = await self.get_job_by_id(session, job_id, tenant_id)

        if target_job.status in ("open", "closed", "archived"):
            raise InvalidJobStatusTransitionError(
                f"Cannot open job in status '{target_job.status}'. Must be draft or paused."
            )

        if not target_job.title or not target_job.description:
            raise InvalidJobDataError("Job title and description are required before opening job")

        now = datetime.now(UTC)
        updated = await self.job_repo.update_job(
            session,
            job_id,
            tenant_id,
            status="open",
            opened_at=now if not target_job.opened_at else target_job.opened_at,
        )
        if not updated:
            raise JobNotFoundError()

        logger.info("Job opened successfully", job_id=str(job_id), tenant_id=str(tenant_id))
        return updated

    async def pause_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_role: str,
    ) -> Job:
        """Pause an open job."""
        self._validate_role_permission(current_user_role, "pause")
        target_job = await self.get_job_by_id(session, job_id, tenant_id)

        if target_job.status != "open":
            raise InvalidJobStatusTransitionError(
                f"Cannot pause job in status '{target_job.status}'. Must be open."
            )

        updated = await self.job_repo.update_job(session, job_id, tenant_id, status="paused")
        if not updated:
            raise JobNotFoundError()

        logger.info("Job paused successfully", job_id=str(job_id), tenant_id=str(tenant_id))
        return updated

    async def close_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_role: str,
    ) -> Job:
        """Close job per API Contract §JOB-7."""
        self._validate_role_permission(current_user_role, "close")
        target_job = await self.get_job_by_id(session, job_id, tenant_id)

        if target_job.status == "closed":
            return target_job

        updated = await self.job_repo.update_job(
            session,
            job_id,
            tenant_id,
            status="closed",
            closed_at=datetime.now(UTC),
        )
        if not updated:
            raise JobNotFoundError()

        logger.info("Job closed successfully", job_id=str(job_id), tenant_id=str(tenant_id))
        return updated

    async def archive_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_role: str,
    ) -> Job:
        """Soft-delete / archive job per API Contract §JOB-5."""
        self._validate_role_permission(current_user_role, "archive")
        await self.get_job_by_id(session, job_id, tenant_id)

        updated = await self.job_repo.update_job(
            session,
            job_id,
            tenant_id,
            status="archived",
            is_archived=True,
        )
        if not updated:
            raise JobNotFoundError()

        logger.info("Job archived successfully", job_id=str(job_id), tenant_id=str(tenant_id))
        return updated
