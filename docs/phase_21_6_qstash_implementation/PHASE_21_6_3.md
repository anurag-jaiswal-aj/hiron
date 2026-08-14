# Phase 21.6.3 — QStash Webhook Delivery POC

## 1. Objective
Prove that a QStash message can be delivered to a Hiron FastAPI webhook endpoint, authenticated using the Phase 21.6.2 signature verifier, and acknowledged correctly, without altering any Celery tasks or behavior.

## 2. FastAPI Webhook Location
A dedicated namespace router was created:
**Router**: `apps/api/hiron/webhooks/router.py`
**Prefix**: `/api/v1/webhooks`
**Endpoint**: `POST /qstash/test`

## 3. Endpoint Contract
**Payload (JSON)**:
```json
{
    "event": "phase_21_6_3_test",
    "message_id": "uuid-string",
    "payload": {
        "hello": "string"
    }
}
```
**Response (200 OK)**:
```json
{
    "status": "accepted",
    "event": "phase_21_6_3_test"
}
```

## 4. Raw-body Verification Flow
The endpoint is strictly constructed to verify the exact raw HTTP bytes prior to JSON parsing.
1. The FastAPI router specifies the authentication dependency: `dependencies=[Depends(verify_qstash_signature)]`.
2. The dependency intercepts the request, reads `await request.body()`, and mathematically validates the hash against the `Upstash-Signature` JWT header.
3. Only upon success does the endpoint execution proceed to parse the validated body using `TestWebhookRequest.model_validate_json(body_bytes)`.
4. If Pydantic fails to parse, a clean `422 Unprocessable Entity` is returned.

## 5. Authentication Mechanism
Authentication relies on the `QStashSignatureVerifier` component engineered in Phase 21.6.2. 
It requires the `Upstash-Signature` header and validates using deterministic keys without leaking secrets in logs, responses, or error details.

## 6. Local Test Matrix
Local integration testing (`test_qstash_webhook.py`) covers:
1. Valid request signed with current key → 200
2. Valid request signed with next key → 200
3. Missing signature → 401
4. Invalid signature → 401
5. Modified body → 401
6. Malformed signature → 401
7. Valid signature but malformed JSON → 422
8. Payload correctly reaches endpoint
9. Secrets never leak in the HTTP response
10. Celery `send_task` is strictly not invoked.

## 7. Exact Test Results
Focused tests:
```bash
tests/test_qstash_webhook.py ..........                                  [100%]
======================= 10 passed, 21 warnings in 0.24s ========================
```
*(Warnings are PyJWT `InsecureKeyLengthWarning` regarding short mock test keys).*
Full regression suite (`pytest tests/ -q`) remains structurally identical (the isolated 1 failure is environmental PostgreSQL timeouts due to the Docker daemon being offline).

## 8. Real QStash Delivery Procedure
A dedicated script was created at `docs/phase_21_6_qstash_implementation/test_qstash_delivery.py`.
It utilizes the official SDK to publish one isolated test message to a configured `WEBHOOK_URL`.

**REAL_QSTASH_DELIVERY = PASS**
The real QStash delivery test has been successfully completed.

**Results:**
- **Public delivery**: PASS (delivered via temporary cloudflared tunnel)
- **HTTP status**: 200 OK
- **Signature verification**: PASS
- **Payload validation**: PASS
- **Observed latency**: ~69ms (webhook execution time)
- **QStash message ID**: `msg_26hZCxZCuWyyTWPmSVBrNC1RACBnSVswNTGp5HweLA5x8Jf96xmbrudqSp8foNW`
- **Secrets leaked**: None
- **Tunnel method**: temporary cloudflared tunnel

## 9. Security Considerations
- Pydantic models flag all three secret keys with `repr=False`.
- Missing/invalid signatures yield generic `401 Unauthorized` responses without exposing cryptographic specifics.
- The webhook requires exactly the exact raw bytes to compute the body hash—ensuring no man-in-the-middle manipulation can succeed.
- Idempotency / Duplicate checks: Not implemented in the POC script, so none were executed, matching the Phase 21.6.3 constraints.

## 10. What is NOT implemented yet
- Database idempotency checks are missing.
- Celery tasks (fan-out, parse, score) are completely untouched.
- `BatchScoreJob` is NOT implemented.
- Production webhook routes are absent.

## 11. Rollback Procedure
The endpoint is an isolated testing namespace (`/api/v1/webhooks/qstash/test`) decoupled from production logic. To rollback, simply drop the include directive from `hiron/main.py` and delete the `apps/api/hiron/webhooks` directory. Existing Celery behavior is mathematically unaffected.

## 12. Final Verdict
The webhook delivery boundary is logically proven, securely authenticated, publicly reachable, and validated against the real Upstash QStash service.

**PHASE 21.6.3 — GREEN (REAL_QSTASH_DELIVERY = PASS)**
