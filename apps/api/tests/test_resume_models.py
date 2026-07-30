"""Unit tests for Resume and ResumeFile SQLAlchemy ORM models."""

import uuid

from hiron.resumes.models import Resume, ResumeFile


def test_resume_model_instantiation() -> None:
    """Verify Resume model attributes, defaults, and table name."""
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    resume = Resume(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        status="pending",
        is_primary=True,
    )

    assert resume.__tablename__ == "resumes"
    assert resume.tenant_id == tenant_id
    assert resume.candidate_id == candidate_id
    assert resume.status == "pending"
    assert resume.is_primary is True
    assert resume.parsed_data is None


def test_resume_file_model_instantiation() -> None:
    """Verify ResumeFile model attributes and table name."""
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    file_meta = ResumeFile(
        tenant_id=tenant_id,
        resume_id=resume_id,
        s3_bucket="hiron-resumes",
        s3_key=f"{tenant_id}/resume.pdf",
        original_filename="resume.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        checksum_sha256="abc123sha256",
    )

    assert file_meta.__tablename__ == "resume_files"
    assert file_meta.tenant_id == tenant_id
    assert file_meta.resume_id == resume_id
    assert file_meta.original_filename == "resume.pdf"
    assert file_meta.content_type == "application/pdf"
    assert file_meta.file_size_bytes == 1024
    assert file_meta.checksum_sha256 == "abc123sha256"
