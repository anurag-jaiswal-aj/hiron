# Phase 21.6.12: Existing Supabase "hiron" Project Audit

## 1. Project Identity
- **Name:** `hiron`
- **Project ID (Ref):** `bpizcvzqehvbzwkuscfe`
- **Region:** `ap-south-1`
- **Status:** `ACTIVE_HEALTHY`
- **Plan:** Free

## 2. Database Status & Size
- **Dashboard Usage:** ~26 MB / 500 MB
- **Context:** In Supabase, ~26 MB of storage is consumed immediately upon project creation by internal system catalogs, the `auth` schema, `storage` schema, `pg_stat_statements`, and default extensions.
- **Finding:** The 26 MB usage does **not** indicate the presence of Hiron application data.

## 3. Existing Schemas & Tables
- **Method:** Using `npx supabase link` and `npx supabase db pull`, the remote schema was pulled to inspect its contents.
- **Findings:** The `public` schema contains **exactly 0 tables**. 
- **Hiron Tables:** `tenants`, `users`, `candidates`, `jobs`, `resumes`, `embeddings`, `batch_score_jobs` **DO NOT EXIST**.

## 4. Migration History
- The `alembic_version` table **DOES NOT EXIST**.
- No Alembic migrations have ever been executed against this database.

## 5. Hiron Data Presence & Preservation Classification
- **Classification:** **C. Supabase internal/default data only.**
- **Preservation Required:** **NO.** The database is an empty, newly provisioned Supabase instance. It is completely safe to run initial Alembic migrations (`alembic upgrade head`).

## 6. pgvector Status
- **Status:** **ENABLED**
- **Details:** The remote schema pull explicitly confirms that `CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "public";` is present on the remote database. pgvector is active and ready for use.

## 7. Storage Bucket Status
- **Intended Bucket (`resumes`):** **MISSING**
- **Existing Buckets Found:** Exactly one bucket exists named `_hiron_storage_poc`.
  - Type: Standard
  - Public: False
  - Created: Aug 12, 2026
- **Action Required:** The `resumes` bucket must be created for the production application to function correctly.

## 8. Credential Availability
- `DATABASE_URL`: **MISSING** (Requires the database password, which is not available in the CLI or local environment. The CLI authenticates via OAuth for schema pulling).
- `SUPABASE_URL`: **AVAILABLE**
- `SUPABASE_SERVICE_ROLE_KEY`: **AVAILABLE**

*(Note: No actual secret values have been printed or written to disk).*

## 9. Risks
- **Deployment Risk:** Because `DATABASE_URL` cannot be constructed without the database password, the Vercel backend cannot be deployed yet.
- **Storage Risk:** Uploading resumes will fail because the `resumes` bucket does not exist.

## 10. Exact Next Step
**Provisioning & Configuration Completion:**
1. Secure the database password to construct the production `DATABASE_URL`.
2. Run `alembic upgrade head` against the remote database to build the Hiron schema.
3. Create the `resumes` bucket in Supabase Storage.
4. Provide the Upstash Redis and OpenAI keys to complete the infrastructure matrix.

**STATUS: SUPABASE AUDIT COMPLETE. WAITING FOR APPROVAL AND MISSING CREDENTIALS.**
