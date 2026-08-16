"""Note service managing privacy visibility filtering, author edit security, and note archiving per API Contract §NOTE-1..4."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.candidates.repository import CandidateRepository
from hiron.common.exceptions import ResourceNotFoundException
from hiron.audit.service import AuditService
from hiron.audit.utils import extract_model_changes, sanitize_audit_payload
from hiron.notes.exceptions import InsufficientNotePermissionsError, NoteValidationError
from hiron.notes.models import CandidateNote
from hiron.notes.repository import NoteRepository
from hiron.notes.schemas import NoteAuthorInfo, NoteData, NoteListResponse, NoteResponse

logger = structlog.get_logger("hiron.notes.service")


class NoteService:
    """Business service handling candidate notes, author permission checks, and private note security."""

    def __init__(
        self,
        note_repository: NoteRepository | None = None,
        candidate_repository: CandidateRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.note_repo = note_repository or NoteRepository()
        self.candidate_repo = candidate_repository or CandidateRepository()
        self.audit_service = audit_service or AuditService()

    def _build_note_data(self, note: CandidateNote) -> NoteData:
        """Convert CandidateNote ORM model to Pydantic NoteData schema."""
        author_info = (
            NoteAuthorInfo(id=note.author.id, full_name=note.author.full_name)
            if note.author
            else None
        )
        return NoteData(
            id=note.id,
            candidate_id=note.candidate_id,
            author=author_info,
            job_id=note.job_id,
            content=note.content,
            is_private=note.is_private,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    async def create_note(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        candidate_id: uuid.UUID,
        content: str,
        job_id: uuid.UUID | None = None,
        is_private: bool = False,
    ) -> NoteResponse:
        """Create and attach note to candidate per API Contract §NOTE-2."""
        if not content or not content.strip():
            raise NoteValidationError("Note content cannot be empty")

        candidate = await self.candidate_repo.get_candidate_by_id(
            session=session, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not candidate:
            raise ResourceNotFoundException(f"Candidate with ID '{candidate_id}' not found")

        note = await self.note_repo.create_note(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            author_id=user_id,
            job_id=job_id,
            content=content,
            is_private=is_private,
        )

        # Refetch with author loaded
        refetched = await self.note_repo.get_note_by_id(
            session=session, tenant_id=tenant_id, note_id=note.id
        )
        target_note = refetched or note

        logger.info(
            "Created candidate note",
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
            note_id=str(note.id),
            is_private=is_private,
        )
        
        changes = extract_model_changes(note, "create")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="note_created",
                entity_type="candidate_note",
                entity_id=note.id,
                actor_id=user_id,
                changes=changes,
            )
            
        await session.commit()
        return NoteResponse(data=self._build_note_data(target_note))

    async def list_candidate_notes(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
    ) -> NoteListResponse:
        """List notes on a candidate filtered by tenant and private note visibility per API Contract §NOTE-1."""
        candidate = await self.candidate_repo.get_candidate_by_id(
            session=session, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not candidate:
            raise ResourceNotFoundException(f"Candidate with ID '{candidate_id}' not found")

        notes = await self.note_repo.list_candidate_notes(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            user_id=user_id,
            job_id=job_id,
        )
        return NoteListResponse(data=[self._build_note_data(n) for n in notes])

    async def update_note(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        candidate_id: uuid.UUID,
        note_id: uuid.UUID,
        content: str | None = None,
        is_private: bool | None = None,
    ) -> NoteResponse:
        """Edit note (author only) per API Contract §NOTE-3."""
        note = await self.note_repo.get_note_by_id(
            session=session, tenant_id=tenant_id, note_id=note_id
        )
        if not note or note.candidate_id != candidate_id:
            raise ResourceNotFoundException(
                f"Note with ID '{note_id}' not found for this candidate"
            )

        if note.author_id != user_id:
            raise InsufficientNotePermissionsError("Only note author can edit note")

        if content is not None and not content.strip():
            raise NoteValidationError("Note content cannot be empty")

        updated = await self.note_repo.update_note(
            session=session, note=note, content=content, is_private=is_private
        )
        
        changes = extract_model_changes(updated, "update")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="note_updated",
                entity_type="candidate_note",
                entity_id=updated.id,
                actor_id=user_id,
                changes=changes,
            )
            
        await session.commit()
        return NoteResponse(data=self._build_note_data(updated))

    async def archive_note(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        candidate_id: uuid.UUID,
        note_id: uuid.UUID,
    ) -> None:
        """Soft-delete note (author or org_admin) per API Contract §NOTE-4."""
        note = await self.note_repo.get_note_by_id(
            session=session, tenant_id=tenant_id, note_id=note_id
        )
        if not note or note.candidate_id != candidate_id:
            raise ResourceNotFoundException(
                f"Note with ID '{note_id}' not found for this candidate"
            )

        if note.author_id != user_id and user_role != "org_admin":
            raise InsufficientNotePermissionsError("Only note author or org_admin can archive note")

        await self.note_repo.archive_note(session=session, note=note)
        logger.info(
            "Archived candidate note",
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
            note_id=str(note_id),
        )
        
        changes = extract_model_changes(note, "update")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="note_archived",
                entity_type="candidate_note",
                entity_id=note.id,
                actor_id=user_id,
                changes=changes,
            )
            
        await session.commit()
