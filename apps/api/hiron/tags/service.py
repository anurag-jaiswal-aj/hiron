"""Tag service normalizing tag names, enforcing duplicate 409 conflict checks, and managing tags per API Contract §TAG-1..3."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.candidates.repository import CandidateRepository
from hiron.common.exceptions import ResourceNotFoundException
from hiron.tags.exceptions import DuplicateTagError, InsufficientTagPermissionsError
from hiron.tags.models import CandidateTag
from hiron.tags.repository import TagRepository
from hiron.tags.schemas import TagData, TagListResponse, TagResponse, TagUserPayload

logger = structlog.get_logger("hiron.tags.service")


class TagService:
    """Business service handling candidate tags, normalization, and duplicate prevention."""

    def __init__(
        self,
        tag_repository: TagRepository | None = None,
        candidate_repository: CandidateRepository | None = None,
    ) -> None:
        self.tag_repo = tag_repository or TagRepository()
        self.candidate_repo = candidate_repository or CandidateRepository()

    def _validate_role_permissions(self, role: str) -> None:
        """Validate that user role is authorized for tag modifications."""
        if role not in ("org_admin", "recruiter"):
            raise InsufficientTagPermissionsError(
                f"User with role '{role}' is not authorized for tag operations"
            )

    def _normalize_tag_name(self, raw_name: str) -> str:
        """Normalize tag name to lowercase and trimmed string."""
        return raw_name.strip().lower()

    def _build_tag_data(self, tag: CandidateTag) -> TagData:
        """Convert CandidateTag ORM model to Pydantic TagData schema."""
        user_info = (
            TagUserPayload(id=tag.user.id, full_name=tag.user.full_name) if tag.user else None
        )
        return TagData(
            id=tag.id,
            tag_name=tag.tag_name,
            tagged_by=user_info,
            created_at=tag.created_at,
        )

    async def add_tag(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        candidate_id: uuid.UUID,
        tag_name: str,
    ) -> TagResponse:
        """Add a normalized tag to candidate per API Contract §TAG-2 (raises 409 Conflict if duplicate)."""
        self._validate_role_permissions(user_role)

        candidate = await self.candidate_repo.get_candidate_by_id(
            session=session, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not candidate:
            raise ResourceNotFoundException(f"Candidate with ID '{candidate_id}' not found")

        normalized = self._normalize_tag_name(tag_name)

        existing = await self.tag_repo.get_candidate_tag_by_name(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            tag_name=normalized,
        )
        if existing:
            raise DuplicateTagError(f"Tag '{normalized}' already exists on this candidate")

        tag = await self.tag_repo.add_tag(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            tag_name=normalized,
            tagged_by=user_id,
        )

        refetched = await self.tag_repo.get_tag_by_id(
            session=session, tenant_id=tenant_id, tag_id=tag.id
        )
        target_tag = refetched or tag

        logger.info(
            "Added tag to candidate",
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
            tag_name=normalized,
        )
        return TagResponse(data=self._build_tag_data(target_tag))

    async def list_candidate_tags(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> TagListResponse:
        """List all tags on a candidate per API Contract §TAG-1."""
        candidate = await self.candidate_repo.get_candidate_by_id(
            session=session, candidate_id=candidate_id, tenant_id=tenant_id
        )
        if not candidate:
            raise ResourceNotFoundException(f"Candidate with ID '{candidate_id}' not found")

        tags = await self.tag_repo.list_candidate_tags(
            session=session, tenant_id=tenant_id, candidate_id=candidate_id
        )
        return TagListResponse(data=[self._build_tag_data(t) for t in tags])

    async def remove_tag(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        candidate_id: uuid.UUID,
        tag_id: uuid.UUID,
    ) -> None:
        """Remove a tag from candidate per API Contract §TAG-3."""
        self._validate_role_permissions(user_role)

        tag = await self.tag_repo.get_tag_by_id(session=session, tenant_id=tenant_id, tag_id=tag_id)
        if not tag or tag.candidate_id != candidate_id:
            raise ResourceNotFoundException(f"Tag with ID '{tag_id}' not found for this candidate")

        await self.tag_repo.remove_tag(session=session, tag=tag)
        logger.info(
            "Removed tag from candidate",
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
            tag_id=str(tag_id),
        )
