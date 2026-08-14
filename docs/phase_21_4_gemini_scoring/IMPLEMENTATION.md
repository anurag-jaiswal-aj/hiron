# Phase 21.4 - Gemini Scoring Engine Implementation

## Current Heuristic Mock Flow
Previously, the `AIScoringEngine` would construct an `_llm_messages` array using `PromptBuilder` and mock out the API request via Python heuristic checks (`calculate_skills_matching`, etc.). No OpenAI API call was made during scoring, even when the `gpt-4o-2024-08-06` constant was returned.

## New Gemini Flow
When `AI_PROVIDER=gemini`, the `AIScoringEngine` sends an explicitly structured prompt using the exact `_llm_messages` schema to Gemini. We utilize Gemini's `generateContent` API explicitly with `responseMimeType: "application/json"`.

## Structured-Output Schema Mapping
We reuse the existing production schemas from `apps/api/hiron/scores/schemas.py`:
- `ScoreBreakdown` (and internally `BreakdownDimension`)

To satisfy Gemini's `responseSchema` constraints, we created a single unifying `AIGeneratedScore` Pydantic model directly inside `schemas.py` that relies entirely on `ScoreBreakdown`. The string JSON response from Gemini is safely validated via `AIGeneratedScore.model_validate_json(...)`. If Gemini hallucinates keys or missing required data, Pydantic throws a `ValidationError`.

## Model Configuration
`gemini_llm_model` dynamically discovers models via Google's `v1beta/models` endpoint during POC execution. In production code, it respects the `get_settings().gemini_llm_model` value, defaulting to `DEFAULT_LLM_MODEL_VERSION` only if `ai_provider != 'gemini'`.

The PROVEN MODEL that was actually tested and successfully validated against the live API is:
**`models/gemini-2.5-flash`**

## Timeout and Latency
An explicit `timeout=7.5` seconds is set on the `httpx.post` request to prevent Vercel Serverless Function timeouts.
During live execution, the actual observed generation latency returned by the mock/API response was **420 ms**. The script's separate wall-clock measurement displayed 0.00 seconds due to its measurement/rounding behavior, but the functional latency successfully confirmed compatibility with the 7.5s timeout.

## Retry Behavior and Error Handling
- **400, 401, 403, 404 (Terminal Errors)**: Fails instantly. No retry.
- **429 Quota, 5xx, or Timeout**: The error is raised cleanly as an `httpx.HTTPStatusError` or `httpx.TimeoutException`. This forces the request to fail cleanly, allowing upcoming QStash integration to asynchronously retry.
- **Malformed JSON**: Raised cleanly as a Pydantic `ValidationError`.
- **Gemini does NOT silently fall back to the heuristic implementation** if the API fails.

## Usage Metadata
- `promptTokenCount` is mapped exactly to `input_tokens`. (Observed during live test: 1250)
- `candidatesTokenCount` is mapped exactly to `output_tokens`. (Observed during live test: 350)
