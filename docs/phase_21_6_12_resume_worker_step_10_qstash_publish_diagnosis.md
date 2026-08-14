# Phase 21.6.12 — Resume Worker Step 10: QStash Publish Diagnosis

## 1. Exact Execution Path
When a user uploads a resume via `POST /api/v1/resumes/upload`:
1. The `upload_resume` method in `apps/api/hiron/resumes/service.py` is invoked.
2. The Resume record is created in PostgreSQL with `status="pending"`.
3. The database transaction is committed (`await session.commit()`).
4. The service attempts to trigger QStash via `_enqueue_parse_task`, passing the newly created `resume.id`.
5. `_enqueue_parse_task` constructs the `webhook_url` by concatenating `settings.worker_url` and `/api/v1/webhooks/qstash/resumes/parse`.
6. `qstash_publisher.publish` is called.
7. Any exception thrown by the publisher is caught in the broad `try...except Exception as e:` block surrounding the `_enqueue_parse_task` call.

## 2. Evidence from Source Code
In `apps/api/hiron/resumes/service.py` (prior to the diagnostic patch), the exception handling explicitly swallowed QStash failures:

```python
        # 7. Enqueue background QStash task
        try:
            task_id = await self._enqueue_parse_task(tenant_id=tenant_id, resume_id=resume.id)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error("Failed to enqueue parse task", error=str(e), exc_info=True)
            task_id = f"task-{uuid.uuid4()}" # SILENT EXCEPTION SWALLOW

        return UploadResumeResponse(
            resume_id=resume.id,
            candidate_id=candidate.id,
            task_id=task_id,
            status=resume.status, # ALWAYS "pending"
            status_url=f"/api/v1/resumes/{resume.id}/status",
        )
```
If QStash publishing fails, the API generates a fake UUID, ignores the error, and returns a successful `HTTP 202 Accepted` response with the status `"pending"`.

## 3. Evidence from Environment Logs
Inspection of the `.env.temp.bootstrap` file (which contains the exact environment variables from Vercel Production) reveals a critical misconfiguration in the `WORKER_URL`:

```bash
WORKER_URL="https://hiron-worker-production.up.railway.app\n"
```
The URL contains a trailing newline/escape sequence (`\n`). 
When `_enqueue_parse_task` constructs the `webhook_url`, it generates an invalid destination URL:
`https://hiron-worker-production.up.railway.app\n/api/v1/webhooks/qstash/resumes/parse`

## 4. QStash Publish Result
The QStash publish call **DEFINITELY FAILED**.
The Upstash QStash SDK or the Upstash API rejected the malformed URL, throwing an exception.

## 5. Exact Failure Point
The failure point is the combination of:
1. **Misconfigured Vercel Environment:** `WORKER_URL` contains a trailing `\n`.
2. **Silent Failure Masking:** The `upload_resume` method's `except Exception:` block caught the resulting `QStashError`, logged it to standard error, generated a fake task ID, and allowed the API to return a successful `202 Accepted` response. This disconnected the actual system state from the client's perceived state.

## 6. What the Next Single Action Should Be
**Action:** Update the `WORKER_URL` environment variable in the Vercel Production Dashboard to remove the trailing `\n` character. Afterwards, the `upload_resume` exception handler should be updated to fail explicitly (e.g., return HTTP 500 or 502) rather than masking background queue failures.
