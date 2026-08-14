import base64
import hashlib
import time

import jwt
import pytest
from fastapi import HTTPException

from hiron.webhooks.qstash_auth import QStashSignatureVerifier

CURRENT_KEY = "sig_current_test_key_123"
NEXT_KEY = "sig_next_test_key_456"


def generate_qstash_signature(
    body: str,
    key: str,
    url: str = "http://test.com",
    expired: bool = False,
    issuer: str = "Upstash",
    modify_body_hash: bool = False,
) -> str:
    """Generate a deterministic test signature matching QStash SDK expectations."""
    now = int(time.time())

    # Generate body hash
    body_hash = hashlib.sha256(body.encode()).digest()
    body_hash_b64 = base64.urlsafe_b64encode(body_hash).decode().rstrip("=")

    if modify_body_hash:
        body_hash_b64 = "modified_" + body_hash_b64

    payload = {
        "iss": issuer,
        "sub": url,
        "exp": now - 3600 if expired else now + 3600,
        "nbf": now - 3600,
        "body": body_hash_b64,
    }

    return jwt.encode(payload, key, algorithm="HS256")


class MockRequest:
    def __init__(self, body: str, headers: dict[str, str], url: str = "http://test.com"):
        self._body = body.encode("utf-8")
        self.headers = headers
        self.url = url

    async def body(self) -> bytes:
        return self._body


@pytest.mark.asyncio
async def test_valid_request_signed_with_current_key():
    body = '{"event": "test"}'
    signature = generate_qstash_signature(body, CURRENT_KEY)
    request = MockRequest(body=body, headers={"Upstash-Signature": signature})

    verifier = QStashSignatureVerifier(current_key=CURRENT_KEY, next_key=NEXT_KEY)

    # Should not raise any exceptions
    await verifier.verify(request)


@pytest.mark.asyncio
async def test_valid_request_signed_with_next_key():
    body = '{"event": "test"}'
    signature = generate_qstash_signature(body, NEXT_KEY)
    request = MockRequest(body=body, headers={"Upstash-Signature": signature})

    verifier = QStashSignatureVerifier(current_key=CURRENT_KEY, next_key=NEXT_KEY)

    # Should not raise any exceptions (tests key rotation)
    await verifier.verify(request)


@pytest.mark.asyncio
async def test_invalid_signature_wrong_key():
    body = '{"event": "test"}'
    signature = generate_qstash_signature(body, "wrong_key")
    request = MockRequest(body=body, headers={"Upstash-Signature": signature})

    verifier = QStashSignatureVerifier(current_key=CURRENT_KEY, next_key=NEXT_KEY)

    with pytest.raises(HTTPException) as exc:
        await verifier.verify(request)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid signature"


@pytest.mark.asyncio
async def test_missing_signature():
    body = '{"event": "test"}'
    request = MockRequest(body=body, headers={})

    verifier = QStashSignatureVerifier(current_key=CURRENT_KEY, next_key=NEXT_KEY)

    with pytest.raises(HTTPException) as exc:
        await verifier.verify(request)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Missing signature"


@pytest.mark.asyncio
async def test_modified_request_body():
    body = '{"event": "test"}'
    # Sign with modified hash
    signature = generate_qstash_signature(body, CURRENT_KEY, modify_body_hash=True)
    request = MockRequest(body=body, headers={"Upstash-Signature": signature})

    verifier = QStashSignatureVerifier(current_key=CURRENT_KEY, next_key=NEXT_KEY)

    with pytest.raises(HTTPException) as exc:
        await verifier.verify(request)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid signature"


@pytest.mark.asyncio
async def test_malformed_signature():
    body = '{"event": "test"}'
    request = MockRequest(body=body, headers={"Upstash-Signature": "not.a.jwt"})

    verifier = QStashSignatureVerifier(current_key=CURRENT_KEY, next_key=NEXT_KEY)

    with pytest.raises(HTTPException) as exc:
        await verifier.verify(request)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid signature"


@pytest.mark.asyncio
async def test_missing_signing_keys():
    body = '{"event": "test"}'
    request = MockRequest(body=body, headers={"Upstash-Signature": "valid_but_no_keys_configured"})

    # Initialize without keys
    verifier = QStashSignatureVerifier(current_key="", next_key="")

    with pytest.raises(HTTPException) as exc:
        await verifier.verify(request)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Webhook authentication not configured"


@pytest.mark.asyncio
async def test_expired_signature_rejected():
    body = '{"event": "test"}'
    signature = generate_qstash_signature(body, CURRENT_KEY, expired=True)
    request = MockRequest(body=body, headers={"Upstash-Signature": signature})

    verifier = QStashSignatureVerifier(current_key=CURRENT_KEY, next_key=NEXT_KEY)

    with pytest.raises(HTTPException) as exc:
        await verifier.verify(request)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid signature"


@pytest.mark.asyncio
async def test_secrets_not_exposed_in_exceptions():
    body = '{"event": "test"}'
    signature = generate_qstash_signature(body, "wrong_key")
    request = MockRequest(body=body, headers={"Upstash-Signature": signature})

    verifier = QStashSignatureVerifier(current_key=CURRENT_KEY, next_key=NEXT_KEY)

    with pytest.raises(HTTPException) as exc:
        await verifier.verify(request)

    exception_repr = repr(exc.value)
    exception_str = str(exc.value)

    assert CURRENT_KEY not in exception_repr
    assert CURRENT_KEY not in exception_str
    assert NEXT_KEY not in exception_repr
    assert NEXT_KEY not in exception_str
