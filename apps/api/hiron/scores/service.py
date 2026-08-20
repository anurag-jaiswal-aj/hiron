"""Score domain business service handling scoring execution, 24h idempotency, and history per API Contract §SCORE-1..5."""

import datetime
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.ai_usage.service import AIUsageService
from hiron.audit.service import AuditService
from hiron.audit.utils import extract_model_changes, sanitize_audit_payload
from hiron.candidates.models import JobCandidate
from hiron.candidates.repository import CandidateRepository
from hiron.common.exceptions import ResourceNotFoundException
from hiron.embeddings.generator import DEFAULT_EMBEDDING_MODEL
from hiron.embeddings.repository import EmbeddingRepository
from hiron.jobs.repository import JobRepository
from hiron.scores.engine import AIScoringEngine
from hiron.scores.exceptions import InsufficientScorePermissionsError
from hiron.scores.models import Score
from hiron.scores.repository import ScoreRepository
from hiron.scores.schemas import (
    BatchScoreData,
    BatchScoreResponse,
    ConfidenceFactorsData,
    ScoreData,
    ScoreExplanationData,
    ScoreExplanationResponse,
    ScoreHistoryItem,
    ScoreHistoryResponse,
    ScoreResponse,
)

logger = structlog.get_logger("hiron.scores.service")

SCORE_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours idempotency cache TTL


class ScoreService:
    """Business service orchestrating candidate-job AI fit scoring pipeline, history, and explanations."""

    def __init__(
        self,
        score_repository: ScoreRepository | None = None,
        candidate_repository: CandidateRepository | None = None,
        job_repository: JobRepository | None = None,
        embedding_repository: EmbeddingRepository | None = None,
        scoring_engine: AIScoringEngine | None = None,
        ai_usage_service: AIUsageService | None = None,
    ) -> None:
        self.score_repo = score_repository or ScoreRepository()
        self.candidate_repo = candidate_repository or CandidateRepository()
        self.job_repo = job_repository or JobRepository()
        self.embedding_repo = embedding_repository or EmbeddingRepository()
        self.engine = scoring_engine or AIScoringEngine()
        self.ai_usage_service = ai_usage_service or AIUsageService()
        self.audit_service = AuditService()

    def _validate_role_permissions(self, role: str) -> None:
        """Validate user role authorization for scoring operations."""
        if role not in ("org_admin", "recruiter"):
            raise InsufficientScorePermissionsError(
                f"User with role '{role}' is not authorized for scoring operations"
            )

    def _build_score_data(self, score: Score) -> ScoreData:
        """Convert Score model instance to Pydantic ScoreData schema."""
        return ScoreData(
            id=score.id,
            fit_score=score.fit_score,
            confidence=score.confidence,
            breakdown=score.breakdown,
            explanation=score.explanation,
            skills_matched=score.skills_matched or [],
            skills_missing=score.skills_missing or [],
            warnings=score.warnings or [],
            prompt_version=score.prompt_version,
            model_version=score.model_version,
            is_current=score.is_current,
            created_at=score.created_at,
        )

    def _is_cache_valid(self, score: Score) -> bool:
        """Check if score was created within 24 hours."""
        if not score.created_at:
            return False
        now = datetime.datetime.now(datetime.UTC)
        created = score.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=datetime.UTC)
        return (now - created).total_seconds() < SCORE_CACHE_TTL_SECONDS

    async def score_candidate_sync(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        force_rescore: bool = False,
    ) -> ScoreResponse:
        """Score candidate against job per API Contract §SCORE-1 (with 24h idempotency cache)."""
        self._validate_role_permissions(user_role)

        candidate = await self.candidate_repo.get_candidate_by_id(
            session=session, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not candidate:
            raise ResourceNotFoundException(f"Candidate with ID '{candidate_id}' not found")

        job = await self.job_repo.get_job_by_id(session=session, job_id=job_id, tenant_id=tenant_id)
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        # Resolve or create candidate-job binding
        job_candidate = await self.candidate_repo.get_job_candidate(
            session=session, job_id=job_id, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not job_candidate:
            new_jc = JobCandidate(
                tenant_id=tenant_id,
                job_id=job_id,
                candidate_id=candidate_id,
            )
            job_candidate = await self.candidate_repo.add_candidate_to_job(
                session=session,
                job_candidate=new_jc,
            )

        # Idempotency check: return cached score within 24h unless force_rescore=True
        if not force_rescore:
            existing_score = await self.score_repo.get_current_score(
                session=session, tenant_id=tenant_id, job_candidate_id=job_candidate.id
            )
            if existing_score and self._is_cache_valid(existing_score):
                logger.info(
                    "Returning cached AI score within 24h window",
                    tenant_id=str(tenant_id),
                    candidate_id=str(candidate_id),
                    job_id=str(job_id),
                )

                try:
                    await self.ai_usage_service.record_ai_usage(
                        session=session,
                        tenant_id=tenant_id,
                        operation="generate_candidate_score",
                        model_version=existing_score.model_version or "gemini-1.5-flash",
                        prompt_name=existing_score.prompt_name or "score_candidate",
                        prompt_version=existing_score.prompt_version or "1.0",
                        input_tokens=0,
                        output_tokens=0,
                        latency_ms=0,
                        cost_usd=0.0,
                        status="success",
                        is_cache_hit=True,
                    )
                except Exception as log_exc:
                    logger.warning(
                        "Failed to write AI usage telemetry for scoring cache hit",
                        error=str(log_exc),
                    )

                return ScoreResponse(data=self._build_score_data(existing_score))

        # Retrieve vectors if present
        cand_emb = await self.embedding_repo.get_candidate_embedding(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            model_version=DEFAULT_EMBEDDING_MODEL,
        )
        job_emb = await self.embedding_repo.get_job_embedding(
            session=session,
            tenant_id=tenant_id,
            job_id=job_id,
            model_version=DEFAULT_EMBEDDING_MODEL,
        )

        cand_vec = cand_emb.embedding if cand_emb else None
        job_vec = job_emb.embedding if job_emb else None

        # Execute scoring engine
        evaluation = await self.engine.evaluate(
            candidate=candidate,
            job=job,
            candidate_vector=cand_vec,
            job_vector=job_vec,
        )

        # Persist new score record
        new_score = await self.score_repo.create_score(
            session=session,
            tenant_id=tenant_id,
            job_candidate_id=job_candidate.id,
            fit_score=evaluation["fit_score"],
            confidence=evaluation["confidence"],
            breakdown=evaluation["breakdown"],
            explanation=evaluation["explanation"],
            skills_matched=evaluation["skills_matched"],
            skills_missing=evaluation["skills_missing"],
            prompt_name=evaluation["prompt_name"],
            prompt_version=evaluation["prompt_version"],
            model_version=evaluation["model_version"],
            input_tokens=evaluation["input_tokens"],
            output_tokens=evaluation["output_tokens"],
            latency_ms=evaluation["latency_ms"],
            warnings=evaluation["warnings"],
        )

        cost_usd = (evaluation["input_tokens"] / 1_000_000 * 0.075) + (
            evaluation["output_tokens"] / 1_000_000 * 0.30
        )

        await self.ai_usage_service.record_ai_usage(
            session=session,
            tenant_id=tenant_id,
            operation="generate_candidate_score",
            model_version=evaluation["model_version"],
            prompt_name=evaluation["prompt_name"],
            prompt_version=evaluation["prompt_version"],
            input_tokens=evaluation["input_tokens"],
            output_tokens=evaluation["output_tokens"],
            latency_ms=evaluation["latency_ms"],
            cost_usd=cost_usd,
            status="success",
            is_cache_hit=False,
        )

        changes = extract_model_changes(new_score, "create")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="candidate_scored",
                entity_type="score",
                entity_id=new_score.id,
                actor_id=None,
                changes=changes,
            )

        await session.commit()

        logger.info(
            "AI candidate scoring executed successfully",
            tenant_id=str(tenant_id),
            job_id=str(job_id),
            candidate_id=str(candidate_id),
            fit_score=new_score.fit_score,
        )
        return ScoreResponse(data=self._build_score_data(new_score))

    async def batch_score_async(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        job_id: uuid.UUID,
        candidate_ids: list[uuid.UUID] | None = None,
        force_rescore: bool = False,
    ) -> BatchScoreResponse:
        """Batch score candidates for a job asynchronously per API Contract §SCORE-2."""
        self._validate_role_permissions(user_role)

        job = await self.job_repo.get_job_by_id(session=session, job_id=job_id, tenant_id=tenant_id)
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        if candidate_ids:
            target_ids = candidate_ids
        else:
            job_candidates = await self.candidate_repo.list_job_candidates(
                session=session, job_id=job_id, tenant_id=tenant_id
            )
            target_ids = [jc.candidate_id for jc in job_candidates]

        queued_count = len(target_ids)
        estimated_sec = max(5, queued_count * 5)

        from hiron.core.config import get_settings

        settings = get_settings()

        if not settings.qstash_webhook_url:
            raise ValueError("qstash_webhook_url is required to publish background tasks")

        # Create exactly one BatchScoreJob row
        batch_job = await self.score_repo.create_batch_score_job(
            session=session,
            tenant_id=tenant_id,
            job_id=job_id,
            queued_count=queued_count,
        )
        task_id = str(batch_job.id)

        from hiron.core.qstash_client import qstash_publisher

        payload = {
            "batch_id": task_id,
            "tenant_id": str(tenant_id),
            "job_id": str(job_id),
            "candidate_ids": [str(cid) for cid in target_ids],
            "force_rescore": force_rescore,
        }

        dedup_id = f"batch-coord-{tenant_id}-{job_id}-{task_id}"

        await session.commit()

        await qstash_publisher.publish(
            url=f"{settings.qstash_webhook_url}/api/v1/webhooks/qstash/scores/batch/coordinator",
            payload=payload,
            deduplication_id=dedup_id,
        )

        logger.info(
            "Enqueued batch candidate scoring via QStash coordinator",
            tenant_id=str(tenant_id),
            job_id=str(job_id),
            candidates_queued=queued_count,
            task_id=task_id,
            force_rescore=force_rescore,
            dedup_id=dedup_id,
        )

        return BatchScoreResponse(
            data=BatchScoreData(
                task_id=task_id,
                candidates_queued=queued_count,
                estimated_completion_seconds=estimated_sec,
                status_url=f"/api/v1/tasks/{task_id}",
            )
        )

    async def get_score(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> ScoreResponse:
        """Fetch current score for candidate-job pair per API Contract §SCORE-3."""
        job_candidate = await self.candidate_repo.get_job_candidate(
            session=session, job_id=job_id, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not job_candidate:
            raise ResourceNotFoundException("No candidate-job association found for this pair")

        score = await self.score_repo.get_current_score(
            session=session, tenant_id=tenant_id, job_candidate_id=job_candidate.id
        )
        if not score:
            raise ResourceNotFoundException("No score exists for this candidate-job pair")

        return ScoreResponse(data=self._build_score_data(score))

    async def get_score_history(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> ScoreHistoryResponse:
        """Fetch score history for candidate-job pair per API Contract §SCORE-4."""
        self._validate_role_permissions(user_role)

        job_candidate = await self.candidate_repo.get_job_candidate(
            session=session, job_id=job_id, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not job_candidate:
            raise ResourceNotFoundException("No candidate-job association found for this pair")

        scores = await self.score_repo.get_score_history(
            session=session, tenant_id=tenant_id, job_candidate_id=job_candidate.id
        )

        history_items = [
            ScoreHistoryItem(
                id=s.id,
                fit_score=s.fit_score,
                prompt_version=s.prompt_version,
                is_current=s.is_current,
                created_at=s.created_at,
            )
            for s in scores
        ]
        return ScoreHistoryResponse(data=history_items)

    async def get_score_explanation(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        score_id: uuid.UUID,
    ) -> ScoreExplanationResponse:
        """Fetch score explanation payload per API Contract §SCORE-5."""
        score = await self.score_repo.get_score_by_id(
            session=session, tenant_id=tenant_id, score_id=score_id
        )
        if not score:
            raise ResourceNotFoundException(f"Score with ID '{score_id}' not found")

        confidence_factors = ConfidenceFactorsData(
            resume_completeness=0.95,
            output_consistency=0.90,
            explanation_quality=0.85,
            sanity_check_passed=len(score.warnings or []) == 0,
        )

        return ScoreExplanationResponse(
            data=ScoreExplanationData(
                score_id=score.id,
                fit_score=score.fit_score,
                explanation=score.explanation,
                breakdown=score.breakdown,
                skills_matched=score.skills_matched or [],
                skills_missing=score.skills_missing or [],
                warnings=score.warnings or [],
                confidence=score.confidence,
                confidence_factors=confidence_factors,
            )
        )
