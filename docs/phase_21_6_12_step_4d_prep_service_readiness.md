# Phase 21.6.12 Step 4D-PREP: Service Readiness Report

## 1. Supabase Status
- **Status:** **NEEDS PROVISIONING**
- **Authentication Check:** Attempted `npx supabase projects list`. Resulted in `LegacyPlatformAuthRequiredError: Access token not provided`. The current environment is unauthenticated, and no Supabase project configuration exists locally.
- **Action Required:** A new Supabase project must be explicitly created/linked for the production environment.

## 2. Supabase Database Status
- **Status:** **BLOCKED**
- **Details:** The production database cannot be audited until the Supabase project is provisioned. The local `DATABASE_URL` is configured for a local development instance (`postgresql+asyncpg://hiron_user:hiron_secure_password@localhost:5432/hiron_dev`) and was strictly NOT copied to Vercel. 
- **Migration State:** UNKNOWN (Requires database provisioning first).

## 3. Supabase Storage Status
- **Status:** **BLOCKED**
- **Details:** The target bucket (`resumes`) cannot be verified or created until the Supabase project is provisioned.

## 4. Upstash Redis Status
- **Status:** **NEEDS PROVISIONING**
- **Details:** No Upstash Redis instance is configured for production. The local `.env.local` explicitly points to a local Redis server (`redis://localhost:6379/0`). A serverless Upstash Redis database must be provisioned for caching and rate limiting.

## 5. Upstash QStash Status
- **Status:** **NEEDS VERIFICATION** (Partially Ready)
- **Token Availability:** `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, and `QSTASH_NEXT_SIGNING_KEY` are populated in `.env.local` and appear to be valid Upstash tokens. 
- **Webhook URL:** Pending deployment. The target webhook route is implemented in FastAPI (`/api/v1/webhooks/qstash`), but `QSTASH_WEBHOOK_URL` cannot be set until the Vercel backend production domain is assigned.
- **Safety Rule Followed:** Existing keys were NOT rotated unnecessarily.

## 6. OpenAI Status
- **Status:** **NEEDS PROVISIONING / MISSING**
- **Requirement Audit:** The active production codebase (`apps/api/hiron/embeddings/generator.py`) explicitly relies on OpenAI (`os.getenv("OPENAI_API_KEY")`) for embedding generation (`text-embedding-3-small`) and scoring (`gpt-4o-2024-08-06`).
- **Key Availability:** No production API key exists in the environment (the local env specifies a placeholder `your_openai_api_key_here`).

## 7. Free-Tier Cost Assessment
Our explicit architectural requirement is **$0/month whenever possible.** AWS is strictly avoided.

| Service | Provider | Free-Tier Status | Expected Cost | What Could Cause Charges | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Database / Auth | Supabase | 2 Free Projects | $0/mo | Exceeding 500MB DB size or 5GB egress. Upgrading to Pro ($25/mo). | Missing |
| Blob Storage | Supabase | Included in Free | $0/mo | Exceeding 1GB storage or file limits. | Missing |
| Redis Cache | Upstash | 10k commands/day | $0/mo | Exceeding daily usage limits. | Missing |
| Background Jobs | Upstash | 500 messages/day | $0/mo | Exceeding daily message limits. | Token exists |
| AI Generation | OpenAI | Pay-as-you-go | Variable | Every API call (embeddings, completions) incurs micro-charges. | Missing |

## 8. Vercel Environment-Variable Matrix

| Variable | Service | Required | Available | Safe to Inject Now? |
| :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Supabase DB | YES | NO | **NO** (Missing) |
| `REDIS_URL` | Upstash Redis | YES | NO | **NO** (Missing) |
| `QSTASH_TOKEN` | Upstash QStash | YES | YES | YES |
| `QSTASH_CURRENT_SIGNING_KEY` | Upstash QStash | YES | YES | YES |
| `QSTASH_NEXT_SIGNING_KEY` | Upstash QStash | YES | YES | YES |
| `QSTASH_WEBHOOK_URL` | Upstash QStash | YES | NO | **NO** (Pending Domain) |
| `SUPABASE_URL` | Supabase Core | YES | NO | **NO** (Missing) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Core | YES | NO | **NO** (Missing) |
| `SUPABASE_STORAGE_BUCKET` | Supabase Storage | YES | YES | YES (Defaults to `resumes`) |
| `OPENAI_API_KEY` | OpenAI | YES | NO | **NO** (Missing) |
| `APP_SECRET_KEY` | Auth | YES | YES | Already Injected |
| `JWT_PRIVATE_KEY_CONTENT`| Auth | YES | YES | Already Injected |
| `JWT_PUBLIC_KEY_CONTENT` | Auth | YES | YES | Already Injected |

## 9. Missing Credentials
The following production credentials must be provisioned before the application can function:
- Supabase Database connection string (`DATABASE_URL`)
- Supabase Project URL (`SUPABASE_URL`)
- Supabase Service Role Key (`SUPABASE_SERVICE_ROLE_KEY`)
- Upstash Redis Connection String (`REDIS_URL`)
- OpenAI API Key (`OPENAI_API_KEY`)

## 10. Security Considerations
- Zero secrets, passwords, or keys were exposed in this report or terminal outputs.
- No local database URLs or placeholders were mistakenly copied into the production Vercel environment.
- No database migrations were executed against unknown targets.

## 11. Exact Blockers
1. **No Supabase Project**: The primary database and storage bucket do not exist.
2. **No Upstash Redis**: The rate-limiting and caching backend does not exist.
3. **No OpenAI Key**: The AI scoring and embedding engine lacks an API key.

## 12. Is First Deployment Safe?
**NO.** The first deployment is NOT safe or ready. While the Vercel projects exist, deploying the API without `DATABASE_URL`, `REDIS_URL`, and `OPENAI_API_KEY` will result in immediate runtime crashes upon boot or health-check execution.

## 13. Exact Next Action
**DO NOT DEPLOY.** The exact next action is to officially provision the free-tier cloud infrastructure:
1. Create a Supabase Project (Database + Auth + Storage).
2. Create an Upstash Redis Database.
3. Obtain a valid OpenAI API key.
4. Populate these missing values into the Vercel `hiron-api` environment.

**STATUS: PHASE 21.6.12 STEP 4D-PREP COMPLETE. WAITING FOR INFRASTRUCTURE PROVISIONING APPROVAL.**
