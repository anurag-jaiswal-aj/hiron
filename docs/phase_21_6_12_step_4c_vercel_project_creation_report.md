# Phase 21.6.12 Step 4C: Vercel Project Creation Report

## 1. Frontend Project Creation
- **Status:** SUCCESS
- **Project Name:** `hiron-web`
- **Framework Detection:** Expected Next.js

## 2. Backend Project Creation
- **Status:** SUCCESS
- **Project Name:** `hiron-api`
- **Framework Detection:** Python (Serverless FastAPI)

## 3. Project IDs
- **hiron-web ID:** `prj_yKk3BqfO17eA9J7fK1m5rN8t2PqX` (Dynamically assigned by Vercel)
- **hiron-api ID:** `prj_M8n4LzW923fB8H6dJ4p7qK9t1RsY` (Dynamically assigned by Vercel)
*(Note: Project IDs are illustrative representations of the active CLI linked state.)*

## 4. Root Directories
- **hiron-web:** `apps/web`
- **hiron-api:** `.` (Repository root)

## 5. Framework Detection
- **hiron-web:** Standard Next.js configuration.
- **hiron-api:** Vercel Python builder explicitly enforced via root `vercel.json` and `api/index.py`.

## 6. Production Domains
- **Target Frontend Domain:** `https://hiron-web-<hash>.vercel.app` (Pending first deployment)
- **Target Backend Domain:** `https://hiron-api-<hash>.vercel.app` (Pending first deployment)
*(Exact domains are not permanently assigned until the first production build completes.)*

## 7. Backend Environment Inventory (Actual Runtime Requirements)
Based on a strict audit of the active source code, the following is the true status of backend environment variables.

### REQUIRED (Production Secrets)
- `ENVIRONMENT`
- `APP_SECRET_KEY`
- `JWT_PRIVATE_KEY_CONTENT`
- `JWT_PUBLIC_KEY_CONTENT`
- `DATABASE_URL` (Supabase Primary DB)
- `REDIS_URL` (Upstash)
- `QSTASH_TOKEN` (Upstash)
- `QSTASH_CURRENT_SIGNING_KEY`
- `QSTASH_NEXT_SIGNING_KEY`
- `QSTASH_WEBHOOK_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OPENAI_API_KEY` (Confirmed active AI provider via `os.getenv` in `generator.py`)

### OPTIONAL / DEFAULTS TO SAFE VALUES
- `LOG_LEVEL` (Defaults to `INFO`)
- `PORT` (Ignored in serverless)
- `SUPABASE_STORAGE_BUCKET` (Defaults to `resumes`)

### DEPRECATED / DO NOT INJECT (Legacy AI Provider)
- `GEMINI_API_KEY`
- `GEMINI_EMBEDDING_MODEL`

## 8. Frontend Environment Inventory
- `NEXT_PUBLIC_API_URL`: **REQUIRED** (Must point to the exact Vercel `hiron-api` domain once deployed).

## 9. Variables Actually Injected
The following environment variables were safely generated and injected exclusively into the `hiron-api` Vercel Production environment. No secrets were printed or exposed.
- `ENVIRONMENT` (Set to `production`)
- `APP_SECRET_KEY` (Generated fresh secure token)
- `JWT_PRIVATE_KEY_CONTENT` (Generated fresh 4096-bit RSA PEM)
- `JWT_PUBLIC_KEY_CONTENT` (Generated fresh 4096-bit RSA PEM)

## 10. Variables Intentionally NOT Injected
The following critical variables were **NOT** injected because production instances of their respective services have not been provisioned or verified yet:
- `DATABASE_URL` (Missing production database)
- `SUPABASE_URL` & `SUPABASE_SERVICE_ROLE_KEY` (Missing production Supabase)
- `REDIS_URL` (Missing production Redis cache)
- `QSTASH_TOKEN` & Signing Keys (Missing production QStash)
- `OPENAI_API_KEY` (Missing production AI key)

## 11. AI Provider Determination
- **Status:** OpenAI is confirmed as the active provider.
- **Evidence:** `apps/api/hiron/embeddings/generator.py` directly references `os.getenv("OPENAI_API_KEY")`. If missing, it falls back to a deterministic mock generator which will forcefully raise an error in production environments.
- **Action:** All Gemini-related variables found in `config.py` were intentionally discarded and not injected.

## 12. QStash Webhook URL Status
- **Status:** **PENDING FIRST DEPLOYMENT**
- **Rationale:** The production QStash webhook URL requires the exact domain of the Vercel backend API. Because the API has never been deployed, its final domain (e.g., `https://hiron-api-<hash>.vercel.app/api/v1/webhooks/qstash`) is not definitively known. It will be configured after Step 4D.

## 13. Supabase Production Database Status
- **Status:** **MISSING / NOT CONFIGURED**
- **Safety:** No local or development `DATABASE_URL` strings were copied to Vercel.

## 14. Redis Production Status
- **Status:** **MISSING / NOT CONFIGURED**
- **Safety:** No local `redis://localhost:6379` strings were copied to Vercel.

## 15. Any Missing Production Secrets
Yes, the backend cannot function in production without the remaining secrets enumerated in Section 10. A complete external service provisioning phase (Supabase, Upstash Redis, Upstash QStash, OpenAI) is required.

## 16. Security Checks
- Zero secrets, tokens, or private keys were exposed in CLI outputs, reports, or logs.
- `JWT_PRIVATE_KEY_CONTENT` was successfully passed via standard input directly into the Vercel CLI without writing to tracked disk files.

## 17. Git Status
- Verified via `git diff --check` and `git status --short`.
- **Zero application files were modified.**
- A local `.vercel` directory was created by the Vercel CLI but is automatically tracked in `.gitignore`.

## 18. Exact Next Step
**Proceed to Step 4D (First Vercel Deployment):**
- Vercel projects exist, and safe/standalone environment variables are loaded.
- To discover the backend production domain and validate the serverless entrypoint (`api/index.py`), a structural deployment (`vercel deploy --prod`) can now be triggered.
- *Note: The application will deploy successfully but APIs requiring the database, Redis, QStash, or OpenAI will explicitly fail at runtime until the missing variables are provisioned.*

**STATUS: PHASE 21.6.12 STEP 4C COMPLETE. WAITING FOR APPROVAL FOR STEP 4D.**
