"""Embedding repository managing DB persistence for candidate_embeddings and job_embeddings."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.embeddings.models import CandidateEmbedding, JobEmbedding


class EmbeddingRepository:
    """Repository handling SQL operations for vector embeddings and coverage stats."""

    async def upsert_candidate_embedding(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        embedding: list[float],
        model_version: str,
        source_text_hash: str,
    ) -> CandidateEmbedding:
        """Create or update candidate vector embedding for candidate and model version."""
        stmt = select(CandidateEmbedding).where(
            CandidateEmbedding.tenant_id == tenant_id,
            CandidateEmbedding.candidate_id == candidate_id,
            CandidateEmbedding.model_version == model_version,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.embedding = embedding
            existing.source_text_hash = source_text_hash
            await session.flush()
            return existing

        new_embedding = CandidateEmbedding(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            embedding=embedding,
            model_version=model_version,
            source_text_hash=source_text_hash,
        )
        session.add(new_embedding)
        await session.flush()
        return new_embedding

    async def get_candidate_embedding(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        model_version: str,
    ) -> CandidateEmbedding | None:
        """Retrieve candidate vector embedding record."""
        stmt = select(CandidateEmbedding).where(
            CandidateEmbedding.tenant_id == tenant_id,
            CandidateEmbedding.candidate_id == candidate_id,
            CandidateEmbedding.model_version == model_version,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_job_embedding(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        embedding: list[float],
        model_version: str,
        source_text_hash: str,
    ) -> JobEmbedding:
        """Create or update job vector embedding for job and model version."""
        stmt = select(JobEmbedding).where(
            JobEmbedding.tenant_id == tenant_id,
            JobEmbedding.job_id == job_id,
            JobEmbedding.model_version == model_version,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.embedding = embedding
            existing.source_text_hash = source_text_hash
            await session.flush()
            return existing

        new_embedding = JobEmbedding(
            tenant_id=tenant_id,
            job_id=job_id,
            embedding=embedding,
            model_version=model_version,
            source_text_hash=source_text_hash,
        )
        session.add(new_embedding)
        await session.flush()
        return new_embedding

    async def get_job_embedding(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        model_version: str,
    ) -> JobEmbedding | None:
        """Retrieve job vector embedding record."""
        stmt = select(JobEmbedding).where(
            JobEmbedding.tenant_id == tenant_id,
            JobEmbedding.job_id == job_id,
            JobEmbedding.model_version == model_version,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_candidate_embeddings_map(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        model_version: str,
    ) -> dict[uuid.UUID, CandidateEmbedding]:
        """Fetch candidate embeddings dictionary keyed by candidate_id."""
        stmt = select(CandidateEmbedding).where(
            CandidateEmbedding.tenant_id == tenant_id,
            CandidateEmbedding.model_version == model_version,
        )
        result = await session.execute(stmt)
        records = result.scalars().all()
        return {r.candidate_id: r for r in records}

    async def get_job_embeddings_map(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        model_version: str,
    ) -> dict[uuid.UUID, JobEmbedding]:
        """Fetch job embeddings dictionary keyed by job_id."""
        stmt = select(JobEmbedding).where(
            JobEmbedding.tenant_id == tenant_id,
            JobEmbedding.model_version == model_version,
        )
        result = await session.execute(stmt)
        records = result.scalars().all()
        return {r.job_id: r for r in records}
