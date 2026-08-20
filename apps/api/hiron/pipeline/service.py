"""Pipeline service orchestrating stage transitions, timeline logging, and Kanban board views per API Contract §PIPE-1..4."""

import datetime
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.audit.service import AuditService
from hiron.audit.utils import extract_model_changes, sanitize_audit_payload
from hiron.candidates.repository import CandidateRepository
from hiron.common.exceptions import ResourceNotFoundException
from hiron.jobs.repository import JobRepository
from hiron.pipeline.exceptions import (
    InsufficientPipelinePermissionsError,
    PipelineStageValidationError,
)
from hiron.pipeline.repository import PipelineRepository
from hiron.pipeline.schemas import (
    KanbanCandidateCard,
    MoveCandidateStageData,
    MoveCandidateStageResponse,
    PipelineBoardResponse,
    PipelineStageStats,
    RejectCandidateData,
    RejectCandidateResponse,
    ShortlistCandidateData,
    ShortlistCandidateResponse,
    StageHistoryItem,
    StageHistoryResponse,
    StageInfo,
    UserInfo,
)
from hiron.users.repository import UserRepository

logger = structlog.get_logger("hiron.pipeline.service")


class PipelineService:
    """Business service handling candidate pipeline movements, stage history, and Kanban stats."""

    def __init__(
        self,
        pipeline_repository: PipelineRepository | None = None,
        candidate_repository: CandidateRepository | None = None,
        job_repository: JobRepository | None = None,
        user_repository: UserRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.pipeline_repo = pipeline_repository or PipelineRepository()
        self.candidate_repo = candidate_repository or CandidateRepository()
        self.job_repo = job_repository or JobRepository()
        self.user_repo = user_repository or UserRepository()
        self.audit_service = audit_service or AuditService()

    def _validate_move_permissions(self, role: str) -> None:
        """Validate that user role has stage movement rights (hiring managers are read-only)."""
        if role not in ("org_admin", "recruiter"):
            raise InsufficientPipelinePermissionsError(
                f"User with role '{role}' is not authorized to move candidates between pipeline stages"
            )

    async def move_candidate_stage(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        job_candidate_id: uuid.UUID,
        to_stage_id: uuid.UUID,
        note: str | None = None,
    ) -> MoveCandidateStageResponse:
        """Move candidate to target pipeline stage per API Contract §PIPE-1."""
        self._validate_move_permissions(user_role)

        job_candidate = await self.pipeline_repo.get_job_candidate_by_id(
            session=session, tenant_id=tenant_id, job_candidate_id=job_candidate_id
        )
        if not job_candidate:
            raise ResourceNotFoundException(f"JobCandidate with ID '{job_candidate_id}' not found")

        target_stage = await self.pipeline_repo.get_stage_by_id(
            session=session, tenant_id=tenant_id, stage_id=to_stage_id
        )
        if not target_stage:
            raise ResourceNotFoundException(f"PipelineStage with ID '{to_stage_id}' not found")

        # Validate stage belongs to the same job
        if target_stage.job_id != job_candidate.job_id:
            raise PipelineStageValidationError(
                "Target pipeline stage does not belong to candidate's job"
            )

        # Validation: no-op check (cannot move to current stage)
        if job_candidate.current_stage_id == to_stage_id:
            raise PipelineStageValidationError(
                "Candidate is already in the requested pipeline stage"
            )

        from_stage = job_candidate.current_stage
        from_stage_id = from_stage.id if from_stage else None

        actor_user = await self.user_repo.get_by_id(session=session, user_id=user_id)
        actor_name = actor_user.full_name if actor_user else "System"

        # Record stage history
        now = datetime.datetime.now(datetime.UTC)
        await self.pipeline_repo.create_stage_history(
            session=session,
            tenant_id=tenant_id,
            job_candidate_id=job_candidate.id,
            from_stage_id=from_stage_id,
            to_stage_id=to_stage_id,
            moved_by=user_id,
            note=note,
        )

        # Update candidate current_stage_id
        updated_jc = await self.pipeline_repo.update_job_candidate_stage(
            session=session, job_candidate=job_candidate, to_stage_id=to_stage_id
        )

        logger.info(
            "Moved candidate to new pipeline stage",
            tenant_id=str(tenant_id),
            job_candidate_id=str(job_candidate_id),
            from_stage_id=str(from_stage_id),
            to_stage_id=str(to_stage_id),
        )

        prev_info = (
            StageInfo(id=from_stage.id, name=from_stage.name, position=from_stage.position)
            if from_stage
            else None
        )
        curr_info = StageInfo(
            id=target_stage.id, name=target_stage.name, position=target_stage.position
        )

        changes = extract_model_changes(updated_jc, "update")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="stage_changed",
                entity_type="job_candidate",
                entity_id=updated_jc.id,
                actor_id=user_id,
                changes=changes,
            )

        await session.commit()

        return MoveCandidateStageResponse(
            data=MoveCandidateStageData(
                job_candidate_id=updated_jc.id,
                previous_stage=prev_info,
                current_stage=curr_info,
                moved_by=UserInfo(id=user_id, full_name=actor_name),
                note=note,
                moved_at=now,
            )
        )

    async def get_stage_history(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> StageHistoryResponse:
        """Get complete timeline of stage transitions for a candidate in a job per API Contract §PIPE-2."""
        job_candidate = await self.candidate_repo.get_job_candidate(
            session=session, job_id=job_id, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not job_candidate:
            raise ResourceNotFoundException("No candidate-job association found")

        history_rows = await self.pipeline_repo.list_stage_history(
            session=session, tenant_id=tenant_id, job_candidate_id=job_candidate.id
        )

        items: list[StageHistoryItem] = []
        for h in history_rows:
            from_info = (
                StageInfo(
                    id=h.from_stage.id, name=h.from_stage.name, position=h.from_stage.position
                )
                if h.from_stage
                else None
            )
            to_info = StageInfo(
                id=h.to_stage.id, name=h.to_stage.name, position=h.to_stage.position
            )
            moved_by_info = (
                UserInfo(id=h.actor.id, full_name=h.actor.full_name) if h.actor else None
            )

            items.append(
                StageHistoryItem(
                    id=h.id,
                    from_stage=from_info,
                    to_stage=to_info,
                    moved_by=moved_by_info,
                    note=h.note,
                    created_at=h.created_at,
                )
            )

        return StageHistoryResponse(data=items)

    async def shortlist_candidate(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> ShortlistCandidateResponse:
        """Mark candidate as shortlisted for hiring manager review per API Contract §PIPE-3."""
        self._validate_move_permissions(user_role)

        job_candidate = await self.candidate_repo.get_job_candidate(
            session=session, job_id=job_id, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not job_candidate:
            raise ResourceNotFoundException("No candidate-job association found")

        updated_jc = await self.pipeline_repo.shortlist_job_candidate(
            session=session, job_candidate=job_candidate, is_shortlisted=True
        )

        now = datetime.datetime.now(datetime.UTC)
        logger.info(
            "Shortlisted candidate for hiring manager review",
            tenant_id=str(tenant_id),
            job_candidate_id=str(job_candidate.id),
        )

        changes = extract_model_changes(updated_jc, "update")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="candidate_shortlisted",
                entity_type="job_candidate",
                entity_id=updated_jc.id,
                actor_id=user_id,
                changes=changes,
            )

        await session.commit()

        return ShortlistCandidateResponse(
            data=ShortlistCandidateData(
                job_candidate_id=updated_jc.id,
                is_shortlisted=updated_jc.is_shortlisted,
                shortlisted_at=datetime.datetime.now(datetime.UTC),
            )
        )

    async def reject_candidate(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        reason: str | None = None,
    ) -> RejectCandidateResponse:
        """Move candidate to rejected stage with reason per API Contract §PIPE-4."""
        self._validate_move_permissions(user_role)

        job_candidate = await self.candidate_repo.get_job_candidate(
            session=session, job_id=job_id, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not job_candidate:
            raise ResourceNotFoundException("No candidate-job association found")

        # Find or use terminal rejected stage
        stages = await self.pipeline_repo.list_stages_for_job(
            session=session, tenant_id=tenant_id, job_id=job_id
        )
        rejected_stage = next(
            (s for s in stages if s.name.lower() in ("rejected", "disqualified")),
            stages[-1] if stages else None,
        )
        if not rejected_stage:
            raise ResourceNotFoundException("No pipeline stages configured for this job")

        from_stage_id = job_candidate.current_stage_id

        # Insert transition history
        await self.pipeline_repo.create_stage_history(
            session=session,
            tenant_id=tenant_id,
            job_candidate_id=job_candidate.id,
            from_stage_id=from_stage_id,
            to_stage_id=rejected_stage.id,
            moved_by=user_id,
            note=f"Rejected: {reason}" if reason else "Rejected",
        )

        updated_jc = await self.pipeline_repo.reject_job_candidate(
            session=session,
            job_candidate=job_candidate,
            rejected_stage_id=rejected_stage.id,
            rejection_reason=reason,
        )

        logger.info(
            "Rejected candidate",
            tenant_id=str(tenant_id),
            job_candidate_id=str(job_candidate.id),
            reason=reason,
        )

        changes = extract_model_changes(updated_jc, "update")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="candidate_rejected",
                entity_type="job_candidate",
                entity_id=updated_jc.id,
                actor_id=user_id,
                changes=changes,
            )

        await session.commit()

        return RejectCandidateResponse(
            data=RejectCandidateData(
                job_candidate_id=updated_jc.id,
                status="rejected",
                rejection_reason=updated_jc.rejection_reason,
                rejected_at=datetime.datetime.now(datetime.UTC),
            )
        )

    async def get_pipeline_board(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> PipelineBoardResponse:
        """Fetch Kanban pipeline board grouping candidates by stage with counts and Phase 8 AI scores."""
        job = await self.job_repo.get_job_by_id(session=session, job_id=job_id, tenant_id=tenant_id)
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        stages = await self.pipeline_repo.list_stages_for_job(
            session=session, tenant_id=tenant_id, job_id=job_id
        )

        board_stats: list[PipelineStageStats] = []

        for stage in stages:
            cand_rows = await self.pipeline_repo.get_job_candidates_for_stage(
                session=session, tenant_id=tenant_id, job_id=job_id, stage_id=stage.id
            )
            cards: list[KanbanCandidateCard] = []

            for jc, cand, score in cand_rows:
                cards.append(
                    KanbanCandidateCard(
                        candidate_id=cand.id,
                        job_candidate_id=jc.id,
                        full_name=cand.full_name,
                        current_title=cand.current_title,
                        fit_score=score.fit_score if score else None,
                        confidence=score.confidence if score else None,
                        is_shortlisted=jc.is_shortlisted,
                        applied_at=jc.created_at,
                    )
                )

            board_stats.append(
                PipelineStageStats(
                    stage_id=stage.id,
                    stage_name=stage.name,
                    position=stage.position,
                    candidate_count=len(cards),
                    candidates=cards,
                )
            )

        return PipelineBoardResponse(data=board_stats)
