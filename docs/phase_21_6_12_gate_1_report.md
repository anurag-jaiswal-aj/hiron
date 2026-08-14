# Phase 21.6.12 Gate 1: Vercel + Supabase Production Readiness Audit

## Current State & Evidence

### 1. Vercel Readiness
- **Frontend (`apps/web`)**: **IMPLEMENTED**. Next.js configuration (`next.config.mjs`, `package.json`) is standard and natively supported by Vercel deployments.
- **Backend (`apps/api`)**: **MISSING**. FastAPI currently runs via `uvicorn` in `apps/api/hiron/main.py`. There is no `vercel.json` and no `api/index.py` serverless entrypoint in the repository root or the `apps/api` root.
- **Evidence**: `find . -name "vercel.json"` yielded no configurations outside of a previous Phase 19 POC directory.

### 2. Supabase Readiness
- **Database (`PostgreSQL + pgvector`)**: **IMPLEMENTED**. The application connects via standard `DATABASE_URL` asyncpg connection strings (`apps/api/hiron/core/config.py`). Alembic migrations dynamically load this URL and are completely compatible with Supabase's transaction pooler (Supavisor).
- **Storage**: **MISSING**. `apps/api/hiron/storage/provider.py` contains `LocalStorageProvider` and the legacy mock `S3StorageProvider`. There is no `SupabaseStorageProvider`.
- **Evidence**: Inspected `provider.py`; the S3 implementation simply returns mock strings and must be rewritten to use Supabase Storage APIs.

### 3. Upstash Readiness
- **QStash Integration**: **IMPLEMENTED**. Fully integrated via `apps/api/hiron/core/qstash_client.py` and webhook routers.
- **Redis Integration**: **PARTIAL**. The application uses `redis.asyncio` for the `CacheManager` and `RateLimitMiddleware`. While `CacheManager` has an in-memory fallback, `RateLimitMiddleware` strongly depends on Redis (`pipe = redis_client.pipeline()`).
- **Serverless Architecture Constraint**: Because Vercel serverless functions are ephemeral, an "in-memory fallback" is wiped on every invocation. Thus, an actual Upstash Redis instance is strictly **REQUIRED** for production rate limiting and caching.

## Environment Variable Inventory

| VARIABLE | USED BY | REQUIRED FOR PRODUCTION | CURRENTLY CONFIGURED | SOURCE |
|---|---|---|---|---|
| `DATABASE_URL` | SQLAlchemy / Alembic | YES | `.env.local` (local) | Supabase DB |
| `REDIS_URL` | RateLimiter / Cache | YES | `.env.local` (local) | Upstash Redis |
| `QSTASH_TOKEN` | QStash Client | YES | `.env.local` (active) | Upstash QStash |
| `QSTASH_CURRENT_SIGNING_KEY` | QStash Webhooks | YES | `.env.local` (active) | Upstash QStash |
| `QSTASH_NEXT_SIGNING_KEY` | QStash Webhooks | YES | `.env.local` (active) | Upstash QStash |
| `QSTASH_WEBHOOK_URL` | App settings | YES | `.env.local` (ngrok) | Vercel URL |
| `OPENAI_API_KEY` | AI Service | YES | `.env.local` (active) | OpenAI |
| `JWT_PRIVATE_KEY_PATH` | Auth Service | YES | `.env.local` (file) | Must change to ENV string |
| `JWT_PUBLIC_KEY_PATH` | Auth Service | YES | `.env.local` (file) | Must change to ENV string |

## Deployment Blockers

| Blocker | Severity | Resolution |
|---|---|---|
| **FastAPI Vercel Entrypoint** | **BLOCKER (High)** | Must create `api/index.py` exposing the FastAPI `app` instance to Vercel. |
| **Vercel Build Config** | **BLOCKER (High)** | Must create `vercel.json` defining `@vercel/python` builder for the `api/` directory and routing rules. |
| **Supabase Storage Implementation** | **BLOCKER (High)** | Must implement `SupabaseStorageProvider` in `apps/api/hiron/storage/provider.py`. |
| **JWT Key File Dependency** | **MEDIUM** | Auth currently reads RSA keys from local files (`keys/jwt_private.pem`). Serverless deployments should inject these directly as environment variable strings (e.g., `JWT_PRIVATE_KEY_CONTENT`). |

## Architecture Verification

| Component | Target Architecture | Current Repository Status |
|---|---|---|
| Frontend | Next.js on Vercel | **IMPLEMENTED** |
| Backend | FastAPI on Vercel Serverless | **MISSING** (Needs config) |
| Database | Supabase PostgreSQL | **IMPLEMENTED** (Config-ready) |
| Storage | Supabase Storage | **MISSING** (Needs Provider class) |
| Async Jobs | Upstash QStash | **IMPLEMENTED** |
| Cache/RateLimit | Upstash Redis | **PARTIAL** (Needs real instance, no code changes required) |

## Recommended Implementation Order

1. **Storage Transition**: Implement `SupabaseStorageProvider` and update dependency injection.
2. **Security Transition**: Update Auth service to accept JWT RSA keys as string environment variables instead of file paths.
3. **Vercel Backend Configuration**: Create `api/index.py` and `vercel.json`.
4. **Vercel Linking**: Authenticate Vercel CLI and link the project.
5. **Environment Injection**: Provision Supabase DB and Upstash Redis, then inject all secrets into Vercel.
6. **Deployment**: Push to main / trigger Vercel build.

**STATUS: WAITING FOR APPROVAL**
