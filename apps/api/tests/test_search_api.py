"""API integration tests for candidate semantic search and saved search CRUD endpoints per API Contract §CAND-7 & §SEARCH-1..4."""

import datetime
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.main import create_app
from hiron.search.router import get_search_service
from hiron.search.schemas import (
    CandidateSearchResultItem,
    CandidateSearchResultPayload,
    SavedSearchData,
    SavedSearchListResponse,
    SavedSearchResponse,
    SearchPaginationData,
    SemanticSearchCandidatesResponse,
)
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_search_service() -> AsyncMock:
    """Fixture supplying mock SearchService."""
    return AsyncMock()


@pytest.fixture
def client(mock_search_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and SearchService dependencies."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="recruiter@example.com",
        role="recruiter",
        is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    app.dependency_overrides[get_search_service] = lambda: mock_search_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_search_candidates_endpoint_success(
    client: TestClient, mock_search_service: AsyncMock
) -> None:
    """Verify POST /api/v1/search/candidates returns 200 OK per API Contract §CAND-7."""
    candidate_id = uuid.uuid4()

    mock_search_service.search_candidates.return_value = SemanticSearchCandidatesResponse(
        data=[
            CandidateSearchResultItem(
                candidate=CandidateSearchResultPayload(
                    id=candidate_id,
                    full_name="Jane Smith",
                    current_title="Senior Engineer",
                    skills=["Python"],
                    total_experience_years=8,
                ),
                relevance_score=0.94,
                highlights=["8 years experience", "Python expertise"],
            )
        ],
        pagination=SearchPaginationData(has_more=False, total_count=1),
    )

    response = client.post(
        "/api/v1/search/candidates",
        json={
            "query": "Senior backend engineers with Python experience",
            "filters": {"experienceMin": 5},
            "limit": 10,
        },
    )

    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json["data"]) == 1
    assert res_json["data"][0]["candidate"]["fullName"] == "Jane Smith"
    assert res_json["data"][0]["relevanceScore"] == 0.94


def test_list_saved_searches_endpoint_success(
    client: TestClient, mock_search_service: AsyncMock
) -> None:
    """Verify GET /api/v1/saved-searches returns 200 OK per API Contract §SEARCH-1."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    search_id = uuid.uuid4()

    mock_search_service.list_saved_searches.return_value = SavedSearchListResponse(
        data=[
            SavedSearchData(
                id=search_id,
                tenant_id=tenant_id,
                created_by=user_id,
                name="Backend SF",
                query_text="Backend engineer",
                filters={"location": "SF"},
                is_shared=False,
                created_at=datetime.datetime.now(datetime.UTC),
                updated_at=datetime.datetime.now(datetime.UTC),
            )
        ]
    )

    response = client.get("/api/v1/saved-searches")

    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json["data"]) == 1
    assert res_json["data"][0]["name"] == "Backend SF"


def test_create_saved_search_endpoint_success(
    client: TestClient, mock_search_service: AsyncMock
) -> None:
    """Verify POST /api/v1/saved-searches returns 201 Created per API Contract §SEARCH-2."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    search_id = uuid.uuid4()

    mock_search_service.create_saved_search.return_value = SavedSearchResponse(
        data=SavedSearchData(
            id=search_id,
            tenant_id=tenant_id,
            created_by=user_id,
            name="Fintech Devs",
            query_text="Fintech engineers",
            filters={},
            is_shared=False,
            created_at=datetime.datetime.now(datetime.UTC),
            updated_at=datetime.datetime.now(datetime.UTC),
        )
    )

    response = client.post(
        "/api/v1/saved-searches",
        json={
            "name": "Fintech Devs",
            "queryText": "Fintech engineers",
            "filters": {},
            "isShared": False,
        },
    )

    assert response.status_code == 201
    res_json = response.json()
    assert res_json["data"]["name"] == "Fintech Devs"
