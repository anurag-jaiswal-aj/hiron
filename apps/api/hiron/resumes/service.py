"""Resume domain business service handling file validation, S3 storage, placeholder candidate creation, candidate-job assignment, and parsing workflow."""

import hashlib
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.candidates.models import Candidate
from hiron.candidates.repository import CandidateRepository
from hiron.candidates.service import CandidateService
from hiron.common.exceptions import ResourceNotFoundException, ValidationException
from hiron.jobs.repository import JobRepository
from hiron.resumes.exceptions import (
    FileTooLargeError,
    InsufficientResumePermissionsError,
    ResumeNotFoundError,
    ResumeParseFailedError,
    UnsupportedFileTypeError,
)
from hiron.resumes.models import Resume
from hiron.resumes.repository import ResumeRepository
from hiron.resumes.schemas import (
    BulkRejectionItem,
    BulkUploadResumeResponse,
    ResumeStatusResponse,
    UploadResumeResponse,
)
from hiron.storage.provider import StorageProvider

logger = structlog.get_logger("hiron.resumes.service")

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per Engineering Guidelines §15.2
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class ResumeService:
    """Business service managing resume storage, candidate binding, and status tracking."""

    def __init__(
        self,
        resume_repository: ResumeRepository | None = None,
        candidate_repository: CandidateRepository | None = None,
        job_repository: JobRepository | None = None,
        candidate_service: CandidateService | None = None,
        storage_provider: StorageProvider | None = None,
    ) -> None:
        self.resume_repo = resume_repository or ResumeRepository()
        self.candidate_repo = candidate_repository or CandidateRepository()
        self.job_repo = job_repository or JobRepository()
        self.candidate_service = candidate_service or CandidateService()
        self.storage_provider = storage_provider

    def _validate_role_permissions(self, role: str) -> None:
        """Validate that user has recruiter or org_admin permissions."""
        if role not in ("org_admin", "recruiter"):
            raise InsufficientResumePermissionsError(
                f"User with role '{role}' is not authorized to perform resume operations"
            )

    def validate_file(self, filename: str, content_type: str, file_size_bytes: int) -> None:
        """Validate file size limit and MIME type / extension."""
        if file_size_bytes > MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(
                f"File '{filename}' exceeds maximum allowed size of 10 MB ({file_size_bytes} bytes)"
            )

        ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
        if content_type not in ALLOWED_CONTENT_TYPES and ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"File '{filename}' with type '{content_type}' is not supported. Allowed types: PDF, DOCX, TXT."
            )

    def _determine_content_type(self, filename: str, content_type: str) -> str:
        """Normalize content type based on extension fallback."""
        if content_type in ALLOWED_CONTENT_TYPES:
            return content_type
        ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
        if ext == ".pdf":
            return "application/pdf"
        if ext == ".docx":
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if ext == ".txt":
            return "text/plain"
        return content_type

    def _get_extension(self, filename: str, content_type: str) -> str:
        """Get sanitized file extension for storage key."""
        if content_type == "application/pdf":
            return "pdf"
        if (
            content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            return "docx"
        if content_type == "text/plain":
            return "txt"
        if "." in filename:
            return filename.split(".")[-1].lower()
        return "bin"



    async def _enqueue_parse_task(self, tenant_id: uuid.UUID, resume_id: uuid.UUID) -> str:
        """Enqueue parsing task via QStash Webhook."""
        from hiron.core.config import get_settings
        from hiron.core.qstash_client import qstash_publisher

        settings = get_settings()
        worker_base_url = settings.worker_url or settings.qstash_webhook_url
        if not worker_base_url:
            logger.error("No worker_url or qstash_webhook_url configured")
            return f"task-{uuid.uuid4()}"

        payload = {
            "tenant_id": str(tenant_id),
            "resume_id": str(resume_id),
        }

        # Normalize URL to prevent double slashes
        base = worker_base_url.rstrip("/")
        webhook_url = f"{base}/api/v1/webhooks/qstash/resumes/parse"

        task_id = await qstash_publisher.publish(
            url=webhook_url,
            payload=payload,
            deduplication_id=f"parse-resume-{resume_id}-{uuid.uuid4()}",
        )
        return task_id or f"task-{uuid.uuid4()}"

    async def upload_resume(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        filename: str,
        content_type: str,
        file_bytes: bytes,
        candidate_id: uuid.UUID | None = None,
        job_id: uuid.UUID | None = None,
    ) -> UploadResumeResponse:
        """Upload a single resume file, create/bind candidate, persist metadata, and trigger parsing pipeline."""
        self._validate_role_permissions(user_role)
        self.validate_file(filename, content_type, len(file_bytes))
        normalized_content_type = self._determine_content_type(filename, content_type)

        checksum_sha256 = hashlib.sha256(file_bytes).hexdigest()

        # Idempotency check: if file already exists in tenant, return existing resume response
        existing_file = await self.resume_repo.find_file_by_checksum(
            session=session,
            tenant_id=tenant_id,
            checksum_sha256=checksum_sha256,
        )
        if existing_file and existing_file.resume:
            logger.info(
                "Idempotent resume upload match detected",
                tenant_id=str(tenant_id),
                checksum=checksum_sha256,
                resume_id=str(existing_file.resume_id),
            )
            return UploadResumeResponse(
                resume_id=existing_file.resume_id,
                candidate_id=existing_file.resume.candidate_id,
                task_id=f"task-{uuid.uuid4()}",
                status=existing_file.resume.status,
                status_url=f"/api/v1/resumes/{existing_file.resume_id}/status",
            )

        # 1. Resolve Candidate
        if candidate_id is not None:
            candidate = await self.candidate_repo.get_candidate_by_id(
                session=session,
                candidate_id=candidate_id,
                tenant_id=tenant_id,
            )
            if not candidate:
                raise ResourceNotFoundException(f"Candidate with ID '{candidate_id}' not found")
        else:
            # Create placeholder candidate from filename
            name_stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
            placeholder_name = name_stem if name_stem.strip() else "Placeholder Candidate"
            new_candidate = Candidate(
                tenant_id=tenant_id,
                full_name=placeholder_name,
                source="upload",
            )
            candidate = await self.candidate_repo.create_candidate(
                session=session,
                candidate=new_candidate,
            )

        # 2. Resolve Job association if job_id provided
        if job_id is not None:
            job = await self.job_repo.get_job_by_id(
                session=session,
                job_id=job_id,
                tenant_id=tenant_id,
            )
            if not job:
                raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")
            await self.candidate_service.add_candidate_to_job(
                session=session,
                job_id=job_id,
                candidate_id=candidate.id,
                tenant_id=tenant_id,
                current_user_role=user_role,
            )

        # 3. Create Resume database entity
        resume = await self.resume_repo.create_resume(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate.id,
            status="pending",
            raw_text_hash=checksum_sha256,
            is_primary=True,
        )

        # 4. Storage upload
        ext = self._get_extension(filename, normalized_content_type)
        storage_key = f"{resume.id}/original.{ext}"
        bucket_name = "hiron-resumes"
        if self.storage_provider:
            await self.storage_provider.upload_file(
                tenant_id=tenant_id,
                key=storage_key,
                file_data=file_bytes,
                content_type=normalized_content_type,
            )

        # 5. Create ResumeFile metadata entity
        await self.resume_repo.create_resume_file(
            session=session,
            tenant_id=tenant_id,
            resume_id=resume.id,
            s3_bucket=bucket_name,
            s3_key=f"{tenant_id}/{storage_key}",
            original_filename=filename,
            content_type=normalized_content_type,
            file_size_bytes=len(file_bytes),
            checksum_sha256=checksum_sha256,
        )

        # 6. Commit transaction before enqueueing background task so worker can read metadata
        await session.commit()

        # 7. Enqueue background QStash task
        try:
            task_id = await self._enqueue_parse_task(tenant_id=tenant_id, resume_id=resume.id)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error("Failed to enqueue parse task", error=str(e), exc_info=True)
            task_id = f"task-{uuid.uuid4()}"

        return UploadResumeResponse(
            resume_id=resume.id,
            candidate_id=candidate.id,
            task_id=task_id,
            status=resume.status,
            status_url=f"/api/v1/resumes/{resume.id}/status",
        )

    async def bulk_upload_resumes(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        files: list[tuple[str, str, bytes]],
        job_id: uuid.UUID | None = None,
    ) -> BulkUploadResumeResponse:
        """Batch upload up to 500 resumes per API Contract §RES-2."""
        self._validate_role_permissions(user_role)

        if len(files) > 500:
            raise ValidationException("Bulk upload cannot exceed 500 files per request")

        if job_id is not None:
            job = await self.job_repo.get_job_by_id(
                session=session,
                job_id=job_id,
                tenant_id=tenant_id,
            )
            if not job:
                raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        accepted_count = 0
        rejections: list[BulkRejectionItem] = []

        for filename, content_type, file_bytes in files:
            file_size = len(file_bytes)
            if file_size > MAX_FILE_SIZE_BYTES:
                rejections.append(
                    BulkRejectionItem(filename=filename, reason="File exceeds 10 MB limit")
                )
                continue

            ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
            if content_type not in ALLOWED_CONTENT_TYPES and ext not in ALLOWED_EXTENSIONS:
                rejections.append(
                    BulkRejectionItem(filename=filename, reason="Unsupported file type")
                )
                continue

            try:
                await self.upload_resume(
                    session=session,
                    tenant_id=tenant_id,
                    user_role=user_role,
                    filename=filename,
                    content_type=content_type,
                    file_bytes=file_bytes,
                    candidate_id=None,
                    job_id=job_id,
                )
                accepted_count += 1
            except Exception as exc:
                logger.warning(
                    "Bulk resume upload file processing failed",
                    filename=filename,
                    error=str(exc),
                )
                rejections.append(
                    BulkRejectionItem(filename=filename, reason=f"Upload failed: {exc}")
                )

        task_id = f"task-{uuid.uuid4()}"
        return BulkUploadResumeResponse(
            task_id=task_id,
            total_files=len(files),
            accepted=accepted_count,
            rejected=len(rejections),
            rejections=rejections,
            status_url=f"/api/v1/tasks/{task_id}",
        )

    async def get_resume_status(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        resume_id: uuid.UUID,
    ) -> ResumeStatusResponse:
        """Fetch resume parsing status and extracted structured data per API Contract §RES-3."""
        resume = await self.resume_repo.get_resume_by_id(
            session=session,
            tenant_id=tenant_id,
            resume_id=resume_id,
        )
        if not resume:
            raise ResumeNotFoundError(f"Resume with ID '{resume_id}' not found")

        return ResumeStatusResponse(
            resume_id=resume.id,
            status=resume.status,
            parse_confidence=resume.parse_confidence,
            parsed_data=resume.parsed_data,
            parse_error=resume.parse_error,
            parser_model_version=resume.parser_model_version,
            created_at=resume.created_at,
        )

    async def retry_parse(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        resume_id: uuid.UUID,
    ) -> UploadResumeResponse:
        """Retry parsing for a failed resume per API Contract §RES-4."""
        self._validate_role_permissions(user_role)

        resume = await self.resume_repo.get_resume_by_id(
            session=session,
            tenant_id=tenant_id,
            resume_id=resume_id,
        )
        if not resume:
            raise ResumeNotFoundError(f"Resume with ID '{resume_id}' not found")

        if resume.status != "failed":
            raise ValidationException(
                f"Resume status is '{resume.status}'. Only failed resumes can be retried."
            )

        # Set status back to pending and clear error
        await self.resume_repo.update_resume_status(
            session=session,
            resume=resume,
            status="pending",
            parse_error="",
        )
        await session.commit()

        # Enqueue background QStash task
        task_id = self._enqueue_parse_task(tenant_id=tenant_id, resume_id=resume.id)

        return UploadResumeResponse(
            resume_id=resume.id,
            candidate_id=resume.candidate_id,
            task_id=task_id,
            status="pending",
            status_url=f"/api/v1/resumes/{resume.id}/status",
        )

    async def get_resumes_by_candidate(
        self, session: AsyncSession, tenant_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> list[ResumeStatusResponse]:
        """Get all resumes for a candidate per API Contract extension."""
        resumes = await self.resume_repo.get_resumes_by_candidate_id(
            session=session, tenant_id=tenant_id, candidate_id=candidate_id
        )
        return [
            ResumeStatusResponse(
                resume_id=r.id,
                status=r.status,
                parse_confidence=r.parse_confidence,
                parsed_data=r.parsed_data,
                parse_error=r.parse_error,
                parser_model_version=r.parser_model_version,
                created_at=r.created_at,
            )
            for r in resumes
        ]
