"""Search repository for vector similarity queries, hybrid metadata filtering, and saved searches in DB."""

import math
import uuid
from typing import Any

from sqlalchemy import literal, or_, select, text

# Configure pgvector types for SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.candidates.models import Candidate
from hiron.embeddings.generator import DEFAULT_EMBEDDING_MODEL
from hiron.embeddings.models import CandidateEmbedding, JobEmbedding
from hiron.jobs.models import Job
from hiron.search.models import SavedSearch
from hiron.search.schemas import SearchCandidateFilters


class SearchRepository:
    """Repository handling SQL pgvector similarity search, metadata filter clause building, and saved search CRUD."""

    def compute_cosine_similarity(
        self, vector_a: list[float] | None, vector_b: list[float] | None
    ) -> float:
        """Compute cosine similarity between two float vectors (0.0 to 1.0)."""
        if not vector_a or not vector_b or len(vector_a) != len(vector_b):
            return 0.5

        dot_product = sum(a * b for a, b in zip(vector_a, vector_b, strict=False))
        norm_a = math.sqrt(sum(a * a for a in vector_a))
        norm_b = math.sqrt(sum(b * b for b in vector_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.5

        similarity = dot_product / (norm_a * norm_b)
        return max(0.0, min(1.0, round(float(similarity), 4)))

    async def search_candidates_by_vector_and_filters(  # noqa: C901
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        query_vector: list[float] | None = None,
        filters: SearchCandidateFilters | None = None,
        limit: int = 20,
    ) -> list[tuple[Candidate, float]]:
        """Query candidates with pgvector similarity search and hybrid metadata filter clauses."""

        if query_vector is not None:
            similarity = (1 - CandidateEmbedding.embedding.cosine_distance(query_vector)).label(
                "similarity"
            )
            order_clause = CandidateEmbedding.embedding.cosine_distance(query_vector)

            stmt = (
                select(Candidate, similarity)
                .select_from(CandidateEmbedding)
                .join(Candidate, Candidate.id == CandidateEmbedding.candidate_id)
                .where(
                    CandidateEmbedding.model_version == DEFAULT_EMBEDDING_MODEL,
                    Candidate.tenant_id == tenant_id,
                    Candidate.is_archived.is_(False),
                )
            )
        else:
            similarity = text("0.5 AS similarity")
            order_clause = Candidate.created_at.desc()

            stmt = select(Candidate, similarity).where(
                Candidate.tenant_id == tenant_id,
                Candidate.is_archived.is_(False),
            )

        if filters:
            if filters.experience_min is not None:
                stmt = stmt.where(Candidate.total_experience_years >= filters.experience_min)
            if filters.experience_max is not None:
                stmt = stmt.where(Candidate.total_experience_years <= filters.experience_max)
            if filters.location:
                stmt = stmt.where(Candidate.location.ilike(f"%{filters.location}%"))
            if filters.current_title:
                stmt = stmt.where(Candidate.current_title.ilike(f"%{filters.current_title}%"))
            if filters.q:
                q_term = f"%{filters.q}%"
                stmt = stmt.where(
                    or_(
                        Candidate.full_name.ilike(q_term),
                        Candidate.summary.ilike(q_term),
                        Candidate.current_title.ilike(q_term),
                        Candidate.current_company.ilike(q_term),
                    )
                )
            if filters.skills:
                # Use PostgreSQL JSONB array containment
                stmt = stmt.where(Candidate.skills.contains(literal(filters.skills, type_=JSONB)))

        # Enforce ordering and limit directly in DB
        stmt = stmt.order_by(order_clause).limit(limit)

        result = await session.execute(stmt)
        rows = result.all()

        scored_candidates: list[tuple[Candidate, float]] = []

        for candidate, sim_score in rows:
            # Ensure similarity score is between 0.0 and 1.0
            if sim_score is None:
                sim_score = 0.5
            similarity_rounded = max(0.0, min(1.0, round(float(sim_score), 4)))
            scored_candidates.append((candidate, similarity_rounded))

        return scored_candidates

    async def search_jobs_by_vector(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        query_vector: list[float] | None = None,
        limit: int = 20,
    ) -> list[tuple[Job, float]]:
        """Query open jobs ranked by vector similarity to candidate embedding or query."""

        if query_vector is not None:
            similarity = (1 - JobEmbedding.embedding.cosine_distance(query_vector)).label(
                "similarity"
            )
            order_clause = JobEmbedding.embedding.cosine_distance(query_vector)
        else:
            similarity = text("0.5 AS similarity")
            order_clause = Job.created_at.desc()

        stmt = (
            select(Job, similarity)
            .outerjoin(
                JobEmbedding,
                (Job.id == JobEmbedding.job_id)
                & (JobEmbedding.model_version == DEFAULT_EMBEDDING_MODEL),
            )
            .where(
                Job.tenant_id == tenant_id,
                Job.status == "published",
            )
        )

        stmt = stmt.order_by(order_clause).limit(limit)

        result = await session.execute(stmt)
        rows = result.all()

        scored_jobs: list[tuple[Job, float]] = []
        for job, sim_score in rows:
            if sim_score is None:
                sim_score = 0.5
            similarity_rounded = max(0.0, min(1.0, round(float(sim_score), 4)))
            scored_jobs.append((job, similarity_rounded))

        return scored_jobs

    async def create_saved_search(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        created_by: uuid.UUID,
        name: str,
        query_text: str,
        filters: dict[str, Any] | None = None,
        is_shared: bool = False,
    ) -> SavedSearch:
        """Create and persist a new SavedSearch entity."""
        saved_search = SavedSearch(
            tenant_id=tenant_id,
            created_by=created_by,
            name=name,
            query_text=query_text,
            filters=filters or {},
            is_shared=is_shared,
        )
        session.add(saved_search)
        await session.flush()
        return saved_search

    async def list_saved_searches(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[SavedSearch]:
        """List saved searches owned by user or marked as shared in tenant."""
        stmt = (
            select(SavedSearch)
            .where(
                SavedSearch.tenant_id == tenant_id,
                or_(SavedSearch.created_by == user_id, SavedSearch.is_shared.is_(True)),
            )
            .order_by(SavedSearch.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_saved_search_by_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        search_id: uuid.UUID,
    ) -> SavedSearch | None:
        """Fetch saved search by ID and tenant ID."""
        stmt = select(SavedSearch).where(
            SavedSearch.tenant_id == tenant_id,
            SavedSearch.id == search_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_saved_search(
        self,
        session: AsyncSession,
        search: SavedSearch,
        name: str | None = None,
        query_text: str | None = None,
        filters: dict[str, Any] | None = None,
        is_shared: bool | None = None,
    ) -> SavedSearch:
        """Update existing saved search attributes."""
        if name is not None:
            search.name = name
        if query_text is not None:
            search.query_text = query_text
        if filters is not None:
            search.filters = filters
        if is_shared is not None:
            search.is_shared = is_shared
        await session.flush()
        return search

    async def delete_saved_search(
        self,
        session: AsyncSession,
        search: SavedSearch,
    ) -> None:
        """Delete saved search entity from DB."""
        await session.delete(search)
        await session.flush()
