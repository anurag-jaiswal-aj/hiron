# Phase 8 Step 1 — Gemini Scoring Contract

## 1. POC Evidence
The repository contains documentation (`docs/phase_21_4_gemini_scoring/IMPLEMENTATION.md`) and a POC script (`docs/phase_21_4_gemini_scoring_poc/test_scoring.py`). 
However, **the actual POC engine implementation was never committed to the repository.** 
- `apps/api/hiron/scores/engine.py` remains a purely heuristic/algorithmic mock. It does not import `httpx` and does not check the `AI_PROVIDER` environment variable.
- `apps/api/hiron/scores/schemas.py` does not contain the `AIGeneratedScore` schema referenced in the documentation.
- `test_scoring.py` imports `AIGeneratedScore` (which fails) and runs the heuristic engine as if it were the Gemini API.

Therefore, much of the strict technical contract must be reconstructed or is entirely missing from the codebase.

## 2. Production Contract
1. **Exact Gemini model identifier**: `models/gemini-2.5-flash` (Established by `IMPLEMENTATION.md`).
2. **Exact API endpoint**: NOT ESTABLISHED BY CURRENT CODEBASE (The documentation mentions `generateContent`, but the exact URL format like `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` is missing from the scoring POC).
3. **HTTP method**: `POST` (Established by `IMPLEMENTATION.md` via `httpx.post`).
4. **Authentication mechanism**: NOT ESTABLISHED BY CURRENT CODEBASE for the `generateContent` call specifically (though the POC's model discovery uses `?key={api_key}`).

## 3. Request Contract
5. **Exact request JSON structure**: NOT ESTABLISHED BY CURRENT CODEBASE (The code constructing the Gemini JSON payload with `contents`, `systemInstruction`, and `generationConfig` is missing).
6. **Exact system/user prompt structure**: Established by `engine.py`. The `PromptBuilder` uses the system instruction: `"You are evaluating {candidate.full_name} for the role of {job.title}."`
7. **How candidate/job information is supplied**: Passed as string kwargs to `PromptBuilder.build_messages()` (candidate_skills, candidate_summary, candidate_resume_text, job_description, job_required_skills).
8. **How candidate/job embedding similarity is incorporated**: NOT ESTABLISHED BY CURRENT CODEBASE. The heuristic engine calculates `(cos_sim - 0.5) * 10` and adds it to the mock score. It is unknown if the POC passed the similarity to Gemini, or if it let Gemini generate a base score and then applied the vector boost programmatically afterward.

## 4. Prompt Contract
(See Request Contract #6 and #7). The structural security boundary is maintained by `PromptBuilder`.

## 5. Response Contract
9. **Exact structured JSON response expected**: Must be `application/json` constrained by a Pydantic schema (`AIGeneratedScore` that relies on `ScoreBreakdown`).
10. **Every field in the response and its type/range**: NOT ESTABLISHED BY CURRENT CODEBASE. The exact JSON keys Gemini was instructed to return are missing because `AIGeneratedScore` was never committed.

## 6. Pydantic Validation Contract
11. **Exact Pydantic model required**: `AIGeneratedScore` (NOT ESTABLISHED BY CURRENT CODEBASE, class is missing).
12. **Gemini response parsing rules**: `AIGeneratedScore.model_validate_json(...)` (Established by `IMPLEMENTATION.md`). If it hallucinates keys or misses data, Pydantic throws a `ValidationError`.

## 7. Token / Telemetry Contract
13. **Token usage metadata available**: `promptTokenCount` and `candidatesTokenCount` (Established by `IMPLEMENTATION.md`).
14. **How input/output tokens map to ai_usage_logs**: `promptTokenCount` maps to `input_tokens`; `candidatesTokenCount` maps to `output_tokens`.
15. **Latency measurement requirements**: Measured functionally via wall-clock time (`time.time()`) and recorded as `latency_ms`.

## 8. Timeout / Retry Contract
16. **Timeout requirement**: `timeout=7.5` seconds explicitly on the HTTP request to prevent Vercel timeouts.
17. **HTTP 429 behavior**: Raised cleanly as `httpx.HTTPStatusError` to force QStash to retry.
18. **HTTP 5xx behavior**: Raised cleanly to force QStash to retry.
19. **HTTP 4xx behavior**: 400, 401, 403, 404 are terminal errors. Fails instantly. No retry.
20. **Malformed JSON behavior**: Raised as Pydantic `ValidationError` (Terminal).
21. **Gemini safety/content-block behavior**: NOT ESTABLISHED BY CURRENT CODEBASE.
22. **Retry semantics**: Gemini does NOT silently fall back to the heuristic implementation. Errors bubble up.

## 9. Transaction Contract
24. **Transaction boundary for score + telemetry**: Currently, `ScoreService.score_candidate_sync()` flushes the score to the DB. The worker webhook (`apps/api/hiron/webhooks/router.py`) calls `await session.commit()`. Telemetry (`record_ai_usage`) MUST be added to `score_candidate_sync` so it shares this single transaction boundary.

## 10. Idempotency Contract
23. **Idempotency requirements**: A 24-hour cache (`SCORE_CACHE_TTL_SECONDS`) exists. If a score was generated < 24h ago, it is returned immediately without hitting Gemini.

## 11. Security / Tenant Isolation
- Tenant isolation is fully enforced via `tenant_id` foreign keys and RLS. 
- Prompt injection protection relies on `PromptBuilder`.

## 12. Existing Code Compatibility
25. **Existing ScoreService assumptions**: 
    - `service.py` currently assumes `engine.evaluate()` is a **synchronous** function.
    - If `httpx.post` is used synchronously (as documented in `IMPLEMENTATION.md`), it will block the FastAPI async event loop. We must either use `httpx.AsyncClient` and change `evaluate()` to `async def`, or run it in a threadpool.
26. **Existing tests that will change**: 
    - `test_scoring_engine.py` tests the math of the heuristic mock.
    - `test_score_service.py` tests the orchestration. Both will require HTTP client mocking (`respx` or `unittest.mock`) once the real API is integrated.

## 13. Required Implementation Changes
- Define the missing `AIGeneratedScore` schema in `schemas.py`.
- Refactor `AIScoringEngine.evaluate()` to construct the actual Gemini REST payload and execute the HTTP call.
- Modify `ScoreService.score_candidate_sync()` to `await` the engine (if made async) and to explicitly call `AIUsageService.record_ai_usage()`.

## 14. Required Test Changes
- Mock Gemini HTTP responses for all engine and service tests.
- Remove strict math assertions that relied on the heuristic algorithm.

## 15. Open Questions / Blockers
- How should the 768-dimensional vector cosine similarity be applied? Should it be sent to Gemini as a prompt input, or should we continue calculating it heuristically and manually adding `(cos_sim - 0.5) * 10` to the LLM's returned fit score? (The codebase does not establish this).
- What exact fields belong in `AIGeneratedScore`? (We must derive them from `ScoreData` / `ScoreBreakdown`).

## 16. Smallest Safe Implementation Slice
1. Add `AIGeneratedScore` to `schemas.py`.
2. Update `engine.py` to make the REST call to `models/gemini-2.5-flash` using `httpx.AsyncClient`.
3. Add telemetry logging to `score_candidate_sync`.
4. Mock the HTTP responses in `test_scoring_engine.py`.

## 17. Acceptance Criteria
- Engine successfully connects to Gemini and parses the response.
- `timeout=7.5` is enforced.
- 429/5xx errors correctly bubble up.
- `ai_usage_logs` records are generated for every scoring attempt.
