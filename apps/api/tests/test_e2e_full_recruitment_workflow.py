"""End-to-End full recruitment workflow integration test per Phase 17."""

import datetime
import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.ai_usage.service import AIUsageService
from hiron.audit.service import AuditService
from hiron.candidates.models import Candidate
from hiron.candidates.service import CandidateService
from hiron.dashboard.service import DashboardService
from hiron.jobs.models import Job, PipelineStage
from hiron.jobs.service import JobService
from hiron.notes.models import CandidateNote
from hiron.notes.service import NoteService
from hiron.pipeline.schemas import (
    MoveCandidateStageData,
    MoveCandidateStageResponse,
    StageInfo,
    UserInfo,
)
from hiron.pipeline.service import PipelineService
from hiron.scores.models import Score
from hiron.scores.service import ScoreService
from hiron.tags.models import CandidateTag
from hiron.tags.service import TagService
from hiron.users.models import User


@pytest.mark.asyncio
async def test_full_recruitment_workflow_e2e_journey() -> None:
    """Execute end-to-end hiring journey: Job Creation -> Candidate Creation -> AI Scoring -> Stage Move -> Notes/Tags -> Audit & Dashboard updates."""
    session = AsyncMock()
    tenant_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    # 1. Job Creation
    job_service = JobService()
    job_service.job_repo = AsyncMock()
    job_id = uuid.uuid4()
    job_service.job_repo.create_job.return_value = Job(
        id=job_id,
        tenant_id=tenant_id,
        title="Senior Staff Engineer",
        description="Full job description",
        department="Engineering",
        status="published",
        created_at=datetime.datetime.now(datetime.UTC),
    )

    job = await job_service.create_job(
        session=session,
        tenant_id=tenant_id,
        created_by=user_id,
        current_user_role="org_admin",
        title="Senior Staff Engineer",
        description="Full job description",
        department="Engineering",
    )
    assert job.title == "Senior Staff Engineer"

    # 2. Candidate Creation
    candidate_service = CandidateService()
    candidate_service.candidate_repo = AsyncMock()
    candidate_service.candidate_repo.get_candidate_by_email.return_value = None
    candidate_id = uuid.uuid4()
    candidate_service.candidate_repo.create_candidate.return_value = Candidate(
        id=candidate_id,
        tenant_id=tenant_id,
        full_name="Alice Engineer",
        email="alice@example.com",
        created_at=datetime.datetime.now(datetime.UTC),
    )

    candidate = await candidate_service.create_candidate(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        current_user_role="org_admin",
        full_name="Alice Engineer",
        email="alice@example.com",
    )
    assert candidate.full_name == "Alice Engineer"

    # 3. Candidate AI Scoring
    score_service = ScoreService()
    score_service.score_repo = AsyncMock()
    score_service.candidate_repo = AsyncMock()
    score_service.job_repo = AsyncMock()
    score_service.embedding_repo = AsyncMock()

    score_service.score_repo.get_current_score.return_value = None
    score_service.score_repo.get_latest_score.return_value = None
    score_service.candidate_repo.get_candidate_by_id.return_value = candidate
    score_service.job_repo.get_job_by_id.return_value = job
    job_candidate_id = uuid.uuid4()
    score_service.candidate_repo.get_job_candidate.return_value = AsyncMock(id=job_candidate_id)
    score_service.embedding_repo.get_candidate_embedding.return_value = None
    score_service.embedding_repo.get_job_embedding.return_value = None
    score_service.engine = AsyncMock()
    score_service.engine.evaluate.return_value = {
        "fit_score": 92,
        "confidence": 0.90,
        "explanation": "Exceptional technical alignment.",
        "skills_matched": ["Python"],
        "skills_missing": [],
        "breakdown": {
            "skills": {"score": 95, "details": "Matched skills"},
            "experience": {"score": 90, "details": "5 years"},
            "education": {"score": 88, "details": "BS CS"},
        },
        "prompt_name": "candidate_fit_scoring",
        "prompt_version": "2.0.0",
        "model_version": "gpt-4o-2024-08-06",
        "input_tokens": 1000,
        "output_tokens": 500,
        "total_tokens": 1500,
        "latency_ms": 1200,
        "warnings": [],
    }

    score_service.score_repo.create_score.return_value = Score(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_candidate_id=job_candidate_id,
        fit_score=92,
        confidence=0.90,
        breakdown={
            "skills": {"score": 95, "weight": 0.40, "details": "Matched skills"},
            "experience": {"score": 90, "weight": 0.35, "details": "5 years"},
            "education": {"score": 88, "weight": 0.25, "details": "BS CS"},
        },
        explanation="Exceptional technical alignment.",
        skills_matched=["Python"],
        skills_missing=[],
        warnings=[],
        prompt_name="candidate_fit_scoring",
        prompt_version="2.0.0",
        model_version="gpt-4o-2024-08-06",
        is_current=True,
        created_at=datetime.datetime.now(datetime.UTC),
    )

    score_res = await score_service.score_candidate_sync(
        session=session,
        tenant_id=tenant_id,
        user_role="org_admin",
        job_id=job_id,
        candidate_id=candidate_id,
    )
    assert score_res.data.fit_score == 92

    # 4. Pipeline Stage Movement (Move to Interview)
    pipeline_service = PipelineService()
    pipeline_service.pipeline_repo = AsyncMock()
    pipeline_service.user_repo = AsyncMock()
    job_candidate_id = uuid.uuid4()
    to_stage_id = uuid.uuid4()

    pipeline_service.user_repo.get_by_id.return_value = AsyncMock(full_name="Alice Admin")

    pipeline_service.pipeline_repo.get_job_candidate_by_id.return_value = AsyncMock(
        id=job_candidate_id,
        candidate_id=candidate_id,
        job_id=job_id,
        current_stage_id=uuid.uuid4(),
        current_stage=None,
    )
    pipeline_service.pipeline_repo.get_stage_by_id.return_value = PipelineStage(
        id=to_stage_id,
        tenant_id=tenant_id,
        job_id=job_id,
        name="Interview",
        position=2,
    )
    pipeline_service.pipeline_repo.update_job_candidate_stage.return_value = AsyncMock(
        id=job_candidate_id
    )

    pipeline_service.pipeline_repo.move_candidate_stage.return_value = MoveCandidateStageResponse(
        data=MoveCandidateStageData(
            job_candidate_id=job_candidate_id,
            previous_stage=None,
            current_stage=StageInfo(id=to_stage_id, name="Interview", position=2),
            moved_by=UserInfo(id=user_id, full_name="Alice Admin"),
            note="Promoted to Technical Interview",
            moved_at=datetime.datetime.now(datetime.UTC),
        )
    )

    move_res = await pipeline_service.move_candidate_stage(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        user_role="org_admin",
        job_candidate_id=job_candidate_id,
        to_stage_id=to_stage_id,
        note="Promoted to Technical Interview",
    )
    assert move_res.data.note == "Promoted to Technical Interview"

    # 5. Candidate Note Addition
    note_service = NoteService()
    note_service.note_repo = AsyncMock()
    note_service.candidate_repo = AsyncMock()
    note_service.candidate_repo.get_candidate_by_id.return_value = AsyncMock(id=candidate_id)
    created_note = CandidateNote(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        author_id=user_id,
        content="Passed technical interview with high marks.",
        is_private=False,
        is_archived=False,
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    created_note.author = User(id=user_id, full_name="Alice Admin", email="admin@example.com")
    note_service.note_repo.create_note.return_value = created_note
    note_service.note_repo.get_note_by_id.return_value = created_note

    note_res = await note_service.create_note(
        session=session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        user_id=user_id,
        content="Passed technical interview with high marks.",
    )
    assert note_res.data.content == "Passed technical interview with high marks."

    # 6. Candidate Tag Addition
    tag_service = TagService()
    tag_service.tag_repo = AsyncMock()
    tag_service.tag_repo.get_candidate_tag_by_name.return_value = None
    tag_service.candidate_repo = AsyncMock()
    tag_service.candidate_repo.get_candidate_by_id.return_value = AsyncMock(id=candidate_id)
    created_tag = CandidateTag(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        tagged_by=user_id,
        tag_name="top-tier",
        created_at=datetime.datetime.now(datetime.UTC),
    )
    created_tag.user = User(id=user_id, full_name="Alice Admin", email="admin@example.com")
    tag_service.tag_repo.add_tag.return_value = created_tag
    tag_service.tag_repo.get_tag_by_id.return_value = created_tag

    tag_res = await tag_service.add_tag(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        user_role="org_admin",
        candidate_id=candidate_id,
        tag_name="top-tier",
    )
    assert tag_res.data.tag_name == "top-tier"

    # 7. Audit Log Retrieval
    audit_service = AuditService()
    audit_service.audit_repo = AsyncMock()
    audit_service.audit_repo.list_audit_logs.return_value = (
        [
            AsyncMock(
                id=uuid.uuid4(),
                action="stage_changed",
                entity_type="job_candidate",
                entity_id=candidate_id,
                actor=AsyncMock(id=user_id, full_name="Alice Admin"),
                changes={"note": "Promoted"},
                ip_address="127.0.0.1",
                created_at=datetime.datetime.now(datetime.UTC),
            )
        ],
        False,
        None,
    )

    audit_res = await audit_service.list_audit_logs(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        user_role="org_admin",
    )
    assert len(audit_res.data) == 1
    assert audit_res.data[0].action == "stage_changed"

    # 8. AI Usage Summary Retrieval
    ai_usage_service = AIUsageService()
    ai_usage_service.usage_repo = AsyncMock()
    ai_usage_service.usage_repo.get_summary_metrics.return_value = (0.015, 1200, 1, 0.0)
    ai_usage_service.usage_repo.get_operation_breakdown.return_value = [
        ("candidate_scoring", 1, 0.015, 1200)
    ]
    ai_usage_service.usage_repo.get_daily_breakdown.return_value = [("2026-07-30", 0.015, 1)]

    usage_res = await ai_usage_service.get_usage_summary(
        session=session,
        tenant_id=tenant_id,
        user_role="org_admin",
    )
    assert usage_res.data.total_cost_usd == 0.015

    # 9. Dashboard Summary Metrics Verification
    dashboard_service = DashboardService()
    dashboard_service.dashboard_repo = AsyncMock()
    dashboard_service.dashboard_repo.get_open_jobs_count.return_value = 1
    dashboard_service.dashboard_repo.get_total_candidates_count.return_value = 1
    dashboard_service.dashboard_repo.get_scored_candidates_count.return_value = 1
    dashboard_service.dashboard_repo.get_shortlisted_candidates_count.return_value = 1
    dashboard_service.dashboard_repo.get_hired_candidates_count.return_value = 0
    dashboard_service.dashboard_repo.get_dashboard_metrics_consolidated.return_value = (
        1,
        1,
        1,
        1,
        0,
    )
    dashboard_service.dashboard_repo.get_top_jobs_pipeline_overviews.return_value = []
    dashboard_service.dashboard_repo.get_score_distribution_stats.return_value = (1, 0, 0, 1, 92.0)
    dashboard_service.dashboard_repo.get_recent_activity_feed.return_value = []

    dash_res = await dashboard_service.get_dashboard_summary(session=session, tenant_id=tenant_id)
    assert dash_res.data.metrics.open_jobs_count == 1
    assert dash_res.data.metrics.total_candidates_count == 1
    assert dash_res.data.metrics.scored_candidates_count == 1
