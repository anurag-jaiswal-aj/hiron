# 1. Migration Architecture Overview

## A. Current Architecture
- **LLM/Embeddings**: OpenAI (`gpt-4o-2024-08-06`, `text-embedding-3-small` outputting 1536 dims).
- **Resume Parsing**: Local NLP execution using `spacy` (`en_core_web_trf`).
- **Async Execution**: Celery workers consuming tasks from Redis broker.
- **Tasks**: `parse_resume`, `generate_candidate_embedding`, `generate_job_embedding`, `execute_batch_scoring` (synchronous loop over N candidates).
- **Storage/DB**: Supabase PostgreSQL + pgvector(1536) + HNSW, S3/Supabase Storage.

## B. Target Architecture
- **LLM/Embeddings**: Google Gemini (`gemini-3.6-flash` for structured output, `gemini-embedding-001` outputting 1536 dims).
- **Resume Parsing**: Gemini `gemini-3.6-flash` for structured NER/entity extraction + local regex for deterministic fields.
- **Async Execution**: Upstash QStash delivering webhooks to Vercel Serverless Functions.
- **Tasks**: Vercel API routes protected by QStash signature validation.
- **Batch Processing**: QStash fan-out (1 message per candidate) instead of synchronous looping, storing batch progress in PostgreSQL.

## C. Complete Migration Dependency Graph
1. **Foundation**: Implement `GeminiProvider` abstraction + add `QSTASH_*` and `GEMINI_API_KEY` to environment variables.
2. **Provider Switch (Embeddings)**: Migrate `EmbeddingGenerator` to use `GeminiEmbeddingProvider`.
3. **Provider Switch (Scoring)**: Migrate `AIScoringEngine` to use `GeminiProvider` for structured outputs.
4. **Provider Switch (Parsing)**: Rewrite `ResumeParser` to use `GeminiProvider` instead of SpaCy.
5. **Task Migration (QStash)**: Convert Celery `@task` definitions to FastAPI webhook endpoints. Implement fan-out for Batch Scoring.
6. **Infrastructure Cleanup**: Remove Celery, Redis broker configuration, SpaCy models, and OpenAI dependencies.

## D. Files that will eventually change
- `apps/api/hiron/embeddings/generator.py` (Add Gemini)
- `apps/api/hiron/scores/engine.py` (Add Gemini Structured JSON)
- `apps/api/hiron/resumes/parser.py` (Remove SpaCy, Add Gemini)
- `apps/api/hiron/*/tasks.py` (Remove Celery, convert to webhooks)
- `pyproject.toml` (Dependency changes)

## E. Files that must NOT change
- `hiron.candidates.models`, `hiron.jobs.models` (Database schema unchanged)
- Alembic migrations (No schema modifications for vector dimensions!)

## F. Database changes required
- **NONE for Embeddings**: 1536 dimensionality natively supported by `gemini-embedding-001`.
- *Minor*: New table required for tracking batch scoring fan-out progress (e.g., `BatchScoreJob`).

## G. External infrastructure changes
- Remove Redis (ElastiCache/Redis).
- Remove ECS Celery Worker containers.
- Add Upstash QStash account configurations.

## H. Risks
- Vercel execution timeouts (10s max for Hobby).
- Gemini API quota/rate limits (HTTP 429).
- Hallucinations during Resume Parsing.

## I. Rollback strategy
- Implement feature flags (`USE_GEMINI_PROVIDER=True`, `USE_QSTASH=True`).
- Retain OpenAI and Celery code paths until the very final phase.
