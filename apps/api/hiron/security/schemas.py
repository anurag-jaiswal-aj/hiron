"""Pydantic schemas for Security Audit Report per Phase 16."""

from pydantic import BaseModel, ConfigDict, Field


class SecurityCheckResult(BaseModel):
    """Single security control audit item."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(...)
    category: str = Field(...)
    status: str = Field(...)  # "PASSED", "WARNING", "FAILED"
    details: str = Field(...)


class SecurityAuditReportData(BaseModel):
    """Payload of security audit report."""

    model_config = ConfigDict(populate_by_name=True)

    checks: list[SecurityCheckResult] = Field(...)
    overall_score: int = Field(..., serialization_alias="overallScore")
    compliance_status: str = Field(..., serialization_alias="complianceStatus")


class SecurityAuditReportResponse(BaseModel):
    """Response wrapper for security audit report."""

    data: SecurityAuditReportData = Field(...)
