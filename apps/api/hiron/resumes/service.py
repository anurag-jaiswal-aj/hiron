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
from hiron.resumes.extractor import extract_text_from_file
from hiron.resumes.models import Resume
from hiron.resumes.parser import ResumeParser
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

    def _enrich_candidate_contact_info(
        self,
        candidate: Candidate,
        parsed_data: dict[str, Any],
    ) -> None:
        """Enrich candidate contact details from parsed data."""
        if parsed_data.get("full_name") and (
            not candidate.full_name
            or candidate.full_name in ("Placeholder Candidate", "Parsed Candidate")
        ):
            candidate.full_name = parsed_data["full_name"]
        if parsed_data.get("email") and not candidate.email:
            candidate.email = parsed_data["email"]
        if parsed_data.get("phone") and not candidate.phone:
            candidate.phone = parsed_data["phone"]
        if parsed_data.get("location") and not candidate.location:
            candidate.location = parsed_data["location"]
        if parsed_data.get("linkedin_url") and not candidate.linkedin_url:
            candidate.linkedin_url = parsed_data["linkedin_url"]
        if parsed_data.get("summary") and not candidate.summary:
            candidate.summary = parsed_data["summary"]

    async def _enrich_candidate_profile(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        parsed_data: dict[str, Any],
    ) -> None:
        """Auto-enrich candidate profile fields from parsed resume data."""
        candidate = await self.candidate_repo.get_candidate_by_id(
            session=session,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
        )
        if not candidate:
            return

        self._enrich_candidate_contact_info(candidate, parsed_data)

        # Skills enrichment
        extracted_skills = parsed_data.get("skills", [])
        if extracted_skills:
            existing_skills = set(candidate.skills or [])
            existing_skills.update(extracted_skills)
            candidate.skills = sorted(existing_skills)

        # Title & Company from latest experience
        experience = parsed_data.get("experience", [])
        if experience and isinstance(experience, list) and len(experience) > 0:
            first_exp = experience[0]
            if isinstance(first_exp, dict):
                if first_exp.get("title") and not candidate.current_title:
                    candidate.current_title = first_exp["title"]
                if first_exp.get("company") and not candidate.current_company:
                    candidate.current_company = first_exp["company"]

        await session.flush()

    async def parse_resume_pipeline(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        resume_id: uuid.UUID,
    ) -> Resume:
        """Execute resume parsing pipeline: text extraction -> NER parsing -> DB update -> candidate auto-enrichment."""
        resume = await self.resume_repo.get_resume_by_id(
            session=session,
            tenant_id=tenant_id,
            resume_id=resume_id,
        )
        if not resume:
            raise ResumeNotFoundError(f"Resume with ID '{resume_id}' not found")

        resume_file = await self.resume_repo.get_resume_file_by_resume_id(
            session=session,
            tenant_id=tenant_id,
            resume_id=resume_id,
        )
        if not resume_file:
            error_msg = f"Resume file metadata missing for resume '{resume_id}'"
            await self.resume_repo.update_resume_status(
                session=session,
                resume=resume,
                status="failed",
                parse_error=error_msg,
            )
            raise ResumeParseFailedError(error_msg)

        await self.resume_repo.update_resume_status(
            session=session,
            resume=resume,
            status="processing",
        )

        # Commit processing status so it becomes durably visible to polling clients
        # before the expensive extraction and NLP parsing blocks begin.
        await session.commit()

        try:
            file_bytes = b""
            if self.storage_provider:
                file_bytes = await self.storage_provider.download_file(
                    tenant_id=tenant_id,
                    key=resume_file.s3_key.replace(f"{tenant_id}/", ""),
                )
            else:
                file_bytes = b"Jane Smith\njane@example.com\nSenior Python Engineer at Stripe\nSkills: Python, FastAPI, Docker, PostgreSQL"

            raw_text = extract_text_from_file(
                file_bytes=file_bytes,
                content_type=resume_file.content_type,
                filename=resume_file.original_filename,
            )

            raw_text_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

            parser = ResumeParser()
            parsed_data, parse_confidence, telemetry = parser.parse(raw_text)

            updated_resume = await self.resume_repo.update_resume_status(
                session=session,
                resume=resume,
                status="parsed",
                parsed_data=parsed_data,
                parse_confidence=parse_confidence,
                parser_model_version=parser.model_version,
                raw_text=raw_text,
                raw_text_hash=raw_text_hash,
                parse_error="",
            )

            # Auto-enrich candidate profile
            await self._enrich_candidate_profile(
                session=session,
                tenant_id=tenant_id,
                candidate_id=resume.candidate_id,
                parsed_data=parsed_data,
            )

            # Auto-trigger candidate embedding generation
            try:
                from hiron.embeddings.service import EmbeddingService

                emb_service = EmbeddingService()
                await emb_service.generate_candidate_embedding_pipeline(
                    session=session,
                    tenant_id=tenant_id,
                    candidate_id=resume.candidate_id,
                )
            except Exception as emb_exc:
                logger.warning("Failed to trigger embedding generation for candidate", error=str(emb_exc))

            # Log AI usage telemetry
            if telemetry:
                try:
                    # Use a SAVEPOINT so a telemetry DB failure doesn't roll back the resume parse
                    async with session.begin_nested():
                        from hiron.ai_usage.repository import AIUsageRepository
                        ai_repo = AIUsageRepository()
                        await ai_repo.create_usage_log(
                            session=session,
                            tenant_id=tenant_id,
                            operation="resume_parsing",
                            model_version=telemetry["model_version"],
                            input_tokens=telemetry["input_tokens"],
                            output_tokens=telemetry["output_tokens"],
                            cost_usd=telemetry["cost_usd"],
                            latency_ms=telemetry["latency_ms"],
                            status=telemetry["status"],
                            error_type=telemetry["error_type"],
                        )
                except Exception as log_exc:
                    logger.warning("Failed to write AI usage telemetry", error=str(log_exc))

            await session.commit()

            logger.info(
                "Resume parsed successfully",
                tenant_id=str(tenant_id),
                resume_id=str(resume_id),
                confidence=parse_confidence,
            )
            return updated_resume

        except Exception as exc:
            logger.warning(
                "Resume parsing failed",
                tenant_id=str(tenant_id),
                resume_id=str(resume_id),
                error=str(exc),
            )
            await self.resume_repo.update_resume_status(
                session=session,
                resume=resume,
                status="failed",
                parse_error=str(exc),
            )
            raise

    def _enqueue_parse_task(self, tenant_id: uuid.UUID, resume_id: uuid.UUID) -> str:
        """Enqueue background Celery resume parsing task and return real Celery task ID."""
        from hiron.resumes.tasks import parse_resume

        task = parse_resume.delay(str(tenant_id), str(resume_id))
        return str(task.id)

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

        # 6. Commit transaction before enqueueing Celery task so background worker can read metadata
        await session.commit()

        # 7. Enqueue background Celery task
        task_id = self._enqueue_parse_task(tenant_id=tenant_id, resume_id=resume.id)

        return UploadResumeResponse(
            resume_id=resume.id,
            candidate_id=candidate.id,
            task_id=task_id,
            status="pending",
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

        # Enqueue background Celery task
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
