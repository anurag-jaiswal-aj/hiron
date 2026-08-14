# 2. AI Provider Migration Strategy

## Step 1: Audit of Every AI Call
- **Embeddings**: `EmbeddingGenerator.generate_embedding` (Calls `openai.OpenAI.embeddings.create`, writes to `AIUsageLog`).
- **Scoring**: `AIScoringEngine.evaluate` (Currently mocks generation, targeted for `gpt-4o-2024-08-06`).
- **Parsing**: `ResumeParser.parse` (Currently uses SpaCy, targeted for Gemini structured extraction).

## Step 2: Design Provider Abstraction
Instead of directly calling `openai` or `httpx` in business logic, we will define an interface:
```python
class LLMProvider(Protocol):
    async def generate_structured(self, prompt: str, schema: dict) -> tuple[dict, AIUsageData]: ...
    
class EmbeddingProvider(Protocol):
    async def generate_embedding(self, text: str) -> tuple[list[float], AIUsageData]: ...
```

## Step 3: Usage Accounting Mapping
Current `AIUsageLog` tracks:
- `input_tokens`, `output_tokens`, `total_tokens`, `cost_usd`, `latency_ms`

Gemini metadata mappings:
- `promptTokenCount` -> `input_tokens`
- `candidatesTokenCount` -> `output_tokens`
- `totalTokenCount` -> `total_tokens`
- `thoughtsTokenCount` -> Logged as extra JSON metadata.
- Cost: We must remove OpenAI-specific hardcoded costs and configure a generic cost calculator based on Gemini's free-tier ($0.00).

## Step 4: Retries and Timeouts
- Use `tenacity` for exponential backoff on `HTTP 429` (Rate Limit) and `HTTP 503` (Service Unavailable).
- Max 3 retries, capped at 8 seconds total execution to avoid Vercel 10s timeouts.
- Fallback to QStash retry mechanism for persistent failures.
