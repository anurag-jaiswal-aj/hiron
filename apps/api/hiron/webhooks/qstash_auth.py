"""QStash webhook signature verification."""

import structlog
from fastapi import HTTPException, Request, status
from qstash import Receiver
from qstash.errors import SignatureError

from hiron.core.config import get_settings

logger = structlog.get_logger("hiron.webhooks.qstash_auth")


class QStashSignatureVerifier:
    """Isolated component responsible for verifying QStash webhook requests.

    Supports key rotation using current and next signing keys.
    """

    def __init__(self, current_key: str | None = None, next_key: str | None = None) -> None:
        settings = get_settings()
        self.current_key = (
            current_key if current_key is not None else settings.qstash_current_signing_key
        )
        self.next_key = next_key if next_key is not None else settings.qstash_next_signing_key

        # Only initialize receiver if keys are available
        if self.current_key and self.next_key:
            self.receiver = Receiver(
                current_signing_key=self.current_key,
                next_signing_key=self.next_key,
            )
        else:
            self.receiver = None

    async def verify(self, request: Request) -> None:
        """Verify the QStash signature of the incoming request.

        Reads the raw HTTP request body and validates the Upstash-Signature header against the
        configured signing keys. If valid, the request proceeds.
        If invalid, raises an HTTP 401 Unauthorized exception.

        We intentionally omit verifying the 'url' parameter because load balancers,
        proxies (like ngrok), or HTTPS-termination can alter the observed URL and
        cause false signature validation failures.
        """
        if not self.receiver:
            logger.error("Webhook authentication failed: signing keys not configured")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook authentication not configured",
            )

        signature = request.headers.get("Upstash-Signature")
        if not signature:
            logger.warning("Webhook authentication failed: missing Upstash-Signature header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing signature",
            )

        try:
            # We must use the exact raw bytes received to verify the signature.
            body_bytes = await request.body()
            body_str = body_bytes.decode("utf-8")

            # The URL parameter is optional in the qstash SDK receiver.
            self.receiver.verify(signature=signature, body=body_str, url=None)

        except SignatureError:
            # We do NOT log the signature or body contents to prevent secret exposure
            logger.warning("Webhook authentication failed: invalid signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )
        except Exception as e:
            logger.error("Webhook authentication failed: internal verification error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
            )


async def verify_qstash_signature(request: Request) -> None:
    """FastAPI dependency for verifying QStash webhooks."""
    verifier = QStashSignatureVerifier()
    await verifier.verify(request)
