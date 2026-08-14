# Phase 21.6.12: Supabase Migration Compatibility Audit

## 1. First Alembic Revision
The migration chain originates with:
`20260729_0000_000000000001_create_tenants_table.py`

## 2. Complete Revision Chain
The repository contains 18 sequential migration scripts in `apps/api/alembic/versions`, building the entire database schema from scratch. The chain includes base tables, Full-Text Search (FTS) triggers, pgvector indexes, and RLS policy implementations.

## 3. pgvector Extension Requirement
**YES.** The migrations explicitly rely on the `vector` extension.

## 4. Vector Columns Creation
Migration `20260730_0000_000000000007_create_candidate_embeddings_and_job_embeddings_tables.py` creates the vector columns and HNSW indexes.
It executes `CREATE EXTENSION IF NOT EXISTS vector;` directly.

## 5. Expected Vector Dimensions
The application models and migrations strictly expect **1536 dimensions** (`pgvector.sqlalchemy.Vector(1536)`).

## 6. Extensions Schema Handling
The migrations do **not** explicitly create an `extensions` schema. They rely on `CREATE EXTENSION IF NOT EXISTS vector;` without specifying `WITH SCHEMA`. This is completely safe for Supabase, as the extension is typically installed globally or in `public`, and the prior audit confirmed `pgvector` is already enabled in the `public` schema.

## 7. PostgreSQL Features & Supabase Compatibility
**Fully Compatible.** The migrations rely heavily on standard PostgreSQL 15+ features:
- `UUID` (gen_random_uuid)
- `JSONB`
- Native `to_tsvector` and `setweight` for full-text search triggers on `jobs` and `candidates`.
- Row-Level Security (RLS).
Supabase natively supports all of these features without modification.

## 8. AWS/RDS Assumptions
**None.** There are no calls to proprietary AWS PostgreSQL extensions (e.g., `aws_s3`, `aws_lambda`). The migrations are standard open-source PostgreSQL.

## 9. S3 Storage Assumptions
The `resume_files` table (`000000000006_create_resumes_and_resume_files_tables.py`) defines columns named `s3_bucket` and `s3_key`.
- **Finding:** While these names imply AWS S3, they are merely `VARCHAR` columns in the schema. They do not introduce database-level S3 constraints.
- **Compatibility:** Supabase Storage is S3-compatible. The application layer (StorageProvider) seamlessly maps these columns to Supabase Bucket names and file paths.

## 10. Row-Level Security (RLS) Policies
**YES.** Migration `20260811_1200_phase16_rls_001.py` enables `FORCE ROW LEVEL SECURITY` on 17 tenant-scoped tables.
It creates SELECT, INSERT, UPDATE, and DELETE policies using:
`tenant_id = current_setting('app.current_tenant_id', true)::UUID`

## 11. Special Supabase Configuration Requirements
**None Required.** The RLS policies use PostgreSQL's native session variables (`current_setting`). Because the FastAPI application acts as a trusted service (using `SUPABASE_SERVICE_ROLE_KEY` or managing its own DB connections directly via standard AsyncPG) and injects the `app.current_tenant_id` at the start of each transaction, it does not conflict with Supabase's native JWT `auth.uid()` flow. 

## 12. Idempotency & Safety on Empty Database
**Safe.** Alembic manages state via the `alembic_version` table. The migrations are designed to run cleanly on a completely empty database. All custom functions and triggers use `CREATE OR REPLACE` and `IF NOT EXISTS` syntax where appropriate.

## 13. Ordering/Dependency Risks
**None.** The Alembic `down_revision` chain is perfectly linear. There are no branched or conflicting migration heads.

## 14. Production-Only Assumptions
**None.** The migration scripts do not contain environment-specific conditional logic. They build the exact same schema across dev, test, and production.

---

### Conclusion

The Hiron database schema and its entire Alembic migration chain have been strictly audited against Supabase PostgreSQL capabilities. The schema relies exclusively on standard PostgreSQL features (`JSONB`, `UUID`, FTS, RLS, `pgvector`) which are fully supported natively by Supabase. There are no AWS-vendor lock-in triggers, proprietary extensions, or incompatible schema constructs.

**READY FOR MIGRATION**
