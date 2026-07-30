"""Unit tests verifying Job and PipelineStage ORM model mappings, foreign keys, constraints, and indexes."""

from typing import cast

from sqlalchemy import Table

from hiron.common.models import BaseModel
from hiron.jobs.models import Job, PipelineStage


def test_job_model_inheritance() -> None:
    """Verify Job inherits from BaseModel and contains all required columns per Database Design §5.4."""
    assert issubclass(Job, BaseModel)
    assert hasattr(Job, "id")
    assert hasattr(Job, "tenant_id")
    assert hasattr(Job, "created_by")
    assert hasattr(Job, "title")
    assert hasattr(Job, "description")
    assert hasattr(Job, "department")
    assert hasattr(Job, "location")
    assert hasattr(Job, "employment_type")
    assert hasattr(Job, "experience_years_min")
    assert hasattr(Job, "experience_years_max")
    assert hasattr(Job, "required_skills")
    assert hasattr(Job, "preferred_skills")
    assert hasattr(Job, "extracted_requirements")
    assert hasattr(Job, "status")
    assert hasattr(Job, "is_archived")
    assert hasattr(Job, "search_vector")
    assert hasattr(Job, "opened_at")
    assert hasattr(Job, "closed_at")


def test_job_tablename() -> None:
    """Verify Job table name per Database Design §5.4."""
    assert Job.__tablename__ == "jobs"


def test_job_foreign_keys_definition() -> None:
    """Verify foreign keys defined on Job table per Database Design §5.4."""
    fks = Job.__table__.foreign_keys
    fk_targets = {fk.name: (fk.target_fullname, fk.ondelete) for fk in fks}

    assert "fk_jobs_tenant_id_tenants" in fk_targets
    assert fk_targets["fk_jobs_tenant_id_tenants"] == ("tenants.id", "CASCADE")

    assert "fk_jobs_created_by_users" in fk_targets
    assert fk_targets["fk_jobs_created_by_users"] == ("users.id", "SET NULL")


def test_job_indexes_definition() -> None:
    """Verify required indexes are defined on Job table per Database Design §5.4."""
    table = cast(Table, Job.__table__)
    index_names = [idx.name for idx in table.indexes]
    assert "ix_jobs_tenant_id" in index_names
    assert "ix_jobs_tenant_status" in index_names
    assert "ix_jobs_tenant_archived" in index_names
    assert "ix_jobs_search_vector" in index_names
    assert "ix_jobs_created_at" in index_names


def test_job_constraints_definition() -> None:
    """Verify check constraints defined on Job table per Database Design §5.4."""
    constraints = Job.__table_args__
    constraint_names = [getattr(c, "name", None) for c in constraints if hasattr(c, "name")]

    assert "ck_jobs_status" in constraint_names
    assert "ck_jobs_employment_type" in constraint_names
    assert "ck_jobs_experience_range" in constraint_names
    assert "ck_jobs_experience_min_range" in constraint_names
    assert "ck_jobs_experience_max_range" in constraint_names


def test_pipeline_stage_model_inheritance() -> None:
    """Verify PipelineStage inherits from BaseModel and contains all required columns per Database Design §5.8."""
    assert issubclass(PipelineStage, BaseModel)
    assert hasattr(PipelineStage, "id")
    assert hasattr(PipelineStage, "tenant_id")
    assert hasattr(PipelineStage, "job_id")
    assert hasattr(PipelineStage, "name")
    assert hasattr(PipelineStage, "position")
    assert hasattr(PipelineStage, "is_terminal")
    assert hasattr(PipelineStage, "stage_type")


def test_pipeline_stage_tablename() -> None:
    """Verify PipelineStage table name per Database Design §5.8."""
    assert PipelineStage.__tablename__ == "pipeline_stages"


def test_pipeline_stage_foreign_keys_definition() -> None:
    """Verify foreign keys defined on PipelineStage table per Database Design §5.8."""
    fks = PipelineStage.__table__.foreign_keys
    fk_targets = {fk.name: (fk.target_fullname, fk.ondelete) for fk in fks}

    assert "fk_pipeline_stages_tenant_id_tenants" in fk_targets
    assert fk_targets["fk_pipeline_stages_tenant_id_tenants"] == ("tenants.id", "CASCADE")

    assert "fk_pipeline_stages_job_id_jobs" in fk_targets
    assert fk_targets["fk_pipeline_stages_job_id_jobs"] == ("jobs.id", "CASCADE")


def test_pipeline_stage_constraints_definition() -> None:
    """Verify unique and check constraints defined on PipelineStage table per Database Design §5.8."""
    constraints = PipelineStage.__table_args__
    constraint_names = [getattr(c, "name", None) for c in constraints if hasattr(c, "name")]

    assert "job_position" in constraint_names
    assert "job_name" in constraint_names
    assert "ck_pipeline_stages_position" in constraint_names
    assert "ck_pipeline_stages_stage_type" in constraint_names


def test_pipeline_stage_indexes_definition() -> None:
    """Verify required indexes are defined on PipelineStage table per Database Design §5.8."""
    table = cast(Table, PipelineStage.__table__)
    index_names = [idx.name for idx in table.indexes]
    assert "ix_pipeline_stages_job_id" in index_names
    assert "ix_pipeline_stages_tenant_id" in index_names
