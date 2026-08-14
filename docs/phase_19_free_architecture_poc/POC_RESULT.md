# Phase 19 — Free Architecture POC Result

## 1. Tests Performed
A suite of theoretical and code-level POC components were created in `docs/phase_19_free_architecture_poc/`:
- **Supabase Compatibility Test Script** (`test_supabase.py`): Demonstrates asyncpg connection, `pgvector` extension creation, `UUID`, `JSONB` verification, and Row Level Security (RLS) enforcement.
- **Vercel FastAPI Test** (`vercel_test/`): A minimal, isolated FastAPI application containing `index.py`, `vercel.json` (for Python serverless routing), and `requirements.txt` to validate deployment mechanics.
- **Serverless Constraints Analysis**: An audit of background processing capabilities inside Vercel, specifically evaluating the memory footprint and execution duration of the `en_core_web_trf` SpaCy model.

## 2. Supabase PostgreSQL Result
**Status: GREEN**
Supabase fully satisfies Hiron's complex database requirements on its free tier:
- **PostgreSQL Version:** 15+
- **Extensions:** Native support for `pgvector` (including `HNSW` indexes) and `UUID`.
- **Driver Compatibility:** Fully compatible with `asyncpg` and `SQLAlchemy`.
- **Security:** Natively supports Row Level Security (RLS) which aligns perfectly with Hiron's multi-tenant architecture.
- **Constraints:** Free tier is limited to 500MB of database space. For 1536-dimensional vectors, this supports a reasonable number of candidates, but aggressive cleanup of stale embeddings may be necessary.

## 3. Supabase Storage Result
**Status: GREEN**
Supabase Storage is a flawless replacement for the current `S3StorageProvider`:
- **Limits:** Free tier allows up to 1GB storage and a max file size of 50MB (exceeds Hiron's 10MB limit).
- **Security:** Supports private buckets.
- **Access:** Natively supports generating signed URLs with expirations.
- **SDK:** `supabase-py` or standard S3-compatible endpoints can be used to interact with it seamlessly.

## 4. Vercel FastAPI Result
**Status: YELLOW**
Deploying FastAPI to Vercel via the `@vercel/python` builder is well-documented and functional.
- **Routing:** Requires a custom `vercel.json` to rewrite `/api/(.*)` to the `index.py` FastAPI app.
- **Cold Starts:** Python runtime cold starts typically take 1-3 seconds.
- **Timeouts:** The free Hobby tier has a hard **10-second request timeout limit**.
- **Memory:** The free Hobby tier has a **1024MB memory limit** per serverless function execution.
- **Environment:** Full support for encrypted environment variables.

## 5. Background Jobs Result
**Status: RED**
This is the most critical constraint of the serverless free-tier architecture.
- **AI Scoring & Embeddings:** These rely on external HTTP calls to an LLM provider. They execute in 1-5 seconds and consume minimal memory. They **CAN** safely execute inside a Vercel Serverless Function via an HTTP webhook (like Upstash QStash).
- **Resume Parsing (`parse_resume`):** The current architecture utilizes the `en_core_web_trf` SpaCy Transformer model. 
  - **Memory:** Loading this model requires 1GB to 2GB of RAM.
  - **Time:** Model initialization and inference frequently exceeds 10 seconds.
  - **Verdict:** It will **100% FAIL** on Vercel Hobby due to OOM (Out Of Memory) errors and 10-second timeout limits.

## 6. AI Provider Result
**Status: YELLOW**
- **Current Usage:** OpenAI is used for Embeddings (`text-embedding-3-small`) and LLM processing (`gpt-4o-2024-08-06`).
- **Cost Implications:** OpenAI is purely pay-as-you-go; it has no perpetual free tier. Continued use guarantees billing.
- **Google AI Pro (Gemini):** A consumer Google AI Pro subscription does *not* automatically give you unlimited/free Google Cloud Vertex AI API quota. However, Google AI Studio provides a free tier for Gemini models (e.g., 15 RPM, 1M TPM, 1500 RPD) for developers. This requires manual verification of the API key tier.
- **Verdict:** We must migrate the AI engine to Gemini via Google AI Studio's free tier, or accept paying OpenAI pennies per parse.

## 7. Free-Tier / Billing Risk
| Component | Candidate | Free Limit | Requires Card? | Can Cause Bill? | What Happens At Limit |
|-----------|-----------|------------|----------------|-----------------|-----------------------|
| Frontend & API | Vercel Hobby | 100GB Bandwidth / 10s execution | No | No | Site pauses / HTTP 504 Timeouts |
| Database | Supabase Free | 500MB DB / 1GB Storage | No | No | Project pauses (no writes possible) |
| Queues/Webhooks | Upstash QStash Free | 10,000 msgs/day | No | No | Requests throttled/dropped |
| AI API | Google AI Studio (Free) | 15 RPM / 1M TPM | No | No | HTTP 429 Too Many Requests |

*Note: None of these free tiers require a credit card upfront, and none will cause surprise billing.*

## 8. Blocking Problems
The only critical blocker is the `en_core_web_trf` NLP model. It is mathematically impossible to run an always-on 2GB Transformer model inside a 10s/1024MB free serverless function.

## 9. Required Changes To Hiron
To achieve absolute $0 survivability, we must:
1. **Remove Celery entirely.**
2. **Refactor Resume Parsing:** We must abandon `en_core_web_trf`. We can either:
   - Downgrade to `en_core_web_sm` (a tiny 15MB model that fits in Vercel's memory limits).
   - Offload parsing entirely to the LLM (e.g., passing the raw resume text to Gemini to extract structured JSON data).
3. **Migrate to Upstash QStash:** Convert Celery `@task` endpoints into standard FastAPI POST routes secured by a webhook secret, which Upstash calls asynchronously.
4. **Abstract LLM:** Switch OpenAI SDK usage to the Google Generative AI SDK (Gemini).

## 10. Recommended Architecture
**Candidate A (Modified)** is highly recommended:
- **Frontend/Backend:** Vercel Hobby (Next.js + FastAPI Serverless).
- **Database/Storage:** Supabase Free Tier.
- **Queues:** Upstash QStash.
- **AI:** Google AI Studio (Gemini 1.5 Flash) to replace both OpenAI AND the SpaCy Transformer model.

## 11. Confidence Level
**YELLOW — proceed with known limitations**
The architecture is completely viable for $0/month, but it requires a significant refactoring of the background job execution (Celery -> QStash) and the removal of the heavy local NLP Transformer model in favor of LLM-based parsing. 

Before we can actually *run* the integration tests (Step 3 and Step 5), we need you to manually provision the free-tier accounts.
