# Phase 8 Step 3 — Gemini Scoring Engine

## 1. Implementation
The heuristic mock scoring engine in `AIScoringEngine` has been completely replaced with a production-grade integration to the Gemini REST API (`models/gemini-2.5-flash`). The engine now operates asynchronously via `httpx.AsyncClient` and evaluates candidates against job descriptions using strict JSON output schemas. The vector boost logic has been entirely removed from the scoring implementation.

## 2. Request Contract
The application constructs the request payload mapping exactly to Gemini's native API:
- `systemInstruction`: Mapped from `PromptBuilder`'s system directive.
- `contents`: Mapped from `PromptBuilder`'s user message (containing truncated, XML-encapsulated data).
- `generationConfig.responseMimeType`: Set to `application/json` to strictly enforce structured output.
- Authentication is handled via the `GEMINI_API_KEY` environment variable in the query string (`?key={api_key}`).

## 3. Response Contract
Gemini is instructed in the system prompt to output a specific JSON structure corresponding precisely to `AIGeneratedScore`. The application extracts the `text` field from the first candidate part in the JSON response.

## 4. Validation
The raw JSON returned by Gemini is immediately validated against the `AIGeneratedScore` Pydantic model. If Gemini hallucinates keys, misses dimensions, or violates type bounds (e.g., `fit_score` > 100), Pydantic raises a `ValidationError` which is translated into a terminal HTTP 422 exception.

## 5. Error Handling
Error behaviors are strictly partitioned for QStash retry logic:
- **429 (Too Many Requests) / 5xx**: Propagated as `httpx.HTTPStatusError` so QStash and batch coordinators can retry the webhook.
- **Timeout**: Enforced strictly at 7.5 seconds and propagated as `httpx.TimeoutException` to trigger retries.
- **Malformed JSON / 400 / 401 / 403 / 404**: Captured and raised as terminal `HTTPException`s. The engine does NOT silently swallow errors and does NOT fallback to a heuristic math formula.

## 6. Token/Latency Capture
- `promptTokenCount` is mapped to `input_tokens`.
- `candidatesTokenCount` is mapped to `output_tokens`.
- Request duration is explicitly measured using `time.time()` wall-clock bounds and returned as `latency_ms`.

## 7. Vector Similarity Decision
As instructed, the heuristic formula (`vector_boost = (cos_sim - 0.5) * 10`) has been completely removed. Gemini alone governs the `fit_score` and `confidence` evaluations. The `candidate_vector` and `job_vector` parameters are still available in the method signature but are intentionally ignored by the evaluation pipeline, preserving them purely for downstream hybrid search workloads.

## 8. Security / PromptBuilder Preservation
The `PromptBuilder` and its underlying security constraints (input truncation, secondary prompt injection detection signals, and XML-style data encapsulation) remain 100% intact. The engine simply maps the output of `builder.build_messages()` into the Gemini REST payload.

## 9. Tests
`apps/api/tests/test_scoring_engine.py` was rewritten to mock asynchronous HTTP traffic (`httpx.AsyncClient`). It verifies:
- Complete parsing of valid AI scores.
- Strict 429 and 5xx propagation.
- Terminal JSON validation failures.
- 7.5s timeout constraint extraction.
`apps/api/tests/test_score_service.py` was updated to `await` the new async implementation.

## 10. Files Changed
- `apps/api/hiron/scores/schemas.py`: Added `AIGeneratedScore` and nested `ScoreBreakdownAI` schemas.
- `apps/api/hiron/scores/engine.py`: Replaced heuristic evaluation with real Gemini REST integration.
- `apps/api/hiron/scores/service.py`: Updated `score_candidate_sync` to `await` the engine evaluation.
- `apps/api/tests/test_scoring_engine.py`: Rewrote tests using `AsyncMock`/`MagicMock`.
- `apps/api/tests/test_score_service.py`: Updated mocked scoring engine to return a coroutine.

## 11. Remaining Work
- **Telemetry Transaction Integration**: `AIUsageService.record_ai_usage()` is still missing from the `ScoreService` transaction boundary (Phase 8 Step 4).
- **Production E2E Tests**: A full QStash integration test against the real Gemini API remains to be executed.

## 12. Acceptance Criteria
- Engine successfully connects to Gemini and parses the response.
- `timeout=7.5` is enforced.
- 429/5xx errors correctly bubble up.
- All modified code is fully covered by updated, focused unit tests.
