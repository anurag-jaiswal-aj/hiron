# Hiron Free Architecture Audit

## 1. Executive Summary
This audit evaluated the Hiron monolithic architecture to determine its viability for a $0/month deployment following the teardown of the AWS Phase 18 infrastructure. The application is a highly modern, modular FastAPI and Next.js stack. Because the backend leverages abstractions for storage and caching, migrating to a free serverless architecture is highly feasible. The primary challenge is replacing the always-on Celery workers and securing a free PostgreSQL database that supports `pgvector` and Row-Level Security (RLS). 

## 2. Current Architecture
- **Frontend:** Next.js 14 (React 18)
- **Backend:** Python 3.12, FastAPI, Uvicorn
- **Database:** PostgreSQL 16 (via asyncpg & SQLAlchemy) with Alembic migrations
- **Background Jobs:** Upstash QStash (Serverless HTTP Webhooks)
- **Caching & Rate Limiting:** Redis
- **Storage:** Abstracted provider (Supabase Storage)
- **AI/NLP:** OpenAI API (Embeddings & LLM Scoring) and SpaCy (local NER)

## 3. Backend Audit
- **Framework:** FastAPI running on Python 3.12.
- **Entry Point:** `apps/api/hiron/main.py`.
- **API Routes:** Comprehensive REST API (Health, Auth, Tenants, Users, Jobs, Candidates, Resumes, Embeddings, AI Scoring, Search, Pipeline, Dashboard, Audit, Tasks, AI Usage).
- **Authentication/Authorization:** JWT (RS256) with Argon2id password hashing and TenantIsolationMiddleware.
- **Database ORM:** SQLAlchemy with Asyncpg driver.
- **Migrations:** Alembic.
- **File Uploads:** Handled via custom StorageProvider interface.
- **AI/LLM:** Extensive integration for scoring and embeddings.

## 4. Database Audit
- **Tables & Schema:** Highly structured, multi-tenant schema spanning roughly 15 tables (tenants, users, jobs, candidates, resumes, embeddings, scores, etc.).
- **PostgreSQL Specifics:** The codebase has a hard dependency on PostgreSQL. It uses `UUID` columns, `JSONB`, Row-Level Security (RLS) migrations, and critically, `pgvector` for HNSW vector indexing on candidate and job embeddings.
- **SQLite Compatibility:** SQLite cannot replace PostgreSQL here without a massive rewrite of the vector search mechanics and security models. A free PostgreSQL provider is mandatory.

## 5. Redis Audit
Redis is currently utilized for two primary purposes:
1. **Rate Limiting:** `RateLimitMiddleware` (supports an automatic graceful fallback to in-memory dictionary if Redis is absent).
2. **Application Caching:** `CacheManager` (also supports automatic fallback to in-memory TTL cache).
*(Note: Celery broker dependencies have been completely removed.)*

## 6. Background Jobs Audit
- **Former Usage:** Celery was previously used for `parse_resume` (SpaCy NLP pipeline), `generate_candidate_embedding` (OpenAI), and AI scoring.
- **Current Architecture:** Background processing has been fully migrated to **Upstash QStash**, an HTTP-invoked task queue. Heavy parsing/embedding tasks are now dispatched as webhook requests to internal FastAPI endpoints (e.g., `/api/v1/webhooks/qstash/*`).
- **Assessment:** This stateless design is fully compatible with serverless timeouts and Vercel Hobby limits, officially eliminating the need for an always-on Celery worker.

## 7. File Storage Audit
- **Usage:** Stores candidate resumes (PDF/DOCX/TXT) up to 10MB.
- **Implementation:** Cleanly abstracted via `StorageProvider` (`LocalStorageProvider` and `S3StorageProvider`).
- **Requirements:** Requires pre-signed URL generation for secure, temporary frontend access.
- **Assessment:** Easily swappable to a free object storage tier (e.g., Supabase Storage, Cloudflare R2).

## 8. AI/LLM Audit
- **Provider:** OpenAI (`gpt-4o-2024-08-06` for scoring, `text-embedding-3-small` for embeddings).
- **Local AI:** SpaCy (`en_core_web_trf`) for deterministic/fallback resume parsing.
- **Assessment:** AI is mandatory for core application logic (scoring and semantic search). LLM API costs are external to cloud infrastructure hosting. (Note: Google AI Pro/Gemini API integration may provide a free alternative, pending further quota investigation).

## 9. Frontend Audit
- **Framework:** Next.js 14.
- **Build:** Standard `pnpm` workspace build.
- **Assessment:** Fully compatible with Vercel Hobby tier out of the box with zero code changes required.

## 10. AWS Dependencies
- The application currently relies on AWS solely through the `S3StorageProvider` for resume storage. 
- Infrastructure assumptions (VPC, ECS, ALB) existed only in Terraform configuration and GitHub Actions deployment scripts, not within the application source code itself.

## 11. Free Architecture Candidates

### Candidate A (Recommended)
- **Frontend & Backend:** Vercel (Next.js + Python Serverless Functions).
- **Database & Storage:** Supabase Free Tier (PostgreSQL with pgvector, RLS, and S3-compatible Object Storage).
- **Background Jobs:** Upstash QStash (HTTP queues) invoking Vercel Serverless Functions, or Supabase Edge Functions.

### Candidate B
- **Frontend & Backend:** Cloudflare Pages + Cloudflare Workers.
- **Database:** Cloudflare D1 + Vectorize.
- **Assessment:** **REJECTED.** Rewriting the massive Python/FastAPI backend and SQLAlchemy ORM into JavaScript for Cloudflare Workers is a massive, unnecessary undertaking that violates the core Python compatibility requirement.

### Candidate C
- **Frontend:** Vercel.
- **Backend:** Render Free Tier (Python web service).
- **Database:** Neon Free Tier (PostgreSQL with pgvector).
- **Assessment:** Feasible, but Render's free tier spins down after 15 minutes of inactivity, resulting in painful 50-second cold starts. 

## 12. Comparison Matrix

| Feature | Candidate A (Vercel+Supabase) | Candidate B (Cloudflare) | Candidate C (Vercel+Render+Neon) |
| :--- | :--- | :--- | :--- |
| **$0 Viability** | Yes | Yes | Yes |
| **Python Compatibility**| Excellent (Vercel Python) | **Fail (Requires JS rewrite)**| Excellent |
| **PostgreSQL & Vector** | Excellent (Supabase) | **Fail (D1 lacks Postgres parity)**| Excellent (Neon) |
| **Redis Requirement** | Removable | Removable | Removable |
| **Background Jobs** | Upstash QStash / Serverless | Cloudflare Queues | In-memory `BackgroundTasks` |
| **File Storage** | Supabase Storage | Cloudflare R2 | S3/Supabase Storage |
| **Cold Starts** | Moderate (Serverless Boot) | Fast | Severe (Render sleep) |

## 13. Recommended Architecture
**Candidate A (Vercel + Supabase + Upstash)** is the only viable $0 architecture that preserves the existing Python FastAPI codebase, SQLAlchemy ORM, pgvector requirements, and eliminates the need for an always-on ECS/RDS/Celery footprint.

## 14. Migration Requirements
- **No-code changes:** Frontend deployment (Vercel), Database migrations execution (Alembic to Supabase).
- **Configuration changes:** `vercel.json` routing configuration to map `/api/*` to the FastAPI entrypoint; updating environment variables.
- **Small code changes:** Implement a `SupabaseStorageProvider` (conforming to the existing `StorageProvider` interface).
- **Architecture changes:** Rip out Celery. Replace `celery_app.task` decorators with FastAPI `BackgroundTasks` (for lightweight tasks) or an Upstash QStash HTTP webhook endpoint (for heavy parsing/embedding tasks) to ensure Vercel doesn't kill the process prematurely.

## 15. Risks
- **Serverless Limits:** Vercel Hobby limits serverless function execution to 10 seconds. The SpaCy transformer model (`en_core_web_trf`) is memory-heavy and may take longer than 10s to boot and infer in a serverless environment. If this occurs, we may need to rely solely on the LLM or deterministic regex parsing for resumes, or offload it to a free external service.
- **Database Storage Limits:** Supabase Free Tier provides 500MB of database storage. Given the 1536-dim embeddings, this will comfortably hold thousands of candidates and jobs, but not millions.
- **AI API Exhaustion:** If OpenAI credits reach $0, embedding generation will fall back to the deterministic mock vectors (as implemented in `embeddings/generator.py`), degrading AI search accuracy. 

## 16. $0 Survivability Assessment
**"If the user's AWS credits become exactly $0 tomorrow, does Hiron still work?"**
**YES.** 
Vercel Hobby, Supabase Free, and Upstash Free do not require a credit card to spin up, and they simply throttle or pause when limits are hit rather than generating surprise bills. 
- **What stops working:** If the 500MB DB limit is hit, writes will fail. 
- **What sleeps:** Vercel serverless functions spin down immediately after request execution (minor 1-2s cold start for Python). Supabase free tier pauses after 1 week of zero activity (requires manual clicking in dashboard to unpause).

## 17. Proposed Migration Phases
1. **Database & Storage Provisioning:** Spin up Supabase, apply Alembic migrations, configure Supabase Storage bucket. *(Completed)*
2. **De-Celerying:** Remove Celery dependencies; implement HTTP-based background task workers compatible with serverless timeouts using Upstash QStash. *(Completed)*
3. **FastAPI Serverless Adaptation:** Add `vercel.json` and ensure FastAPI boots cleanly in a stateless environment.
4. **Vercel Deployment:** Deploy frontend and backend to Vercel Hobby tier.
