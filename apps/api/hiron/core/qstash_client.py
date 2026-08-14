"""Minimal QStash client abstraction for publishing webhooks."""

import structlog
from qstash import AsyncQStash

from hiron.core.config import get_settings

logger = structlog.get_logger("hiron.core.qstash_client")


class QStashPublisher:
    """Wrapper around Upstash QStash client to publish messages."""

    def __init__(self) -> None:
        settings = get_settings()
        self.enabled = bool(settings.qstash_token)

        if self.enabled and settings.qstash_token:
            self.client = AsyncQStash(settings.qstash_token)
        else:
            self.client = None

    async def publish(
        self,
        url: str,
        payload: dict | str,
        deduplication_id: str | None = None,
        retries: int | None = None,
        delay: str | int | None = None,
    ) -> str | None:
        """Publish a message to QStash asynchronously.

        Args:
            url: The destination webhook URL.
            payload: JSON dictionary or string payload.
            deduplication_id: Optional deterministic ID for deduplication.
            retries: Optional maximum number of retries.
            delay: Optional delay before first delivery (e.g., '10s' or integer seconds).

        Returns:
            The QStash message ID if successfully published and enabled, else None.
        """
        if not self.enabled or not self.client:
            logger.warning("QStash publishing is disabled or client not initialized")
            return None

        try:
            if isinstance(payload, dict):
                res = await self.client.message.publish_json(
                    url=url,
                    body=payload,
                    deduplication_id=deduplication_id,
                    retries=retries,
                    delay=delay,
                )
            else:
                res = await self.client.message.publish(
                    url=url,
                    body=payload,
                    deduplication_id=deduplication_id,
                    retries=retries,
                    delay=delay,
                )

            logger.info("Published QStash message", url=url, message_id=res.message_id)
            return str(res.message_id)
        except Exception as e:
            logger.error("Failed to publish QStash message", error=str(e), url=url)
            raise


qstash_publisher = QStashPublisher()
