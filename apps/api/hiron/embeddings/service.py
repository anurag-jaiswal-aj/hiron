"""Embedding business service managing vector generation, staleness detection, and coverage stats."""

import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.candidates.models import Candidate
from hiron.candidates.repository import CandidateRepository
from hiron.common.exceptions import ResourceNotFoundException
from hiron.embeddings.exceptions import InsufficientEmbeddingPermissionsError
from hiron.embeddings.generator import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    EmbeddingGenerator,
)
from hiron.embeddings.repository import EmbeddingRepository
from hiron.embeddings.schemas import (
    CandidateEmbeddingResponseData,
    CoverageMetricData,
    EmbeddingStatusData,
    EmbeddingStatusResponse,
    GenerateCandidateEmbeddingResponse,
    GenerateJobEmbeddingResponse,
    IndividualEmbeddingStatusData,
    IndividualEmbeddingStatusResponse,
    JobEmbeddingResponseData,
)
from hiron.jobs.models import Job
from hiron.jobs.repository import JobRepository
from hiron.resumes.models import Resume

logger = structlog.get_logger("hiron.embeddings.service")


@dataclass
class PipelineResult:
    """Telemetry metadata for an embedding pipeline execution."""

    cache_hit: bool
    model_version: str
    input_tokens: int
    total_tokens: int
    latency_ms: int
    status: str
    error_type: str | None


class EmbeddingService:
    """Business service orchestrating candidate and job vector embedding generation and status tracking."""

    def __init__(
        self,
        embedding_repository: EmbeddingRepository | None = None,
        candidate_repository: CandidateRepository | None = None,
        job_repository: JobRepository | None = None,
        embedding_generator: EmbeddingGenerator | None = None,
    ) -> None:
        self.embedding_repo = embedding_repository or EmbeddingRepository()
        self.candidate_repo = candidate_repository or CandidateRepository()
        self.job_repo = job_repository or JobRepository()
        self.generator = embedding_generator or EmbeddingGenerator()

    def _validate_role_permissions(self, role: str) -> None:
        """Validate user role permissions for embedding operations."""
        if role not in ("org_admin", "recruiter"):
            raise InsufficientEmbeddingPermissionsError(
                f"User with role '{role}' is not authorized for embedding operations"
            )

    def _construct_job_source_text(self, job: Job) -> str:
        """Construct canonical text string from job entity for embedding generation."""
        skills_str = ", ".join(job.required_skills) if job.required_skills else "None"
        dept_str = f"Department: {job.department}\n" if job.department else ""
        return (
            f"{job.title}\n{dept_str}Description: {job.description}\nRequired Skills: {skills_str}"
        )

    async def _construct_candidate_source_text(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate: Candidate,
    ) -> str:
        """Construct canonical text string from candidate parsed resume or profile."""
        stmt = (
            select(Resume)
            .where(Resume.tenant_id == tenant_id, Resume.candidate_id == candidate.id)
            .order_by(Resume.is_primary.desc(), Resume.created_at.desc())
        )
        result = await session.execute(stmt)
        resumes = result.scalars().all()

        for resume in resumes:
            if resume.raw_text and resume.raw_text.strip():
                return resume.raw_text.strip()

        # Profile fallback if raw resume text is not present
        skills_str = ", ".join(candidate.skills) if candidate.skills else "None"
        title_str = f"Current Title: {candidate.current_title}\n" if candidate.current_title else ""
        summary_str = f"Summary: {candidate.summary}\n" if candidate.summary else ""
        return f"{candidate.full_name}\n{title_str}{summary_str}Skills: {skills_str}"

    async def generate_candidate_embedding_pipeline(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        model_version: str = DEFAULT_EMBEDDING_MODEL,
    ) -> PipelineResult:
        """Execute candidate embedding generation pipeline."""
        candidate = await self.candidate_repo.get_candidate_by_id(
            session=session,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
        )
        if not candidate:
            raise ResourceNotFoundException(f"Candidate with ID '{candidate_id}' not found")

        source_text = await self._construct_candidate_source_text(
            session=session,
            tenant_id=tenant_id,
            candidate=candidate,
        )
        current_hash = self.generator.compute_source_text_hash(source_text)

        existing = await self.embedding_repo.get_candidate_embedding(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            model_version=model_version,
        )

        if (
            existing is not None
            and existing.source_text_hash == current_hash
            and existing.model_version == model_version
            and existing.embedding is not None
            and len(existing.embedding) == EMBEDDING_DIMENSION
        ):
            logger.info(
                "Candidate embedding skipped (cache hit)",
                tenant_id=str(tenant_id),
                candidate_id=str(candidate_id),
            )
            return PipelineResult(
                cache_hit=True,
                model_version=model_version,
                input_tokens=0,
                total_tokens=0,
                latency_ms=0,
                status="success",
                error_type=None,
            )

        gen_result = await self.generator.generate_embedding(source_text)

        await self.embedding_repo.upsert_candidate_embedding(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            embedding=gen_result.embedding,
            model_version=model_version,
            source_text_hash=gen_result.source_text_hash,
        )
        logger.info(
            "Candidate embedding generated successfully",
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
            model_version=model_version,
        )

        return PipelineResult(
            cache_hit=False,
            model_version=model_version,
            input_tokens=gen_result.input_tokens,
            total_tokens=gen_result.total_tokens,
            latency_ms=gen_result.latency_ms,
            status=gen_result.status,
            error_type=gen_result.error_type,
        )

    async def generate_job_embedding_pipeline(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        model_version: str = DEFAULT_EMBEDDING_MODEL,
    ) -> PipelineResult:
        """Execute job embedding generation pipeline."""
        job = await self.job_repo.get_job_by_id(
            session=session,
            job_id=job_id,
            tenant_id=tenant_id,
        )
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        source_text = self._construct_job_source_text(job)
        current_hash = self.generator.compute_source_text_hash(source_text)

        existing = await self.embedding_repo.get_job_embedding(
            session=session,
            tenant_id=tenant_id,
            job_id=job_id,
            model_version=model_version,
        )

        if (
            existing is not None
            and existing.source_text_hash == current_hash
            and existing.model_version == model_version
            and existing.embedding is not None
            and len(existing.embedding) == EMBEDDING_DIMENSION
        ):
            logger.info(
                "Job embedding skipped (cache hit)",
                tenant_id=str(tenant_id),
                job_id=str(job_id),
            )
            return PipelineResult(
                cache_hit=True,
                model_version=model_version,
                input_tokens=0,
                total_tokens=0,
                latency_ms=0,
                status="success",
                error_type=None,
            )

        gen_result = await self.generator.generate_embedding(source_text)

        await self.embedding_repo.upsert_job_embedding(
            session=session,
            tenant_id=tenant_id,
            job_id=job_id,
            embedding=gen_result.embedding,
            model_version=model_version,
            source_text_hash=gen_result.source_text_hash,
        )
        logger.info(
            "Job embedding generated successfully",
            tenant_id=str(tenant_id),
            job_id=str(job_id),
            model_version=model_version,
        )

        return PipelineResult(
            cache_hit=False,
            model_version=model_version,
            input_tokens=gen_result.input_tokens,
            total_tokens=gen_result.total_tokens,
            latency_ms=gen_result.latency_ms,
            status=gen_result.status,
            error_type=gen_result.error_type,
        )

    async def generate_candidate_embedding(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        candidate_id: uuid.UUID,
        model_version: str = DEFAULT_EMBEDDING_MODEL,
    ) -> GenerateCandidateEmbeddingResponse:
        """API action to trigger candidate embedding generation per API Contract §EMBED-1."""
        self._validate_role_permissions(user_role)

        candidate = await self.candidate_repo.get_candidate_by_id(
            session=session,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
        )
        if not candidate:
            raise ResourceNotFoundException(f"Candidate with ID '{candidate_id}' not found")

        from hiron.core.config import get_settings
        settings = get_settings()

        if not settings.qstash_webhook_url:
            raise ValueError("qstash_webhook_url is required to publish background tasks")

        from hiron.core.qstash_client import qstash_publisher

        payload = {
            "tenant_id": str(tenant_id),
            "candidate_id": str(candidate_id),
            "model_version": model_version,
        }
        webhook_url = f"{settings.qstash_webhook_url.rstrip('/')}/api/v1/webhooks/qstash/embeddings/candidate"
        # Deduplication ID ensures we don't enqueue multiple generation tasks for the same candidate simultaneously
        task_id = await qstash_publisher.publish(
            url=webhook_url,
            payload=payload,
            deduplication_id=f"embed-cand-{candidate_id}-{model_version}-{uuid.uuid4()}",
        )
        if not task_id:
            task_id = f"task-{uuid.uuid4()}"

        return GenerateCandidateEmbeddingResponse(
            data=CandidateEmbeddingResponseData(
                candidate_id=candidate_id,
                task_id=task_id,
                status="processing",
                model_version=model_version,
            )
        )

    async def generate_job_embedding(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        job_id: uuid.UUID,
        model_version: str = DEFAULT_EMBEDDING_MODEL,
    ) -> GenerateJobEmbeddingResponse:
        """API action to trigger job embedding generation per API Contract §EMBED-2."""
        self._validate_role_permissions(user_role)

        job = await self.job_repo.get_job_by_id(
            session=session,
            job_id=job_id,
            tenant_id=tenant_id,
        )
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        from hiron.core.config import get_settings
        settings = get_settings()

        if not settings.qstash_webhook_url:
            raise ValueError("qstash_webhook_url is required to publish background tasks")

        from hiron.core.qstash_client import qstash_publisher

        payload = {
            "tenant_id": str(tenant_id),
            "job_id": str(job_id),
            "model_version": model_version,
        }
        webhook_url = (
            f"{settings.qstash_webhook_url.rstrip('/')}/api/v1/webhooks/qstash/embeddings/job"
        )
        # Deduplication ID ensures we don't enqueue multiple generation tasks for the same job simultaneously
        task_id = await qstash_publisher.publish(
            url=webhook_url,
            payload=payload,
            deduplication_id=f"embed-job-{job_id}-{model_version}-{uuid.uuid4()}",
        )
        if not task_id:
            task_id = f"task-{uuid.uuid4()}"

        return GenerateJobEmbeddingResponse(
            data=JobEmbeddingResponseData(
                job_id=job_id,
                task_id=task_id,
                status="processing",
                model_version=model_version,
            )
        )

    async def get_candidate_embedding_status(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        model_version: str = DEFAULT_EMBEDDING_MODEL,
    ) -> IndividualEmbeddingStatusResponse:
        """Fetch individual candidate embedding status (read-only, all roles)."""

        candidate = await self.candidate_repo.get_candidate_by_id(
            session=session,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
        )
        if not candidate:
            raise ResourceNotFoundException(f"Candidate with ID '{candidate_id}' not found")

        existing = await self.embedding_repo.get_latest_candidate_embedding(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
        )

        status = "missing"
        if existing:
            current_text = await self._construct_candidate_source_text(
                session=session, tenant_id=tenant_id, candidate=candidate
            )
            current_hash = self.generator.compute_source_text_hash(current_text)

            if (
                existing.source_text_hash == current_hash
                and existing.model_version == model_version
                and existing.embedding is not None
                and len(existing.embedding) == EMBEDDING_DIMENSION
            ):
                status = "current"
            else:
                status = "stale"

        return IndividualEmbeddingStatusResponse(
            data=IndividualEmbeddingStatusData(
                status=status,
                model_version=model_version,
            )
        )

    async def get_job_embedding_status(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        model_version: str = DEFAULT_EMBEDDING_MODEL,
    ) -> IndividualEmbeddingStatusResponse:
        """Fetch individual job embedding status (read-only, all roles)."""

        job = await self.job_repo.get_job_by_id(
            session=session,
            job_id=job_id,
            tenant_id=tenant_id,
        )
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        existing = await self.embedding_repo.get_latest_job_embedding(
            session=session,
            tenant_id=tenant_id,
            job_id=job_id,
        )

        status = "missing"
        if existing:
            current_text = self._construct_job_source_text(job)
            current_hash = self.generator.compute_source_text_hash(current_text)

            if (
                existing.source_text_hash == current_hash
                and existing.model_version == model_version
                and existing.embedding is not None
                and len(existing.embedding) == EMBEDDING_DIMENSION
            ):
                status = "current"
            else:
                status = "stale"

        return IndividualEmbeddingStatusResponse(
            data=IndividualEmbeddingStatusData(
                status=status,
                model_version=model_version,
            )
        )

    async def get_embedding_status(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        model_version: str = DEFAULT_EMBEDDING_MODEL,
    ) -> EmbeddingStatusResponse:
        """Fetch tenant embedding coverage statistics per API Contract §EMBED-3."""
        self._validate_role_permissions(user_role)

        # 1. Candidate coverage calculations
        stmt_cand = select(Candidate).where(
            Candidate.tenant_id == tenant_id, Candidate.is_archived.is_(False)
        )
        res_cand = await session.execute(stmt_cand)
        candidates = res_cand.scalars().all()

        cand_embeddings_map = await self.embedding_repo.get_candidate_embeddings_map(
            session=session, tenant_id=tenant_id
        )

        cand_total = len(candidates)
        cand_with_embedding = 0
        cand_stale = 0
        cand_missing = 0

        for cand in candidates:
            emb = cand_embeddings_map.get(cand.id)
            if not emb:
                cand_missing += 1
            else:
                current_text = await self._construct_candidate_source_text(
                    session=session, tenant_id=tenant_id, candidate=cand
                )
                current_hash = self.generator.compute_source_text_hash(current_text)
                if (
                    emb.source_text_hash == current_hash
                    and emb.model_version == model_version
                    and emb.embedding is not None
                    and len(emb.embedding) == EMBEDDING_DIMENSION
                ):
                    cand_with_embedding += 1
                else:
                    cand_stale += 1

        # 2. Job coverage calculations
        stmt_job = select(Job).where(Job.tenant_id == tenant_id)
        res_job = await session.execute(stmt_job)
        jobs = res_job.scalars().all()

        job_embeddings_map = await self.embedding_repo.get_job_embeddings_map(
            session=session, tenant_id=tenant_id
        )

        job_total = len(jobs)
        job_with_embedding = 0
        job_stale = 0
        job_missing = 0

        for job in jobs:
            job_emb = job_embeddings_map.get(job.id)
            if not job_emb:
                job_missing += 1
            else:
                current_text = self._construct_job_source_text(job)
                current_hash = self.generator.compute_source_text_hash(current_text)
                if (
                    job_emb.source_text_hash == current_hash
                    and job_emb.model_version == model_version
                    and job_emb.embedding is not None
                    and len(job_emb.embedding) == EMBEDDING_DIMENSION
                ):
                    job_with_embedding += 1
                else:
                    job_stale += 1

        return EmbeddingStatusResponse(
            data=EmbeddingStatusData(
                candidates=CoverageMetricData(
                    total=cand_total,
                    with_embedding=cand_with_embedding,
                    stale=cand_stale,
                    missing=cand_missing,
                    model_version=model_version,
                ),
                jobs=CoverageMetricData(
                    total=job_total,
                    with_embedding=job_with_embedding,
                    stale=job_stale,
                    missing=job_missing,
                    model_version=model_version,
                ),
            )
        )
