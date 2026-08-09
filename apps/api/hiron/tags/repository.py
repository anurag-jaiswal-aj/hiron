"""Tag repository managing SQL persistence and unique tag checking per Database Design §5.15."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hiron.tags.models import CandidateTag


class TagRepository:
    """Repository handling SQL persistence for candidate tags."""

    async def get_candidate_tag_by_name(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        tag_name: str,
    ) -> CandidateTag | None:
        """Fetch candidate tag by normalized tag name."""
        stmt = select(CandidateTag).where(
            CandidateTag.tenant_id == tenant_id,
            CandidateTag.candidate_id == candidate_id,
            CandidateTag.tag_name == tag_name,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_tag(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        tag_name: str,
        tagged_by: uuid.UUID,
    ) -> CandidateTag:
        """Insert and persist a new CandidateTag."""
        tag = CandidateTag(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            tag_name=tag_name,
            tagged_by=tagged_by,
        )
        session.add(tag)
        await session.flush()
        return tag

    async def list_candidate_tags(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> list[CandidateTag]:
        """Fetch all tags for a candidate ordered by created_at ASC."""
        stmt = (
            select(CandidateTag)
            .where(
                CandidateTag.tenant_id == tenant_id,
                CandidateTag.candidate_id == candidate_id,
            )
            .options(selectinload(CandidateTag.user))
            .order_by(CandidateTag.created_at.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def list_tenant_tags(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> list[str]:
        """Fetch all unique tag names for a tenant ordered alphabetically."""
        stmt = (
            select(CandidateTag.tag_name)
            .where(CandidateTag.tenant_id == tenant_id)
            .distinct()
            .order_by(CandidateTag.tag_name.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_tag_by_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        tag_id: uuid.UUID,
    ) -> CandidateTag | None:
        """Fetch tag by ID and tenant ID."""
        stmt = (
            select(CandidateTag)
            .where(
                CandidateTag.tenant_id == tenant_id,
                CandidateTag.id == tag_id,
            )
            .options(selectinload(CandidateTag.user))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def remove_tag(
        self,
        session: AsyncSession,
        tag: CandidateTag,
    ) -> None:
        """Hard delete tag from database."""
        await session.delete(tag)
        await session.flush()
