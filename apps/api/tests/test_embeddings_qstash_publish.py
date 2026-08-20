import uuid
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from hiron.core.config import get_settings
from hiron.embeddings.service import EmbeddingService


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    monkeypatch.setenv("QSTASH_TOKEN", "test-token")
    monkeypatch.setenv("QSTASH_CURRENT_SIGNING_KEY", "test-key-1")
    monkeypatch.setenv("QSTASH_NEXT_SIGNING_KEY", "test-key-2")
    monkeypatch.setenv("QSTASH_WEBHOOK_URL", "http://test-qstash-url")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_generate_candidate_embedding_uses_qstash():
    get_settings.cache_clear()

    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    service = EmbeddingService(candidate_repository=MagicMock())
    service.candidate_repo.get_candidate_by_id = AsyncMock()

    with patch(
        "hiron.core.qstash_client.qstash_publisher.publish", new_callable=AsyncMock
    ) as mock_publish:
        mock_publish.return_value = "msg-123"

        response = await service.generate_candidate_embedding(
            session=AsyncMock(),
            tenant_id=tenant_id,
            user_role="org_admin",
            candidate_id=candidate_id,
            model_version="models/gemini-embedding-001",
        )

        mock_publish.assert_called_once_with(
            url="http://test-qstash-url/api/v1/webhooks/qstash/embeddings/candidate",
            payload={
                "tenant_id": str(tenant_id),
                "candidate_id": str(candidate_id),
                "model_version": "models/gemini-embedding-001",
            },
            deduplication_id=ANY,
        )
        assert response.data.task_id == "msg-123"
