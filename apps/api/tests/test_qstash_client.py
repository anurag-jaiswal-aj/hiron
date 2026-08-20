from unittest.mock import AsyncMock, patch

import pytest

from hiron.core.config import get_settings
from hiron.core.qstash_client import QStashPublisher


def test_qstash_publisher_initialization(monkeypatch):
    monkeypatch.setenv("QSTASH_TOKEN", "fake_token")
    monkeypatch.setenv("QSTASH_CURRENT_SIGNING_KEY", "fake_key1")
    monkeypatch.setenv("QSTASH_NEXT_SIGNING_KEY", "fake_key2")
    get_settings.cache_clear()

    publisher = QStashPublisher()
    assert publisher.enabled is True
    assert publisher.client is not None

def test_qstash_publisher_disabled_when_no_token(monkeypatch):
    monkeypatch.setenv("QSTASH_TOKEN", "")
    get_settings.cache_clear()

    publisher = QStashPublisher()
    assert getattr(publisher, "enabled", False) is False

@pytest.mark.asyncio
async def test_qstash_publisher_publish(monkeypatch):
    monkeypatch.setenv("QSTASH_TOKEN", "fake_token")
    monkeypatch.setenv("QSTASH_CURRENT_SIGNING_KEY", "fake_key1")
    monkeypatch.setenv("QSTASH_NEXT_SIGNING_KEY", "fake_key2")
    get_settings.cache_clear()

    publisher = QStashPublisher()
    assert publisher.enabled is True
    assert publisher.client is not None

    with patch.object(publisher.client.message, "publish_json", new_callable=AsyncMock) as mock_publish_json:
        class MockResponse:
            message_id = "msg_123"
        mock_publish_json.return_value = MockResponse()

        result = await publisher.publish(
            url="http://test.com/webhook",
            payload={"data": "value"},
            deduplication_id="dedup_abc",
            retries=3,
            delay="10s"
        )

        assert result == "msg_123"
        mock_publish_json.assert_called_once_with(
            url="http://test.com/webhook",
            body={"data": "value"},
            deduplication_id="dedup_abc",
            retries=3,
            delay="10s",
        )
