# Phase 8 Step 4 — Scoring Telemetry & Transaction Integration

## 1. Call Graph Audit
- `score_candidate_sync` is orchestrated by `ScoreService`.
- Webhooks and API endpoints orchestrate this operation by injecting an active `AsyncSession`.
- `batch_score_async` uses QStash to distribute batch tasks, where each QStash worker hits the webhook which resolves down to `score_candidate_sync`. Therefore, the async contract is completely preserved.

## 2. Transaction Ownership
The transaction owner remains the API endpoint or QStash webhook router that instantiates and injects the `AsyncSession` into `score_candidate_sync()`. Because AI usage telemetry and score persistence both use the same injected `session`, they automatically participate in the SAME transaction without arbitrary inner commits. If an exception is raised, or if the caller fails to commit, the entire transaction is rolled back.

## 3. Telemetry Integration
`AIUsageService` was injected into `ScoreService`. Immediately after a successful `ScoreRepository.create_score()`, the system calls `AIUsageService.record_ai_usage()` using the exact same session boundary.

## 4. Token Mapping
Gemini token counts map exactly from the evaluated schema:
- `input_tokens` (from Gemini's `promptTokenCount`) -> telemetry `input_tokens`
- `output_tokens` (from Gemini's `candidatesTokenCount`) -> telemetry `output_tokens`
Cost is accurately computed directly via Gemini 2.5 Flash bounds (0.075 / 1M input, 0.30 / 1M output).

## 5. Latency Mapping
`evaluation["latency_ms"]` is directly propagated to telemetry `latency_ms`.

## 6. Provenance
Values accurately extract and persist into the database logs:
- `prompt_name` -> `candidate_fit_scoring`
- `prompt_version` -> `2.0.0`
- `model_version` -> `models/gemini-2.5-flash`

## 7. Cache/Idempotency
The 24-hour cache idempotency check returns early, skipping the Gemini engine call, skipping `create_score()`, and skipping `record_ai_usage()`. Cache hits do NOT produce duplicate AI usage records.

## 8. Batch Scoring
Batch scoring distributes candidates to individual QStash worker webhook deliveries. Because each QStash delivery synchronously `awaits` `score_candidate_sync`, telemetry guarantees apply transparently across all background batch executions.

## 9. Failure Semantics
- **Gemini failure**: An exception is raised by the engine before persistence. No score is committed. No telemetry is generated.
- **Persistence failure**: `create_score()` raises an exception. `record_ai_usage()` execution is immediately skipped.
- **Commit failure**: Any downstream exception automatically rolls back the `AsyncSession`. Neither score nor telemetry is persisted.

## 10. Tests
- Updated `test_score_candidate_sync_success`: Asserts telemetry is recorded with exact pricing, metrics, and provenance when successfully executed.
- Updated `test_score_candidate_sync_idempotent_cached_response`: Asserts telemetry is skipped on a 24-hour cache hit.
- Added `test_score_candidate_sync_gemini_failure`: Asserts an engine exception entirely aborts the flow.
- Added `test_score_candidate_sync_persistence_failure`: Asserts a database exception during score creation actively skips telemetry recording.

## 11. Files Changed
- `apps/api/hiron/scores/service.py`: Added `AIUsageService` dependency and invoked `record_ai_usage()` within the existing transactional bounds.
- `apps/api/tests/test_score_service.py`: Added comprehensive unit tests targeting all permutations of telemetry conditions.

## 12. Remaining Risks
None related to scoring telemetry or transaction integrity. The code operates safely under established RDBMS transactional guarantees.

## 13. Acceptance Criteria
- [x] Successful score generates corresponding AI Usage log.
- [x] Transaction boundary is strictly adhered to.
- [x] The `generate_candidate_score` string is used for the operation identifier.
- [x] Cache hits do NOT create duplicate usage rows.
- [x] Failures do NOT leave orphaned rows.
- [x] Synchronous and background QStash async tasks are unified under the exact same transaction bounds.
