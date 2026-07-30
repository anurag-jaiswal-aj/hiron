"""Note repository managing SQL persistence and private note filtering per Database Design §5.14."""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hiron.notes.models import CandidateNote


class NoteRepository:
    """Repository handling SQL persistence for candidate notes."""

    async def create_note(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
        job_id: uuid.UUID | None = None,
        is_private: bool = False,
    ) -> CandidateNote:
        """Create and persist a new CandidateNote."""
        note = CandidateNote(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            author_id=author_id,
            job_id=job_id,
            content=content,
            is_private=is_private,
            is_archived=False,
        )
        session.add(note)
        await session.flush()
        return note

    async def list_candidate_notes(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        user_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
    ) -> list[CandidateNote]:
        """Fetch candidate notes ordered by created_at DESC with private notes filtering."""
        stmt = (
            select(CandidateNote)
            .where(
                CandidateNote.tenant_id == tenant_id,
                CandidateNote.candidate_id == candidate_id,
                CandidateNote.is_archived.is_(False),
                or_(
                    CandidateNote.is_private.is_(False),
                    CandidateNote.author_id == user_id,
                ),
            )
            .options(selectinload(CandidateNote.author))
            .order_by(CandidateNote.created_at.desc())
        )
        if job_id:
            stmt = stmt.where(CandidateNote.job_id == job_id)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_note_by_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        note_id: uuid.UUID,
    ) -> CandidateNote | None:
        """Fetch note by ID with author loaded."""
        stmt = (
            select(CandidateNote)
            .where(
                CandidateNote.tenant_id == tenant_id,
                CandidateNote.id == note_id,
                CandidateNote.is_archived.is_(False),
            )
            .options(selectinload(CandidateNote.author))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_note(
        self,
        session: AsyncSession,
        note: CandidateNote,
        content: str | None = None,
        is_private: bool | None = None,
    ) -> CandidateNote:
        """Update candidate note content or privacy flag."""
        if content is not None:
            note.content = content
        if is_private is not None:
            note.is_private = is_private
        await session.flush()
        return note

    async def archive_note(
        self,
        session: AsyncSession,
        note: CandidateNote,
    ) -> None:
        """Soft delete (archive) candidate note."""
        note.is_archived = True
        await session.flush()
