"""Search service generating query embeddings, normalizing vector scores, and extracting highlights per API Contract §CAND-7 & §SEARCH-1..4."""

import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.ai_usage.repository import AIUsageRepository
from hiron.audit.service import AuditService
from hiron.audit.utils import extract_model_changes, sanitize_audit_payload
from hiron.candidates.models import Candidate
from hiron.candidates.repository import CandidateRepository
from hiron.common.exceptions import ResourceNotFoundException
from hiron.embeddings.generator import DEFAULT_EMBEDDING_MODEL, EmbeddingGenerator
from hiron.embeddings.repository import EmbeddingRepository
from hiron.jobs.repository import JobRepository
from hiron.search.exceptions import InsufficientSearchPermissionsError, SearchQueryValidationError
from hiron.search.models import SavedSearch
from hiron.search.repository import SearchRepository
from hiron.search.schemas import (
    CandidateSearchResultItem,
    CandidateSearchResultPayload,
    SavedSearchData,
    SavedSearchListResponse,
    SavedSearchResponse,
    SearchCandidateFilters,
    SearchPaginationData,
    SemanticSearchCandidatesResponse,
)

logger = structlog.get_logger("hiron.search.service")


class SearchService:
    """Business service orchestrating candidate semantic search, job matching, and saved searches."""

    def __init__(
        self,
        search_repository: SearchRepository | None = None,
        candidate_repository: CandidateRepository | None = None,
        job_repository: JobRepository | None = None,
        embedding_repository: EmbeddingRepository | None = None,
        embedding_generator: EmbeddingGenerator | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.search_repo = search_repository or SearchRepository()
        self.candidate_repo = candidate_repository or CandidateRepository()
        self.job_repo = job_repository or JobRepository()
        self.embedding_repo = embedding_repository or EmbeddingRepository()
        self.generator = embedding_generator or EmbeddingGenerator()
        self.ai_usage_repo = AIUsageRepository()
        self.audit_service = audit_service or AuditService()

    def _validate_role_permissions(self, role: str) -> None:
        """Validate user role authorization for search operations."""
        if role not in ("org_admin", "recruiter"):
            raise InsufficientSearchPermissionsError(
                f"User with role '{role}' is not authorized for search operations"
            )

    def _extract_highlights(self, candidate: Candidate, query: str) -> list[str]:
        """Extract matched attribute highlights for candidate search result card."""
        highlights: list[str] = []
        if candidate.total_experience_years:
            highlights.append(f"{candidate.total_experience_years} years experience")
        if candidate.current_title:
            highlights.append(f"{candidate.current_title}")

        cand_skills = candidate.skills or []
        query_words = {w.lower() for w in query.split()}
        matched_skills = [s for s in cand_skills if s.lower() in query_words]

        if matched_skills:
            highlights.append(f"{', '.join(matched_skills[:3])} expertise")
        elif cand_skills:
            highlights.append(f"Skills: {', '.join(cand_skills[:3])}")

        return highlights

    def _build_saved_search_data(self, search: SavedSearch) -> SavedSearchData:
        """Convert SavedSearch ORM model to Pydantic SavedSearchData schema."""
        return SavedSearchData(
            id=search.id,
            tenant_id=search.tenant_id,
            created_by=search.created_by,
            name=search.name,
            query_text=search.query_text,
            filters=search.filters or {},
            is_shared=search.is_shared,
            created_at=search.created_at,
            updated_at=search.updated_at,
        )

    async def search_candidates(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        query: str,
        filters: SearchCandidateFilters | None = None,
        limit: int = 20,
    ) -> SemanticSearchCandidatesResponse:
        """Execute semantic search across candidate pool using vector similarity and metadata filters."""
        self._validate_role_permissions(user_role)

        if not query or len(query.strip()) < 3 or len(query) > 500:
            raise SearchQueryValidationError("Search query must be between 3 and 500 characters")

        # Generate query vector
        embed_result = await self.generator.generate_embedding(query)
        query_vec = embed_result.embedding

        # Log AI usage for generating search embedding
        cost_usd = 0.00000002 * embed_result.total_tokens
        await self.ai_usage_repo.create_usage_log(
            session=session,
            tenant_id=tenant_id,
            operation="semantic_search",
            model_version=self.generator.model_version,
            input_tokens=embed_result.input_tokens,
            output_tokens=0,
            cost_usd=cost_usd,
            latency_ms=embed_result.latency_ms,
            status=embed_result.status,
            error_type=embed_result.error_type,
            is_cache_hit=embed_result.is_fallback,
        )

        scored_candidates = await self.search_repo.search_candidates_by_vector_and_filters(
            session=session,
            tenant_id=tenant_id,
            query_vector=query_vec,
            filters=filters,
            limit=limit,
        )

        result_items: list[CandidateSearchResultItem] = []
        for cand, sim_score in scored_candidates:
            highlights = self._extract_highlights(cand, query)
            payload = CandidateSearchResultPayload(
                id=cand.id,
                full_name=cand.full_name,
                current_title=cand.current_title,
                skills=cand.skills or [],
                total_experience_years=cand.total_experience_years,
            )
            result_items.append(
                CandidateSearchResultItem(
                    candidate=payload,
                    relevance_score=sim_score,
                    highlights=highlights,
                )
            )

        logger.info(
            "Executed candidate semantic search",
            tenant_id=str(tenant_id),
            query=query,
            total_matched=len(result_items),
        )

        return SemanticSearchCandidatesResponse(
            data=result_items,
            pagination=SearchPaginationData(
                has_more=False,
                total_count=len(result_items),
            ),
        )

    async def search_candidates_by_job(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        job_id: uuid.UUID,
        limit: int = 20,
    ) -> SemanticSearchCandidatesResponse:
        """Search matching candidates for a job description via vector similarity."""
        self._validate_role_permissions(user_role)

        job = await self.job_repo.get_job_by_id(session=session, job_id=job_id, tenant_id=tenant_id)
        if not job:
            raise ResourceNotFoundException(f"Job with ID '{job_id}' not found")

        job_emb = await self.embedding_repo.get_job_embedding(
            session=session,
            tenant_id=tenant_id,
            job_id=job_id,
            model_version=DEFAULT_EMBEDDING_MODEL,
        )

        job_vec = job_emb.embedding if job_emb else None
        if not job_vec:
            job_text = f"{job.title} {job.department or ''} {job.description or ''}"
            embed_result = await self.generator.generate_embedding(job_text)
            job_vec = embed_result.embedding

            # Log AI usage
            cost_usd = 0.00000002 * embed_result.total_tokens
            await self.ai_usage_repo.create_usage_log(
                session=session,
                tenant_id=tenant_id,
                operation="semantic_search_by_job",
                model_version=self.generator.model_version,
                input_tokens=embed_result.input_tokens,
                output_tokens=0,
                cost_usd=cost_usd,
                latency_ms=embed_result.latency_ms,
                status=embed_result.status,
                error_type=embed_result.error_type,
                is_cache_hit=embed_result.is_fallback,
            )

        scored_candidates = await self.search_repo.search_candidates_by_vector_and_filters(
            session=session,
            tenant_id=tenant_id,
            query_vector=job_vec,
            limit=limit,
        )

        result_items: list[CandidateSearchResultItem] = []
        for cand, sim_score in scored_candidates:
            highlights = self._extract_highlights(cand, job.title)
            payload = CandidateSearchResultPayload(
                id=cand.id,
                full_name=cand.full_name,
                current_title=cand.current_title,
                skills=cand.skills or [],
                total_experience_years=cand.total_experience_years,
            )
            result_items.append(
                CandidateSearchResultItem(
                    candidate=payload,
                    relevance_score=sim_score,
                    highlights=highlights,
                )
            )

        return SemanticSearchCandidatesResponse(
            data=result_items,
            pagination=SearchPaginationData(
                has_more=False,
                total_count=len(result_items),
            ),
        )

    async def create_saved_search(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        name: str,
        query_text: str,
        filters: dict[str, Any] | None = None,
        is_shared: bool = False,
    ) -> SavedSearchResponse:
        """Create a new SavedSearch entry per §SEARCH-2."""
        self._validate_role_permissions(user_role)

        search = await self.search_repo.create_saved_search(
            session=session,
            tenant_id=tenant_id,
            created_by=user_id,
            name=name,
            query_text=query_text,
            filters=filters,
            is_shared=is_shared,
        )
        
        changes = extract_model_changes(search, "create")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="saved_search_created",
                entity_type="saved_search",
                entity_id=search.id,
                actor_id=user_id,
                changes=changes,
            )
            
        await session.commit()
        return SavedSearchResponse(data=self._build_saved_search_data(search))

    async def list_saved_searches(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
    ) -> SavedSearchListResponse:
        """List saved searches visible to the user per §SEARCH-1."""
        self._validate_role_permissions(user_role)

        searches = await self.search_repo.list_saved_searches(
            session=session, tenant_id=tenant_id, user_id=user_id
        )
        return SavedSearchListResponse(data=[self._build_saved_search_data(s) for s in searches])

    async def update_saved_search(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        search_id: uuid.UUID,
        name: str | None = None,
        query_text: str | None = None,
        filters: dict[str, Any] | None = None,
        is_shared: bool | None = None,
    ) -> SavedSearchResponse:
        """Update existing saved search per §SEARCH-3."""
        self._validate_role_permissions(user_role)

        search = await self.search_repo.get_saved_search_by_id(
            session=session, tenant_id=tenant_id, search_id=search_id
        )
        if not search:
            raise ResourceNotFoundException(f"Saved search with ID '{search_id}' not found")

        if search.created_by != user_id and user_role != "org_admin":
            raise InsufficientSearchPermissionsError(
                "Only search owner or org_admin can update saved search"
            )

        updated = await self.search_repo.update_saved_search(
            session=session,
            search=search,
            name=name,
            query_text=query_text,
            filters=filters,
            is_shared=is_shared,
        )
        
        changes = extract_model_changes(updated, "update")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="saved_search_updated",
                entity_type="saved_search",
                entity_id=updated.id,
                actor_id=user_id,
                changes=changes,
            )
            
        await session.commit()
        return SavedSearchResponse(data=self._build_saved_search_data(updated))

    async def delete_saved_search(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        search_id: uuid.UUID,
    ) -> None:
        """Delete saved search entry per §SEARCH-4."""
        self._validate_role_permissions(user_role)

        search = await self.search_repo.get_saved_search_by_id(
            session=session, tenant_id=tenant_id, search_id=search_id
        )
        if not search:
            raise ResourceNotFoundException(f"Saved search with ID '{search_id}' not found")

        if search.created_by != user_id and user_role != "org_admin":
            raise InsufficientSearchPermissionsError(
                "Only search owner or org_admin can delete saved search"
            )

        changes = extract_model_changes(search, "delete")
        if changes:
            changes = sanitize_audit_payload(changes)
            await self.audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="saved_search_deleted",
                entity_type="saved_search",
                entity_id=search.id,
                actor_id=user_id,
                changes=changes,
            )

        await self.search_repo.delete_saved_search(session=session, search=search)
        await session.commit()
