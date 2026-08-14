# Phase 21.1 — Gemini Provider Audit

## 1. Current OpenAI Implementation

### Models Used
- **Embeddings:** `text-embedding-3-small` (1536 dimensions)
- **Scoring (LLM):** `gpt-4o-2024-08-06`

### Operations and Requirements
| Operation | Model Used | Requires Embeddings? | Output Format | Input Format |
|-----------|------------|----------------------|---------------|--------------|
| `generate_embedding` (Candidate) | `text-embedding-3-small` | YES | 1536-dim `list[float]` | Raw string (`text`) |
| `generate_embedding` (Job) | `text-embedding-3-small` | YES | 1536-dim `list[float]` | Raw string (`text`) |
| `evaluate` (Scoring Engine) | `gpt-4o-2024-08-06` | NO | Structured JSON (`dict`) | Templated string (`PromptBuilder`) |
| `parse` (Resume Engine) | SpaCy (No LLM currently) | NO | Structured JSON (`dict`) | Raw string |

### Error & Usage Handling
- **Failures/Retries:** OpenAI client is instantiated with `max_retries=3`. In production, failures raise exceptions. In non-production, embeddings fall back to a deterministic deterministic vector generator.
- **Timeouts:** Implicitly relies on OpenAI defaults. The new architecture needs a <10s timeout to respect Vercel limits.
- **Token Tracking:** `generate_embedding` captures `response.usage.prompt_tokens` and `total_tokens` and writes to `AIUsageLog`.

### Existing Abstractions
- `EmbeddingGenerator` abstracts the LLM provider. It can cleanly support Gemini by checking an environment variable or model string.
- `AIScoringEngine` abstracts scoring. It can support Gemini since it expects a generic `dict` output.
- `ResumeParser` abstracts extraction. It can easily swap SpaCy for a Gemini LLM call.

## 2. Gemini Candidate Architecture

### Discovered Live Models (Dynamic Discovery)
The live `ModelService.ListModels` API revealed 50 available models for the current API key.
- **LLM/Structured Output (Second Attempt Error):** The initial script erroneously selected `gemini-2.5-flash-image`, a multimodal image model that hit a strict quota limit (HTTP 429) for `generate_content_free_tier`. The selector has been updated to specifically exclude `image`, `video`, `audio`, and `embedding` variants to isolate a pure text model suitable for rapid JSON extraction.
- **Embeddings:** `gemini-embedding-001`. 

### ✅ DIMENSIONALITY COMPATIBILITY CONFIRMED
- **OpenAI:** 1536 dimensions.
- **Gemini (`gemini-embedding-001`):** The actual live API execution confirms that supplying the parameter `outputDimensionality: 1536` returns exactly 1536 dimensions.
- **Conclusion:** **Gemini embeddings are natively COMPATIBLE with the current `vector(1536)` database schema.** No database migration or schema alteration is necessary.

## 3. Compatibility Matrix (Pending Final Text Test)

| Capability | Hiron Current | Gemini Actual | Result |
|---|---|---|---|
| Text generation | OpenAI LLM | *(Pending Test)* | *(Pending)* |
| Structured JSON | OpenAI structured output | *(Pending Test)* | *(Pending)* |
| Resume parsing | SpaCy | Gemini | *(Pending)* |
| AI scoring | OpenAI | Gemini | *(Pending)* |
| Embeddings | `vector(1536)` | `gemini-embedding-001` | **PASS** |
| Embedding dimensions | 1536 | 1536 | **PASS** |
| Usage metadata | `AIUsageLog` | Gemini metadata | *(Pending)* |

## 4. Current Environment State
- **`GEMINI_API_KEY`**: MISSING

*Execution of the isolated POC will test the network authentication and payload compatibility directly against the Google REST API using `httpx` to avoid touching dependency graphs.*
