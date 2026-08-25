"""FastAPI API endpoints for Resume Upload and status polling per API Contract §RES-1..RES-4."""

import typing
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.common.schemas import ResponseEnvelope
from hiron.core.config import get_settings
from hiron.core.database import get_db_session
from hiron.resumes.schemas import (
    BatchStatusRequest,
    BatchStatusResponse,
    BulkUploadResumeResponse,
    ResumeStatusResponse,
    UploadResumeResponse,
)
from hiron.resumes.service import ResumeService
from hiron.storage.provider import LocalStorageProvider, StorageProvider, SupabaseStorageProvider
from hiron.users.models import User

router = APIRouter(tags=["resumes"])

_storage_provider: StorageProvider | None = None


def get_resume_service() -> ResumeService:
    """Dependency provider for ResumeService."""
    global _storage_provider
    if _storage_provider is None:
        settings = get_settings()
        if settings.supabase_url and settings.supabase_service_role_key:
            _storage_provider = SupabaseStorageProvider(
                supabase_url=settings.supabase_url,
                supabase_service_role_key=settings.supabase_service_role_key,
                bucket_name=settings.supabase_storage_bucket,
            )
        else:
            _storage_provider = LocalStorageProvider()
    return ResumeService(storage_provider=_storage_provider)


@router.post(
    "/upload",
    response_model=ResponseEnvelope[UploadResumeResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_resume(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    resume_service: Annotated[ResumeService, Depends(get_resume_service)],
    candidateId: Annotated[str | None, Form()] = None,
    jobId: Annotated[str | None, Form()] = None,
) -> ResponseEnvelope[UploadResumeResponse]:
    """Upload a resume file, create/bind candidate, and trigger parsing per API Contract §RES-1."""
    parsed_candidate_id = uuid.UUID(candidateId) if candidateId else None
    parsed_job_id = uuid.UUID(jobId) if jobId else None

    file_size = file.size or 0
    filename = file.filename or "resume.pdf"
    content_type = file.content_type or "application/pdf"

    result = await resume_service.upload_resume(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        filename=filename,
        content_type=content_type,
        file_data=file.file,
        file_size_bytes=file_size,
        candidate_id=parsed_candidate_id,
        job_id=parsed_job_id,
    )

    return ResponseEnvelope(data=result)


@router.post(
    "/bulk-upload",
    response_model=ResponseEnvelope[BulkUploadResumeResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def bulk_upload_resumes(
    files: Annotated[list[UploadFile], File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    resume_service: Annotated[ResumeService, Depends(get_resume_service)],
    jobId: Annotated[str | None, Form()] = None,
) -> ResponseEnvelope[BulkUploadResumeResponse]:
    """Upload up to 500 resumes in a single bulk request per API Contract §RES-2."""
    parsed_job_id = uuid.UUID(jobId) if jobId else None

    file_tuples: list[tuple[str, str, bytes | typing.BinaryIO, int]] = []
    for f in files:
        fname = f.filename or "resume.pdf"
        ctype = f.content_type or "application/pdf"
        file_tuples.append((fname, ctype, f.file, f.size or 0))

    result = await resume_service.bulk_upload_resumes(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        files=file_tuples,
        job_id=parsed_job_id,
    )

    return ResponseEnvelope(data=result)


@router.get(
    "/{resume_id}/status",
    response_model=ResponseEnvelope[ResumeStatusResponse],
)
async def get_resume_status(
    resume_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    resume_service: Annotated[ResumeService, Depends(get_resume_service)],
) -> ResponseEnvelope[ResumeStatusResponse]:
    """Poll for resume parsing status completion per API Contract §RES-3."""
    result = await resume_service.get_resume_status(
        session=session,
        tenant_id=current_user.tenant_id,
        resume_id=resume_id,
    )

    return ResponseEnvelope(data=result)


@router.post(
    "/status/batch",
    response_model=ResponseEnvelope[BatchStatusResponse],
)
async def get_batch_resume_status(
    request: BatchStatusRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    resume_service: Annotated[ResumeService, Depends(get_resume_service)],
) -> ResponseEnvelope[BatchStatusResponse]:
    """Poll for multiple resume parsing statuses in batch."""
    items = await resume_service.get_batch_resume_status(
        session=session,
        tenant_id=current_user.tenant_id,
        resume_ids=request.resume_ids,
    )
    return ResponseEnvelope(data=BatchStatusResponse(items=items))


@router.post(
    "/{resume_id}/retry",
    response_model=ResponseEnvelope[UploadResumeResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_resume_parse(
    resume_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    resume_service: Annotated[ResumeService, Depends(get_resume_service)],
) -> ResponseEnvelope[UploadResumeResponse]:
    """Retry parsing for a failed resume per API Contract §RES-4."""
    result = await resume_service.retry_parse(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        resume_id=resume_id,
    )

    return ResponseEnvelope(data=result)


@router.get(
    "/candidate/{candidate_id}",
    response_model=ResponseEnvelope[list[ResumeStatusResponse]],
)
async def get_candidate_resumes(
    candidate_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    resume_service: Annotated[ResumeService, Depends(get_resume_service)],
) -> ResponseEnvelope[list[ResumeStatusResponse]]:
    """Get all resumes for a candidate to display in UI."""
    result = await resume_service.get_resumes_by_candidate(
        session=session,
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
    )
    return ResponseEnvelope(data=result)
