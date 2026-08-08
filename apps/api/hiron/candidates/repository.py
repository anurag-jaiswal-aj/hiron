"""Candidate repository responsible ONLY for database persistence per Engineering Guidelines §6."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hiron.candidates.models import Candidate, JobCandidate


class CandidateRepository:
    """Data access layer for Candidate entity and JobCandidate junction table."""

    async def create_candidate(
        self,
        session: AsyncSession,
        candidate: Candidate,
    ) -> Candidate:
        """Persist a new Candidate record."""
        session.add(candidate)
        await session.flush()
        await session.refresh(candidate)
        return candidate

    async def get_candidate_by_id(
        self,
        session: AsyncSession,
        candidate_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Candidate | None:
        """Fetch candidate by ID ensuring tenant isolation, loading job associations."""
        stmt = (
            select(Candidate)
            .where(
                Candidate.id == candidate_id,
                Candidate.tenant_id == tenant_id,
            )
            .options(
                selectinload(Candidate.job_associations).selectinload(JobCandidate.job),
                selectinload(Candidate.job_associations).selectinload(JobCandidate.current_stage),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_candidate_by_email(
        self,
        session: AsyncSession,
        email: str,
        tenant_id: uuid.UUID,
    ) -> Candidate | None:
        """Lookup candidate by email within a tenant for duplicate detection."""
        stmt = select(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.email == email.strip().lower(),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    def _build_candidate_field_filters(
        self,
        tenant_id: uuid.UUID,
        location: str | None,
        experience_min: int | None,
        experience_max: int | None,
        source: str | None,
        include_archived: bool,
    ) -> list[ColumnElement[bool]]:
        """Construct scalar field filters."""
        filters: list[ColumnElement[bool]] = [Candidate.tenant_id == tenant_id]
        if not include_archived:
            filters.append(Candidate.is_archived == False)  # noqa: E712
        if source:
            filters.append(Candidate.source == source)
        if location:
            filters.append(Candidate.location.ilike(f"%{location.strip()}%"))
        if experience_min is not None:
            filters.append(Candidate.total_experience_years >= experience_min)
        if experience_max is not None:
            filters.append(Candidate.total_experience_years <= experience_max)
        return filters

    def _build_candidate_search_and_skills_filters(
        self,
        session: AsyncSession,
        q: str | None,
        skills: list[str] | None,
    ) -> list[ColumnElement[bool]]:
        """Construct full-text search and JSONB skills containment filters."""
        filters: list[ColumnElement[bool]] = []
        if skills:
            for skill in skills:
                clean_skill = skill.strip()
                if clean_skill:
                    if session.bind and getattr(session.bind.dialect, "name", None) == "postgresql":
                        from sqlalchemy.dialects.postgresql import JSONB
                        filters.append(Candidate.skills.contains(literal([clean_skill], type_=JSONB)))
                    else:
                        filters.append(Candidate.skills.cast(func.text).ilike(f"%{clean_skill}%"))

        if q and q.strip():
            clean_q = q.strip()
            if session.bind and session.bind.dialect.name == "postgresql":
                filters.append(
                    Candidate.search_vector.op("@@")(func.websearch_to_tsquery("english", clean_q))
                )
            else:
                filters.append(
                    or_(
                        Candidate.full_name.ilike(f"%{clean_q}%"),
                        Candidate.current_title.ilike(f"%{clean_q}%"),
                        Candidate.current_company.ilike(f"%{clean_q}%"),
                    )
                )
        return filters

    def _build_candidate_filters(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        q: str | None,
        skills: list[str] | None,
        location: str | None,
        experience_min: int | None,
        experience_max: int | None,
        source: str | None,
        include_archived: bool,
    ) -> list[ColumnElement[bool]]:
        """Construct WHERE filter expressions for candidate listing."""
        filters = self._build_candidate_field_filters(
            tenant_id, location, experience_min, experience_max, source, include_archived
        )
        filters.extend(self._build_candidate_search_and_skills_filters(session, q, skills))
        return filters

    def _build_candidate_order_by(self, sort: str) -> list[Any]:
        """Construct ORDER BY clauses from sort parameter."""
        order_clauses: list[Any] = []
        sort_parts = [s.strip() for s in sort.split(",") if s.strip()]
        column_map: dict[str, Any] = {
            "fullName": Candidate.full_name,
            "createdAt": Candidate.created_at,
            "totalExperienceYears": Candidate.total_experience_years,
            "currentTitle": Candidate.current_title,
        }
        for part in sort_parts:
            field_dir = part.split(":")
            field_name = field_dir[0].strip()
            direction = field_dir[1].strip().lower() if len(field_dir) > 1 else "desc"
            col: Any = column_map.get(field_name, Candidate.created_at)
            order_clauses.append(col.asc() if direction == "asc" else col.desc())

        if not order_clauses:
            order_clauses.append(Candidate.created_at.desc())

        return order_clauses

    async def list_candidates(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        q: str | None = None,
        skills: list[str] | None = None,
        location: str | None = None,
        experience_min: int | None = None,
        experience_max: int | None = None,
        source: str | None = None,
        include_archived: bool = False,
        sort: str = "createdAt:desc",
        limit: int = 20,
        offset: int = 0,
        compute_total: bool = True,
    ) -> tuple[Sequence[Candidate], int | None]:
        """Query candidates with filtering, search, sorting, and pagination per API Contract §CAND-1."""
        base_filters = self._build_candidate_filters(
            session=session,
            tenant_id=tenant_id,
            q=q,
            skills=skills,
            location=location,
            experience_min=experience_min,
            experience_max=experience_max,
            source=source,
            include_archived=include_archived,
        )

        total_count: int | None = None
        if compute_total:
            count_stmt = select(func.count(Candidate.id)).where(*base_filters)
            count_result = await session.execute(count_stmt)
            total_count = int(count_result.scalar_one())

        order_clauses = self._build_candidate_order_by(sort)

        query_stmt = (
            select(Candidate)
            .where(*base_filters)
            .order_by(*order_clauses)
            .offset(offset)
            .limit(limit)
        )
        query_result = await session.execute(query_stmt)
        candidates = query_result.scalars().all()

        return candidates, total_count

    async def update_candidate(
        self,
        session: AsyncSession,
        candidate_id: uuid.UUID,
        tenant_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> Candidate | None:
        """Update candidate attributes."""
        candidate = await self.get_candidate_by_id(session, candidate_id, tenant_id)
        if not candidate:
            return None

        for key, value in updates.items():
            if hasattr(candidate, key):
                setattr(candidate, key, value)

        await session.flush()
        await session.refresh(candidate)
        return candidate

    async def archive_candidate(
        self,
        session: AsyncSession,
        candidate_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Candidate | None:
        """Soft-delete candidate record."""
        return await self.update_candidate(
            session=session,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            updates={"is_archived": True},
        )

    async def delete_candidate(
        self,
        session: AsyncSession,
        candidate_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Hard delete candidate record."""
        candidate = await self.get_candidate_by_id(session, candidate_id, tenant_id)
        if not candidate:
            return False
        await session.delete(candidate)
        await session.flush()
        return True

    # --- JobCandidate Junction Operations ---

    async def add_candidate_to_job(
        self,
        session: AsyncSession,
        job_candidate: JobCandidate,
    ) -> JobCandidate:
        """Persist candidate-to-job association."""
        session.add(job_candidate)
        await session.flush()
        await session.refresh(job_candidate)

        # Reload with current_stage relationship
        stmt = (
            select(JobCandidate)
            .where(JobCandidate.id == job_candidate.id)
            .options(selectinload(JobCandidate.current_stage))
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    async def get_job_candidate(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> JobCandidate | None:
        """Fetch candidate-job association record."""
        stmt = (
            select(JobCandidate)
            .where(
                JobCandidate.job_id == job_id,
                JobCandidate.candidate_id == candidate_id,
                JobCandidate.tenant_id == tenant_id,
            )
            .options(selectinload(JobCandidate.current_stage))
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_job_candidates(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Sequence[JobCandidate]:
        """Fetch all candidates assigned to a job."""
        stmt = (
            select(JobCandidate)
            .where(
                JobCandidate.job_id == job_id,
                JobCandidate.tenant_id == tenant_id,
                JobCandidate.is_archived == False,  # noqa: E712
            )
            .options(
                selectinload(JobCandidate.candidate),
                selectinload(JobCandidate.current_stage),
            )
            .order_by(JobCandidate.created_at.desc())
        )
        res = await session.execute(stmt)
        return res.scalars().all()
