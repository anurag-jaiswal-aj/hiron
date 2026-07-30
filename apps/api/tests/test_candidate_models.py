"""Unit tests for Candidate and JobCandidate SQLAlchemy ORM models."""

import uuid

from hiron.candidates.models import Candidate, JobCandidate


def test_candidate_model_instantiation() -> None:
    """Verify Candidate model attributes, default source, skills, and table name."""
    tenant_id = uuid.uuid4()
    candidate = Candidate(
        tenant_id=tenant_id,
        full_name="Jane Doe",
        email="jane@example.com",
        skills=["Python", "FastAPI"],
        total_experience_years=5,
        source="upload",
        is_archived=False,
    )

    assert candidate.__tablename__ == "candidates"
    assert candidate.tenant_id == tenant_id
    assert candidate.full_name == "Jane Doe"
    assert candidate.email == "jane@example.com"
    assert candidate.skills == ["Python", "FastAPI"]
    assert candidate.total_experience_years == 5
    assert candidate.source == "upload"
    assert candidate.is_archived is False


def test_job_candidate_model_instantiation() -> None:
    """Verify JobCandidate junction model attributes and table name."""
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    stage_id = uuid.uuid4()

    assoc = JobCandidate(
        tenant_id=tenant_id,
        job_id=job_id,
        candidate_id=candidate_id,
        current_stage_id=stage_id,
        is_shortlisted=False,
        is_archived=False,
    )

    assert assoc.__tablename__ == "job_candidates"
    assert assoc.tenant_id == tenant_id
    assert assoc.job_id == job_id
    assert assoc.candidate_id == candidate_id
    assert assoc.current_stage_id == stage_id
    assert assoc.is_shortlisted is False
    assert assoc.is_archived is False
