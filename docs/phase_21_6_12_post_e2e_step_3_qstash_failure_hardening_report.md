# Phase 21.6.12 — Post-E2E Step 3: QStash Failure Semantics Hardening Report

## 1. Existing Failure Behavior
Prior to this fix, if `_enqueue_parse_task` raised an exception (e.g. QStash network timeout, authentication error, or missing webhook URL), the `upload_resume` service method would gracefully catch the exception, generate a fake error string disguised as a `task_id` (e.g., `ERROR: ... | TRACE: ...`), and return HTTP 202 to the client. This masked the queuing failure entirely from the client and left the newly-created Resume stuck in a `pending` state permanently in the database.

## 2. Architectural Analysis
When evaluating how to address a QStash failure during upload, three transaction strategies were considered:
A. **Rollback:** Rolling back the database transaction. 
B. **Failed State:** Committing the transaction but marking the resume state as `failed`.
C. **Alternative Queues:** Using a fallback queue.

**Chosen Strategy (B - Failed State):**
Because `upload_resume` uploads the physical file to Supabase Storage *before* committing the database transaction and enqueueing the task, a strict database rollback would result in an orphaned S3 object. Furthermore, Hiron's existing system design includes a `retry_parse` endpoint explicitly designed to take a Resume in the `failed` state and push it back to the `pending` state while re-attempting background queuing. 

By catching the QStash exception, updating the Resume status to `failed` with the exact error message, committing the transaction, and raising an HTTP 503 error, we perfectly satisfy the existing architectural boundaries:
- The S3 object is properly tracked in the DB.
- The client is truthfully informed that the parsing queue is unavailable (503).
- The client can seamlessly use the "Retry" feature in the frontend later, which calls `retry_parse`.

## 3. Source Changes
**Files Modified:** `apps/api/hiron/resumes/service.py`
- Updated both `upload_resume` and `retry_parse`.
- Replaced the silent `Exception` catch with a block that updates the database status to `failed`.
- Raised a `HironException` (Code: `QUEUE_ERROR`, HTTP Status: 503 Service Unavailable).
- Fixed a silent bug in `retry_parse` where `_enqueue_parse_task` was missing the `await` keyword.

## 4. Tests Added & Updated
**Files Modified:** `apps/api/tests/test_resume_service.py`
- **Updated:** Fixed the mocking of `get_settings` in `test_retry_parse_success` to properly invoke the QStash publish pipeline during tests.
- **Added:** `test_upload_resume_qstash_publish_failure_raises_503`
  - *Test 1 (Implicit):* Standard upload tests verified QStash publish success scenarios still operate correctly.
  - *Test 2 (Fake ID removal):* Verified that QStash exceptions raise `HironException(503)` rather than returning a 202 response.
  - *Test 3 (DB State Verification):* Verified that `update_resume_status(status="failed")` is called and `session.commit()` is fired correctly *before* the exception is thrown.

## 5. Test Results
- Ran `uv run pytest apps/api/tests/test_resume_service.py`.
- **Result:** 11 passed.
- No whitespace errors detected via `git diff --check`.

## 6. Confirmations
- **No infrastructure modified:** Vercel, Railway, Supabase, and QStash infrastructure were completely untouched.
- **No secrets accessed:** No secrets or credentials were read, rotated, or printed to logs.
- **No unrelated code modified:** The API parser, UI schemas, and database schema were completely unedited. Only the exception handling block inside the resume domain service was hardened.

## 7. Remaining Risks
The system is significantly more resilient. However, if QStash is down *during* a bulk upload, the current bulk upload loop gracefully handles the `HironException` and adds the file to the `rejections` array. This is mathematically correct but could theoretically result in up to 500 files being marked as `failed` sequentially in a single batch. This is acceptable within the current limits but should be monitored if scale increases.
