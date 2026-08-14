# Phase 21.6.2 — QStash Webhook Signature Verification

## 1. Objective
Implement and prove QStash webhook signature verification as an isolated infrastructure/security boundary component. This boundary ensures that future webhook implementations are securely authenticated before any task execution begins, while leaving existing Celery tasks completely untouched.

## 2. Installed QStash SDK/Version
- **Package:** `qstash` (PyPI)
- **Version:** `3.4.0`

## 3. Verification API Used
The verification component leverages the `qstash.Receiver` API provided by the official SDK. Specifically:
```python
receiver = Receiver(
    current_signing_key=self.current_key,
    next_signing_key=self.next_key,
)
receiver.verify(signature=signature, body=body_str, url=None)
```
*Note: The `url` parameter is explicitly omitted (`None`) because proxies (like ngrok), internal ALB hops, or HTTPS termination can alter the `request.url` observed by the application, causing false signature verification failures.*

## 4. Raw-Body Verification Requirement
The `Receiver.verify()` function mathematically requires the **exact raw request body string/bytes** that QStash originally signed. The verifier reads `await request.body()` and decodes it without JSON-parsing it. Reserializing a parsed JSON body introduces whitespace differences and key reordering, which alters the SHA-256 hash and invalidates the signature. 

## 5. Current/Next Key Rotation
The QStash SDK intrinsically handles key rotation seamlessly. 
1. It first attempts to decode the Upstash-Signature JWT using `QSTASH_CURRENT_SIGNING_KEY`.
2. If this fails due to a `SignatureError`, it gracefully falls back and attempts verification using `QSTASH_NEXT_SIGNING_KEY`.
3. If both fail, a `SignatureError` propagates up.

## 6. Authentication Failure Semantics
Expected HTTP semantics implemented for webhooks:
- **Valid Signature**: Request proceeds (HTTP 200/202 from downstream logic).
- **Missing Signature**: HTTP 401 Unauthorized.
- **Invalid/Malformed Signature**: HTTP 401 Unauthorized.
- **Missing Configuration**: HTTP 401 Unauthorized.

*Note: We strictly return 401 (Unauthorized) rather than 200, but we also do NOT want QStash to retry authentication failures forever. While a 401 natively triggers retries in QStash, authentication failures are typically persistent. Future webhook route implementations may need to explicitly `try/except` and swallow 401s if they prefer to prevent retry storms, but the verifier dependency cleanly raises 401.*

## 7. Test Matrix
Focused unit tests were written to cover the following scenarios deterministically without real QStash network calls:
1. Valid request signed with current key
2. Valid request signed with next key
3. Invalid signature (wrong key)
4. Missing signature
5. Modified request body (hash mismatch)
6. Malformed signature (non-JWT)
7. Missing signing keys configuration
8. Expired signature rejected
9. Secrets are not exposed in exception messages/logging

## 8. Exact Test Results
Tests ran securely and deterministically using `PyJWT` to simulate the signature generation.
```text
tests/test_qstash_client.py ........                                     [100%]
tests/test_qstash_auth.py .........                                      [100%]
======================== 17 passed, 17 warnings in 0.14s =======================
```
*(Warnings are purely PyJWT `InsecureKeyLengthWarning` regarding short mock test keys, which is expected).*
The full suite (`pytest tests/ -q`) also continues to exit structurally identically (environmental Postgres timeout).

## 9. Security Considerations
- Pydantic models flag all three secret keys with `repr=False`.
- The `QStashSignatureVerifier` intentionally catches `SignatureError` and raises a generic `HTTP 401 Unauthorized` without exposing the signature, body hashes, or the underlying exception strings in HTTP responses.
- Keys are verified without leaking into logs.

## 10. Rollback
No rollback is required. The verification component is an isolated dependency (`apps/api/hiron/webhooks/qstash_auth.py`). It is not yet connected to any FastAPI routes, and existing Celery tasks remain the default execution model. 

## 11. Known Limitations
Because we omit the `url` parameter in `receiver.verify()`, we do not validate the subject claim (`sub`) of the signature. This is a common and necessary tradeoff when running behind ngrok tunnels or load balancers that mutate the requested Host or Scheme.

## 12. Final Verdict
The signature verification component is secure, deterministic, and isolated. 

**PHASE 21.6.2 — GREEN**
