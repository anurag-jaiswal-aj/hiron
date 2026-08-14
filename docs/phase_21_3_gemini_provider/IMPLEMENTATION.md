# Phase 21.3 - Gemini Provider & Embedding Implementation

## Files Changed
- `apps/api/hiron/core/config.py`: Added `ai_provider`, `gemini_api_key`, `gemini_embedding_model`, and `gemini_llm_model` to configuration while explicitly preserving `OPENAI_API_KEY`.
- `apps/api/hiron/embeddings/generator.py`: Updated `EmbeddingGenerator` to gracefully support both OpenAI (via SDK) and Gemini (via REST `httpx`) concurrently.
- `apps/api/tests/test_embedding_generator_gemini.py`: Added 11 focused tests covering new Gemini capabilities.

## Provider Abstraction
The `EmbeddingGenerator` now acts as a multi-provider handler using `self.ai_provider = settings.ai_provider`. Based on configuration, it routes either to `openai.embeddings.create` or sends an `httpx.post` request to `generativelanguage.googleapis.com`. Both return a uniform `EmbeddingGenerationResult` dataclass.

## Configuration
Added to `.env` conventions:
- `AI_PROVIDER=gemini` (defaults to `openai` to ensure backwards compatibility).
- `GEMINI_API_KEY=...`
- `GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001`

## Embedding Request Format
Gemini embeddings are generated using:
```json
{
  "model": "models/gemini-embedding-001",
  "content": {"parts": [{"text": "..."}]},
  "outputDimensionality": 1536
}
```

## 1536-Dimensional Compatibility
By explicitly specifying `outputDimensionality: 1536` in the request payload, Gemini natively returns a 1536-dimensional float list. This cleanly fits into Hiron's existing `vector(1536)` pgvector column without any padding, truncation, or database schema migration.

## Usage Metadata Mapping
Gemini REST API returns usage metadata under `usageMetadata` (e.g. `promptTokenCount`, `totalTokenCount`). 
- `promptTokenCount` is mapped to `input_tokens` in `EmbeddingGenerationResult`.
- `totalTokenCount` is mapped to `total_tokens`.
Cost USD remains unset (`0.0`) as per the architectural design, eliminating incorrect OpenAI pricing mappings for Gemini workloads.

## Error Handling & Timeout/Retry Policy
- **Timeout**: The `httpx` POST is strictly configured with a `7.5s` timeout to ensure safety under Vercel Serverless environments. 
- **Error Types**: If an `httpx.HTTPStatusError` (like 429 Quota or 503) or `httpx.TimeoutException` is encountered, the generator logs the error and gracefully falls back to deterministic mock vectors out-of-production, propagating the error cleanly in production.

## OpenAI Fallback
The `OPENAI_API_KEY` configuration is preserved. Setting `AI_PROVIDER=openai` instantly reverts the generator to using the existing `openai` client. OpenAI compatibility was maintained and explicitly verified via test isolation.
