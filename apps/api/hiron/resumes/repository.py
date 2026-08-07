"""Resume repository providing tenant-isolated persistence operations for resumes and resume files."""

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hiron.resumes.models import Resume, ResumeFile


class ResumeRepository:
    """Data access repository for Resume and ResumeFile entities."""

    async def create_resume(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        status: str = "pending",
        raw_text_hash: str | None = None,
        is_primary: bool = True,
    ) -> Resume:
        """Create a new Resume entity in database."""
        if is_primary:
            await self.unset_primary_resumes(session, tenant_id, candidate_id)

        resume = Resume(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            status=status,
            raw_text_hash=raw_text_hash,
            is_primary=is_primary,
        )
        session.add(resume)
        await session.flush()
        return resume

    async def create_resume_file(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        resume_id: uuid.UUID,
        s3_bucket: str,
        s3_key: str,
        original_filename: str,
        content_type: str,
        file_size_bytes: int,
        checksum_sha256: str,
    ) -> ResumeFile:
        """Create a new ResumeFile metadata entity in database."""
        resume_file = ResumeFile(
            tenant_id=tenant_id,
            resume_id=resume_id,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            original_filename=original_filename,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            checksum_sha256=checksum_sha256,
        )
        session.add(resume_file)
        await session.flush()
        return resume_file

    async def get_resume_by_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        resume_id: uuid.UUID,
    ) -> Resume | None:
        """Fetch resume entity by ID within tenant context."""
        stmt = (
            select(Resume)
            .options(selectinload(Resume.file), selectinload(Resume.candidate))
            .where(
                Resume.id == resume_id,
                Resume.tenant_id == tenant_id,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_resume_file_by_resume_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        resume_id: uuid.UUID,
    ) -> ResumeFile | None:
        """Fetch resume file metadata by resume ID within tenant context."""
        stmt = select(ResumeFile).where(
            ResumeFile.resume_id == resume_id,
            ResumeFile.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_file_by_checksum(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        checksum_sha256: str,
    ) -> ResumeFile | None:
        """Find existing resume file by SHA-256 checksum for idempotency check."""
        stmt = (
            select(ResumeFile)
            .options(selectinload(ResumeFile.resume))
            .where(
                ResumeFile.checksum_sha256 == checksum_sha256,
                ResumeFile.tenant_id == tenant_id,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def unset_primary_resumes(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> None:
        """Unset is_primary for all existing resumes of a candidate within tenant context."""
        stmt = (
            update(Resume)
            .where(
                Resume.candidate_id == candidate_id,
                Resume.tenant_id == tenant_id,
                Resume.is_primary.is_(True),
            )
            .values(is_primary=False)
        )
        await session.execute(stmt)

    async def update_resume_status(
        self,
        session: AsyncSession,
        resume: Resume,
        status: str,
        parse_error: str | None = None,
        parsed_data: dict[str, Any] | None = None,
        parse_confidence: float | None = None,
        parser_model_version: str | None = None,
        raw_text: str | None = None,
        raw_text_hash: str | None = None,
    ) -> Resume:
        """Update processing status and parse results on resume entity."""
        resume.status = status
        if parse_error is not None:
            resume.parse_error = parse_error
        if parsed_data is not None:
            resume.parsed_data = parsed_data
        if parse_confidence is not None:
            resume.parse_confidence = parse_confidence
        if parser_model_version is not None:
            resume.parser_model_version = parser_model_version
        if raw_text is not None:
            resume.raw_text = raw_text
        if raw_text_hash is not None:
            resume.raw_text_hash = raw_text_hash

        await session.flush()
        return resume

    async def get_resumes_by_candidate_id(
        self, session: AsyncSession, tenant_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> list[Resume]:
        """Get all resumes for a specific candidate."""
        stmt = (
            select(Resume)
            .where(Resume.tenant_id == tenant_id, Resume.candidate_id == candidate_id)
            .order_by(Resume.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
