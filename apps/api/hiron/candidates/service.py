"""Candidate service encapsulating business rules, validations, and domain logic per Engineering Guidelines §5."""

import uuid
from collections.abc import Sequence
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.candidates.exceptions import (
    CandidateNotFoundError,
    DuplicateCandidateEmailError,
    InsufficientCandidatePermissionsError,
    InvalidCandidateDataError,
    JobCandidateConflictError,
)
from hiron.candidates.models import Candidate, JobCandidate
from hiron.candidates.repository import CandidateRepository
from hiron.jobs.exceptions import JobNotFoundError
from hiron.jobs.repository import JobRepository

logger = structlog.get_logger(__name__)

MANAGEMENT_ROLES = {"org_admin", "recruiter"}
ALLOWED_CANDIDATE_SOURCES = {"upload", "bulk_upload", "api", "ats_sync"}
ALLOWED_CANDIDATE_SORT_FIELDS = {"fullName", "createdAt", "totalExperienceYears", "currentTitle"}


class CandidateService:
    """Business logic for Candidate Management module."""

    def __init__(
        self,
        candidate_repo: CandidateRepository | None = None,
        job_repo: JobRepository | None = None,
    ) -> None:
        self.candidate_repo = candidate_repo or CandidateRepository()
        self.job_repo = job_repo or JobRepository()

    def _validate_role_permission(self, current_user_role: str, action: str) -> None:
        """Verify requesting user has appropriate management role."""
        if current_user_role not in MANAGEMENT_ROLES:
            raise InsufficientCandidatePermissionsError(
                f"Only org_admin or recruiter can {action} candidates"
            )

    def _validate_basic_fields(
        self,
        full_name: str | None,
        email: str | None,
        source: str | None,
    ) -> None:
        """Validate name, email, and source."""
        if full_name is not None:
            clean_name = full_name.strip()
            if not clean_name or len(clean_name) > 200:
                raise InvalidCandidateDataError(
                    "Candidate full name must be between 1 and 200 characters"
                )

        if email is not None and email.strip():
            clean_email = email.strip()
            if len(clean_email) > 320:
                raise InvalidCandidateDataError("Candidate email cannot exceed 320 characters")

        if source is not None and source not in ALLOWED_CANDIDATE_SOURCES:
            raise InvalidCandidateDataError(
                f"Invalid candidate source '{source}'. Allowed: {', '.join(sorted(ALLOWED_CANDIDATE_SOURCES))}"
            )

    def _validate_skills_and_experience(
        self,
        skills: list[str] | None,
        total_experience_years: int | None,
    ) -> None:
        """Validate skills list bounds and experience years."""
        if skills is not None:
            if len(skills) > 50:
                raise InvalidCandidateDataError("Skills list cannot exceed 50 items")
            for skill in skills:
                clean_skill = skill.strip()
                if not clean_skill or len(clean_skill) > 100:
                    raise InvalidCandidateDataError(
                        "Individual skill name must be between 1 and 100 characters"
                    )

        if total_experience_years is not None and (
            total_experience_years < 0 or total_experience_years > 70
        ):
            raise InvalidCandidateDataError("Total experience years must be between 0 and 70")

    def _validate_candidate_fields(
        self,
        full_name: str | None = None,
        email: str | None = None,
        skills: list[str] | None = None,
        total_experience_years: int | None = None,
        source: str | None = None,
    ) -> None:
        """Validate candidate attributes against business domain constraints."""
        self._validate_basic_fields(full_name, email, source)
        self._validate_skills_and_experience(skills, total_experience_years)

    def _validate_sort_parameter(self, sort: str) -> None:
        """Validate sort query string against allowed sortable fields."""
        if not sort or not sort.strip():
            return
        sort_parts = [s.strip() for s in sort.split(",") if s.strip()]
        if len(sort_parts) > 2:
            raise InvalidCandidateDataError("Maximum 2 sort fields allowed per request")
        for part in sort_parts:
            field_dir = part.split(":")
            field_name = field_dir[0].strip()
            if field_name not in ALLOWED_CANDIDATE_SORT_FIELDS:
                raise InvalidCandidateDataError(
                    f"Invalid sort field '{field_name}'. Allowed fields: {', '.join(sorted(ALLOWED_CANDIDATE_SORT_FIELDS))}"
                )
            if len(field_dir) > 1:
                direction = field_dir[1].strip().lower()
                if direction not in ("asc", "desc"):
                    raise InvalidCandidateDataError(f"Invalid sort direction '{direction}'")

    async def create_candidate(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        current_user_role: str,
        full_name: str,
        email: str | None = None,
        phone: str | None = None,
        location: str | None = None,
        linkedin_url: str | None = None,
        summary: str | None = None,
        current_title: str | None = None,
        current_company: str | None = None,
        skills: list[str] | None = None,
        total_experience_years: int | None = None,
        source: str = "upload",
    ) -> Candidate:
        """Create a candidate profile per API Contract §CAND-3."""
        self._validate_role_permission(current_user_role, "create")
        self._validate_candidate_fields(
            full_name=full_name,
            email=email,
            skills=skills,
            total_experience_years=total_experience_years,
            source=source,
        )

        clean_email = email.strip().lower() if email and email.strip() else None
        if clean_email:
            existing = await self.candidate_repo.get_candidate_by_email(
                session, clean_email, tenant_id
            )
            if existing:
                raise DuplicateCandidateEmailError()

        candidate = Candidate(
            tenant_id=tenant_id,
            email=clean_email,
            full_name=full_name.strip(),
            phone=phone.strip() if phone else None,
            location=location.strip() if location else None,
            linkedin_url=linkedin_url.strip() if linkedin_url else None,
            summary=summary.strip() if summary else None,
            current_title=current_title.strip() if current_title else None,
            current_company=current_company.strip() if current_company else None,
            skills=[s.strip() for s in (skills or []) if s.strip()],
            total_experience_years=total_experience_years,
            source=source,
            is_archived=False,
        )
        created_candidate = await self.candidate_repo.create_candidate(session, candidate)

        logger.info(
            "Candidate profile created",
            candidate_id=str(created_candidate.id),
            tenant_id=str(tenant_id),
            action="candidate_created",
        )
        await session.commit()
        return created_candidate

    async def get_candidate_by_id(
        self,
        session: AsyncSession,
        candidate_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Candidate:
        """Fetch candidate details by ID per API Contract §CAND-2."""
        candidate = await self.candidate_repo.get_candidate_by_id(session, candidate_id, tenant_id)
        if not candidate:
            raise CandidateNotFoundError()
        return candidate

    async def list_candidates(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        q: str | None = None,
        skills: list[str] | str | None = None,
        location: str | None = None,
        experience_min: int | None = None,
        experience_max: int | None = None,
        source: str | None = None,
        tag: str | None = None,
        sort: str = "createdAt:desc",
        limit: int = 20,
        offset: int = 0,
        cursor: str | None = None,
    ) -> tuple[Sequence[Candidate], int | None, str | None]:
        """List tenant candidates per API Contract §CAND-1."""
        self._validate_sort_parameter(sort)

        parsed_skills: list[str] | None = None
        if isinstance(skills, str):
            parsed_skills = [s.strip() for s in skills.split(",") if s.strip()]
        elif isinstance(skills, list):
            parsed_skills = [s.strip() for s in skills if s.strip()]

        computed_offset = offset
        compute_total = cursor is None

        if cursor:
            from hiron.common.pagination import decode_cursor

            payload = decode_cursor(cursor)
            computed_offset = int(payload.get("offset", 0))

        effective_limit = min(limit, 100)

        candidates, total_count = await self.candidate_repo.list_candidates(
            session=session,
            tenant_id=tenant_id,
            q=q,
            skills=parsed_skills,
            location=location,
            experience_min=experience_min,
            experience_max=experience_max,
            source=source,
            tag=tag,
            include_archived=False,
            sort=sort,
            limit=effective_limit,
            offset=computed_offset,
            compute_total=compute_total,
        )

        has_more = len(candidates) == effective_limit
        next_cursor = None
        if has_more:
            from hiron.common.pagination import encode_cursor

            next_cursor = encode_cursor({"offset": computed_offset + effective_limit})

        return candidates, total_count if compute_total else None, next_cursor

    def _build_update_dict(
        self,
        full_name: str | None,
        phone: str | None,
        location: str | None,
        linkedin_url: str | None,
        summary: str | None,
        current_title: str | None,
        current_company: str | None,
        skills: list[str] | None,
        total_experience_years: int | None,
    ) -> dict[str, Any]:
        """Construct field updates dictionary."""
        updates: dict[str, Any] = {}
        if full_name is not None:
            updates["full_name"] = full_name.strip()
        if phone is not None:
            updates["phone"] = phone.strip()
        if location is not None:
            updates["location"] = location.strip()
        if linkedin_url is not None:
            updates["linkedin_url"] = linkedin_url.strip()
        if summary is not None:
            updates["summary"] = summary.strip()
        if current_title is not None:
            updates["current_title"] = current_title.strip()
        if current_company is not None:
            updates["current_company"] = current_company.strip()
        if skills is not None:
            updates["skills"] = [s.strip() for s in skills if s.strip()]
        if total_experience_years is not None:
            updates["total_experience_years"] = total_experience_years
        return updates

    async def update_candidate(
        self,
        session: AsyncSession,
        candidate_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_role: str,
        full_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        location: str | None = None,
        linkedin_url: str | None = None,
        summary: str | None = None,
        current_title: str | None = None,
        current_company: str | None = None,
        skills: list[str] | None = None,
        total_experience_years: int | None = None,
    ) -> Candidate:
        """Update candidate details per API Contract §CAND-4."""
        self._validate_role_permission(current_user_role, "update")
        target_candidate = await self.get_candidate_by_id(session, candidate_id, tenant_id)

        self._validate_candidate_fields(
            full_name=full_name,
            email=email,
            skills=skills,
            total_experience_years=total_experience_years,
        )

        updates = self._build_update_dict(
            full_name,
            phone,
            location,
            linkedin_url,
            summary,
            current_title,
            current_company,
            skills,
            total_experience_years,
        )

        if email is not None and email.strip().lower() != (target_candidate.email or "").lower():
            clean_email = email.strip().lower()
            existing = await self.candidate_repo.get_candidate_by_email(
                session, clean_email, tenant_id
            )
            if existing and existing.id != candidate_id:
                raise DuplicateCandidateEmailError()
            updates["email"] = clean_email

        updated_candidate = await self.candidate_repo.update_candidate(
            session=session,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            updates=updates,
        )
        if not updated_candidate:
            raise CandidateNotFoundError()

        logger.info(
            "Candidate profile updated",
            candidate_id=str(candidate_id),
            tenant_id=str(tenant_id),
            action="candidate_updated",
        )
        await session.commit()
        return updated_candidate

    async def archive_candidate(
        self,
        session: AsyncSession,
        candidate_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user_role: str,
    ) -> Candidate:
        """Soft delete candidate per API Contract §CAND-5."""
        self._validate_role_permission(current_user_role, "archive")
        await self.get_candidate_by_id(session, candidate_id, tenant_id)

        archived = await self.candidate_repo.archive_candidate(session, candidate_id, tenant_id)
        if not archived:
            raise CandidateNotFoundError()

        logger.info(
            "Candidate archived",
            candidate_id=str(candidate_id),
            tenant_id=str(tenant_id),
            action="candidate_archived",
        )
        await session.commit()
        return archived

    async def add_candidate_to_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        tenant_id: uuid.UUID,
        added_by_user_id: uuid.UUID | None = None,
        current_user_role: str = "recruiter",
    ) -> JobCandidate:
        """Associate candidate with job and place in initial pipeline stage per API Contract §CAND-6."""
        self._validate_role_permission(current_user_role, "assign")

        # 1. Verify candidate exists in tenant
        await self.get_candidate_by_id(session, candidate_id, tenant_id)

        # 2. Verify job exists in tenant
        job = await self.job_repo.get_job_by_id(session, job_id, tenant_id)
        if not job:
            raise JobNotFoundError()

        # 3. Check for existing candidate-job association
        existing = await self.candidate_repo.get_job_candidate(
            session, job_id, candidate_id, tenant_id
        )
        if existing:
            raise JobCandidateConflictError()

        # 4. Get initial pipeline stage (position == 1 or first stage)
        stages = await self.job_repo.list_pipeline_stages(session, job_id, tenant_id)
        if not stages:
            raise InvalidCandidateDataError("Target job has no configured pipeline stages")

        initial_stage = min(stages, key=lambda s: s.position)

        job_candidate = JobCandidate(
            tenant_id=tenant_id,
            job_id=job_id,
            candidate_id=candidate_id,
            current_stage_id=initial_stage.id,
            added_by=added_by_user_id,
            is_shortlisted=False,
            is_archived=False,
        )
        result = await self.candidate_repo.add_candidate_to_job(session, job_candidate)

        logger.info(
            "Candidate added to job",
            job_id=str(job_id),
            candidate_id=str(candidate_id),
            tenant_id=str(tenant_id),
            action="candidate_added_to_job",
        )
        await session.commit()
        return result
