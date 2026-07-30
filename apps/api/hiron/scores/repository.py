"""Score repository managing persistence and active score status demotion in DB per Database Design §5.10."""

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.scores.models import Score


class ScoreRepository:
    """Repository handling SQL persistence and score history queries."""

    async def create_score(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_candidate_id: uuid.UUID,
        fit_score: int,
        confidence: float,
        breakdown: dict[str, Any],
        explanation: str,
        skills_matched: list[str],
        skills_missing: list[str],
        prompt_name: str,
        prompt_version: str,
        model_version: str,
        input_tokens: int = 1250,
        output_tokens: int = 350,
        latency_ms: int = 420,
        warnings: list[str] | None = None,
    ) -> Score:
        """Demote existing current scores for job_candidate_id to is_current=False, then create new score."""
        # 1. Demote previous active scores
        stmt_demote = (
            update(Score)
            .where(
                Score.job_candidate_id == job_candidate_id,
                Score.is_current.is_(True),
            )
            .values(is_current=False)
        )
        await session.execute(stmt_demote)

        # 2. Insert new score record
        new_score = Score(
            tenant_id=tenant_id,
            job_candidate_id=job_candidate_id,
            fit_score=fit_score,
            confidence=confidence,
            breakdown=breakdown,
            explanation=explanation,
            skills_matched=skills_matched,
            skills_missing=skills_missing,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            model_version=model_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            warnings=warnings or [],
            is_current=True,
        )
        session.add(new_score)
        await session.flush()
        return new_score

    async def get_current_score(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_candidate_id: uuid.UUID,
    ) -> Score | None:
        """Fetch the active current score record for a job_candidate."""
        stmt = select(Score).where(
            Score.tenant_id == tenant_id,
            Score.job_candidate_id == job_candidate_id,
            Score.is_current.is_(True),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_score_history(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_candidate_id: uuid.UUID,
    ) -> list[Score]:
        """Fetch historical scores for a job_candidate ordered by created_at DESC."""
        stmt = (
            select(Score)
            .where(
                Score.tenant_id == tenant_id,
                Score.job_candidate_id == job_candidate_id,
            )
            .order_by(Score.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_score_by_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        score_id: uuid.UUID,
    ) -> Score | None:
        """Fetch score record by ID and tenant ID."""
        stmt = select(Score).where(
            Score.tenant_id == tenant_id,
            Score.id == score_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
