# Phase 16.4 Implementation Gate

## 1. Phase 16.4 Objective
Perform read-only security audits and finalize the hardening of database isolation (Row-Level Security) and AWS infrastructure boundaries.

## 1.1 Explicit Security Constraints
1. Tenant identity MUST come from an authenticated/trusted server-side source. Never accept a client-supplied tenant_id header, query parameter, request body field, or arbitrary cookie as authoritative tenant identity.
2. `app.current_tenant_id` MUST be scoped to the current database transaction or connection lifecycle and MUST NOT leak between requests, tenants, or pooled connections.
3. RLS MUST remain effective even if application-level tenant filtering is accidentally omitted.
4. The implementation MUST explicitly test connection-pool reuse and verify that tenant context from Tenant A cannot survive into Tenant B's request.
5. `FORCE ROW LEVEL SECURITY` must only be used where compatible with the actual database role architecture. Do not claim FORCE RLS provides protection if the application role can bypass it through ownership or elevated privileges.
6. Migration/schema changes must be reversible and must preserve existing data.
7. AWS resources must be integrated with the existing Terraform architecture. Do not create duplicate VPC, ALB, ECS, S3, or networking resources.

## 2. Exact Roadmap Requirements
From `docs/IMPLEMENTATION_ROADMAP.md` (Phase 16):
**Database Tasks**:
- RLS policy audit: verify every tenant-scoped table has correct policy
- Verify no `SECURITY DEFINER` functions that bypass RLS
- Verify database user permissions (app user has minimal privileges)

**Infrastructure Tasks**:
- Configure AWS WAF rules
- Enable VPC security groups (DB not publicly accessible)
- Enable S3 bucket encryption (AES-256)
- Configure TLS 1.3 on ALB

**Testing Tasks**:
- Security: RLS bypass attempts

## 3. Authoritative Source References
- `docs/DATABASE_DESIGN.md` §15.2: Application must set `app.current_tenant_id`. Every tenant-scoped table must have an RLS policy checking `tenant_id = current_setting('app.current_tenant_id')::UUID`.
- `docs/ENGINEERING_GUIDELINES.md` §1.2: Explicit over Implicit.
- `docs/IMPLEMENTATION_ROADMAP.md` Phase 1: RLS must be enforced.

## 4. Current Database Architecture
Hiron uses a **shared database, shared schema** architecture. Isolation between tenants is solely dependent on `tenant_id` filtering enforced by PostgreSQL Row-Level Security (RLS).

## 5. RLS Audit Findings
- **Missing Policies**: NO RLS policies have been created in the Alembic migrations. All 16 tenant-scoped tables (`users`, `refresh_tokens`, `jobs`, `candidates`, etc.) lack both `ENABLE ROW LEVEL SECURITY` and `CREATE POLICY`.
- **Missing Middleware**: The application codebase (`FastAPI`) completely lacks the `TenantIsolationMiddleware` required to execute `SET app.current_tenant_id` at the start of database sessions.
- **Result**: Tenant isolation is currently **NOT ENFORCED** at the database level.

## 6. SECURITY DEFINER Findings
- **None found**: A global repository search confirms there are zero `SECURITY DEFINER` functions in the database migrations or codebase.

## 7. Database Privilege Findings
- **Over-privileged User**: The API connects using `hiron_user` configured via `config.py`. There are no dedicated database roles for `app_user`, `migration_user`, and `super_admin`.
- **Impact**: The application user likely operates as the table owner. In PostgreSQL, table owners bypass RLS unless `FORCE ROW LEVEL SECURITY` is applied. This means even if policies existed, the current app user would bypass them.

## 8. Infrastructure Audit Findings (Terraform)
- **VPC Security Groups**: ✅ Configured in `infra/terraform/main.tf`. The ECS SG strictly allows traffic only from the ALB.
- **S3 Encryption**: ✅ Configured. `aws_s3_bucket_server_side_encryption_configuration` correctly sets `AES256`. Public access is blocked.
- **AWS WAF**: ❌ Missing. No `aws_wafv2_web_acl` is defined in Terraform.
- **ALB TLS 1.3**: ❌ Missing. The `aws_lb` and `aws_lb_listener` resources themselves are entirely missing from the checked-in Terraform configuration.

## 9. What is Verified
- All Terraform checks (S3, VPC) were verified against the checked-in `infra/terraform/main.tf`.
- Database checks were verified by analyzing the complete set of checked-in Alembic migrations and application source code.

## 10. What Cannot be Verified
- Live AWS configuration cannot be verified locally without AWS credentials.
- Live database user privileges inside the Docker container cannot be queried because the local database is currently offline/unavailable (Connection Refused).

## 11. Identified Gaps
1. **Critical Data Leakage Risk**: RLS is entirely absent from both the database (no policies) and the application (no tenant context injection).
2. **Missing AWS Resources**: WAF and ALB configurations are completely missing from Terraform.
3. **Privilege Escalation**: Application uses a single database user for migrations and runtime queries, bypassing intended separation of duties.

## 12. Proposed Implementation Strategy
1. **Application RLS Context**: Create `TenantIsolationMiddleware` or a DB dependency interceptor in FastAPI to inject `SET app.current_tenant_id` for every authenticated request.
2. **Database Policies**: Create a new Alembic migration to `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, and `CREATE POLICY` for all 16 tenant-scoped tables.
3. **Database Roles**: Create a setup script or migration that properly scaffolds `hiron_app` (read/write, non-owner) and `hiron_migrator` (owner) roles.
4. **Terraform**: Append `aws_lb`, `aws_lb_listener` (TLS 1.3), and `aws_wafv2_web_acl` to `main.tf`.

## 13. Exact Files Expected to Change
- `apps/api/hiron/security/middleware.py`: Add `TenantIsolationMiddleware`.
- `apps/api/hiron/main.py`: Register the middleware.
- `apps/api/hiron/core/database.py`: Configure session hooks for `set_config`.
- `apps/api/alembic/versions/*_enable_rls.py` (NEW): Apply RLS policies.
- `apps/api/tests/test_rls.py` (NEW): Cross-tenant access tests.
- `infra/terraform/main.tf`: Add WAF and ALB definitions.

## 14. Files That Must Remain Untouched
- Frontend files (`apps/web/*`).
- Phase 16.3 AI Boundary definitions.
- Existing migrations (do not rewrite history; add a new migration).

## 15. Testing Strategy
- Write an integration test that creates two tenants, inserts data for Tenant A, and attempts to query it using Tenant B's JWT context. The test MUST assert that 0 rows are returned.
- Run `terraform validate` to ensure the new AWS infrastructure syntax is correct.

## 16. Risks
- Implementing RLS late may break existing endpoints that query data across tenants (e.g., admin dashboards). We must ensure a bypass mechanism exists exclusively for system-level operations.

## 17. Explicit Scope Boundaries
- Do not deploy to AWS.
- Do not create mock endpoints.
- Do not change UI logic.

## 18. Final Readiness Verdict
**VERDICT: FAIL**

Phase 16.4 cannot be marked complete. Major foundational security requirements from Phase 1 (RLS isolation) were discovered to be entirely missing. The infrastructure is missing WAF and ALB configurations. Phase 16.4 implementation is required to rectify these gaps.
