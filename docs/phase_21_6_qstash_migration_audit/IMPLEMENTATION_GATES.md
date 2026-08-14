# Phase 21.6 QStash Implementation Gates

To ensure stability and safety, the QStash migration will be executed sequentially through the following implementation gates.

## GATE 1 — QStash Client
- Client can publish a signed message.
- Configuration validation works.
- No production behavior changed.

## GATE 2 — Webhook Authentication
- Valid QStash signature accepted.
- Invalid signature rejected.
- Missing signature rejected.

## GATE 3 — Resume Parsing Webhook
- Valid message executes parsing.
- Duplicate delivery does not invoke Gemini twice.
- Retryable Gemini failure returns retryable HTTP status.
- Permanent failure is persisted correctly.

## GATE 4 — Candidate Embedding Webhook
- Existing embedding cache prevents duplicate generation.
- Gemini errors map correctly.
- AIUsageLog remains correct.

## GATE 5 — Job Embedding Webhook
- Same guarantees as candidate embedding.

## GATE 6 — Candidate Scoring Webhook
- One candidate is one independently retryable task.
- Score cache prevents duplicate scoring.
- `force_rescore` semantics remain correct.

## GATE 7 — Batch Coordinator
- Batch creates durable `BatchScoreJob` state.
- N candidate messages are published.
- Completion count is durable.
- Failed candidates are tracked.
- Duplicate coordinator delivery does not create duplicate work.

## GATE 8 — Celery/QStash Parallel Operation
- Celery remains functional.
- QStash can be enabled/disabled via configuration.
- Rollback to Celery is immediate.

## GATE 9 — Full Lifecycle
Test: Upload Resume → Parse → Candidate Enrichment → Candidate Embedding → Job Embedding → Batch Scoring using QStash.
Verify database state and AIUsageLog.

## GATE 10 — Decommission Approval
Celery/Redis may NOT be removed until all previous gates pass and explicit approval is granted.
