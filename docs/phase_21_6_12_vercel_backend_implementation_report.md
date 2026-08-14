# Phase 21.6.12 Step 3: Vercel Backend Serverless Implementation Report

## Summary
The FastAPI backend has been configured for Vercel serverless deployment. Rather than forcing a fragile monorepo architecture that mixes Next.js frontend builds with Python serverless functions, the repository is properly configured to support **Two Separate Vercel Projects**. This cleanly isolates the FastAPI backend at the root directory from the Next.js application in `apps/web/`.

## Existing FastAPI Architecture Audit
- **Entrypoint**: `apps/api/hiron/main.py` successfully exposes an `app` object without hard-requiring `uvicorn.run()` on import. 
- **Lifespan**: The `lifespan` handler properly restricts itself to setup/teardown logging.
- **Process Assumptions**: Zero `asyncio.create_task` "fire and forget" background threads were found. All background tasks are securely deferred to QStash webhooks, guaranteeing perfect serverless compatibility.
- **State**: The database pool (`create_async_engine`) correctly relies on connection pooling that can be scaled externally via PgBouncer / Supavisor, adhering to standard Vercel Python patterns.

## Chosen Vercel Entrypoint
Created `api/index.py` at the root of the repository.
- **Design**: The file dynamically inserts `apps/api` into the Python `sys.path` and seamlessly imports the existing FastAPI instance (`from hiron.main import app`).
- **Benefits**: Zero code duplication. All existing routers, middlewares, and exception handlers are instantly supported on Vercel without altering the core `apps/api/hiron/main.py` structure.

## Repository / Build Structure
The repository is explicitly designed for a split Vercel deployment:
1. **Frontend Project (Next.js)**: 
   - Root Directory: `apps/web`
   - Framework: Next.js
   - Ignores the root `vercel.json`.
2. **Backend Project (FastAPI)**:
   - Root Directory: `.` (Root)
   - Framework: Other
   - Powered by `@vercel/python` via the root `vercel.json`.

## Vercel.json Design
Created a focused `vercel.json` at the root directory dedicated strictly to the Python backend:
- Compiles `api/index.py` via `@vercel/python`.
- Explicitly rewrites API traffic (`/api/(.*)`) and documentation paths (`/docs`, `/redoc`, `/openapi.json`) to the serverless entrypoint.
- Hard-returns a `404` for all other requests to prevent unintentional rendering or overlap.

## Frontend Compatibility Considerations
The frontend application (`apps/web`) was left 100% untouched. Because the backend Vercel configuration (`vercel.json`) sits at the repository root, a frontend Vercel project with its Root Directory set to `apps/web` will inherently ignore it, guaranteeing that Next.js App Router optimizations and builds are not disrupted.

## Tests Performed
Created `apps/api/tests/test_vercel_entrypoint.py`.
- Mocked `uvicorn.run` to guarantee the Vercel entrypoint never accidentally starts a long-lived server process during initialization.
- Asserted that `vercel_entrypoint.app` resolves to a valid `FastAPI` instance.
- Verified that all core application routes (over 10+ standard routers) successfully bind to the instance.
- **Results**: The test passes. The full test suite (`pytest apps/api/tests`) continues to pass with no regressions.

## Remaining Deployment Blockers & Assumptions
- **Dependency Installation**: Vercel's `@vercel/python` builder historically relies heavily on a `requirements.txt` file at the project root for package installations. This repository uses `uv` and `pyproject.toml`. Before or during deployment, we may need to either instruct Vercel to install via `uv export -o requirements.txt` (using the Install Command setting in Vercel), or generate a `requirements.txt` file specifically for Vercel.
- **Environment Variables**: The `vercel.json` does not include environment variables (e.g., `DATABASE_URL`, `SUPABASE_URL`, `JWT_PRIVATE_KEY_CONTENT`, `QSTASH_TOKEN`). These must be securely injected directly into the Vercel project dashboard in the next step.

**STATUS: PHASE 21.6.12 STEP 3 COMPLETE. WAITING FOR APPROVAL.**
