# Phase 21.6 QStash Retry Error Matrix

To control QStash retry behavior, our webhook endpoints must map application errors and Gemini API errors to specific HTTP response codes.

| Scenario | Application Event / Error | Webhook HTTP Response | QStash Behavior | DB State Transition | Logging Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Success** | Task completes successfully | `200 OK` | Mark Delivered | Success state (e.g., status="parsed") | `INFO` success |
| **Idempotency** | Task claimed by other worker / Duplicate | `200 OK` | Mark Delivered (Ack) | None (skip execution) | `INFO` duplicate ignored |
| **Quota limit** | Gemini HTTP 429 (Too Many Requests) | `429 Too Many Requests` | Retry with backoff | None (retain "processing") | `WARNING` quota exceeded |
| **AI Internal Error** | Gemini HTTP 500 (Internal Server Error) | `500 Internal Server Error` | Retry with backoff | None (retain "processing") | `WARNING` AI provider error |
| **AI Bad Gateway** | Gemini HTTP 502 / 503 / 504 | `503 Service Unavailable` | Retry with backoff | None (retain "processing") | `WARNING` AI provider error |
| **Timeout** | Webhook execution exceeds 15-30s | (No response sent) | Retry with backoff | Potentially inconsistent if DB commit hasn't fired | `ERROR` task timed out |
| **Invalid Payload** | Missing tenant_id / Invalid JSON Schema | `200 OK` (Ack) *or* configure QStash to ignore 400s | Mark Delivered | Update entity status="failed" | `ERROR` invalid payload |
| **Invalid Entity** | Invalid UUID / Entity Not Found | `200 OK` (Ack) | Mark Delivered | None (entity doesn't exist) | `ERROR` resource not found |
| **AI Schema Error** | Gemini returns unparsable JSON / 400 Bad Request | `200 OK` (Ack) | Mark Delivered | Update entity status="failed" | `ERROR` fatal AI schema error |
| **DB Constraint** | PostgreSQL Unique Violation / Foreign Key | `200 OK` (Ack) | Mark Delivered | None (catch exception) | `ERROR` db constraint failed |
| **Unhandled Code Error**| Unexpected Python Exception | `500 Internal Server Error` | Retry with backoff | None (rollback transaction) | `ERROR` unhandled exception |

**Important Note:** 
For fatal, non-retryable errors (Invalid UUID, Bad JSON Schema from AI), we must return `200 OK` to QStash to acknowledge receipt and stop the retry loop, while explicitly persisting the `failed` state in our PostgreSQL database. If we return `400 Bad Request`, QStash will retry the message unless specifically configured to drop 4xx codes. Returning `200 OK` ensures the message is cleared from the queue.
