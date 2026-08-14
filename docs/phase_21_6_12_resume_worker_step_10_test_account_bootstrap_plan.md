# Phase 21.6.12 — Resume Worker Step 10: Test Account Bootstrap Plan

## A. Relevant Database Models
- **Tenant**: Defined in `apps/api/hiron/tenants/models.py`. Represents the organization.
- **User**: Defined in `apps/api/hiron/users/models.py`. Represents the human actor within the organization.

## B. Required Records
A minimum complete set requires exactly two records:
1. One `Tenant` record.
2. One `User` record assigned the `org_admin` role.
No additional membership or organization records are required by the Hiron schema.

## C. Required Relationships
- **Foreign Key**: `User.tenant_id` must reference a valid `Tenant.id`. The application mandates that a Tenant is created first.
- **Constraints**: 
  - `User.role` is restricted by a `CheckConstraint` to `('org_admin', 'recruiter', 'hiring_manager')`.
  - `User` requires a unique `email` within the `tenant_id`.
  - `Tenant` requires a unique `slug`.

## D. Existing Password Hashing Mechanism
Hiron uses **Argon2id** for password hashing.
The utility is located at `hiron.core.security.hash_password(password: str) -> str`.
The bootstrap script will import and use this exact application utility to generate the hash, ensuring compatibility with the application's verification logic and preventing manual hashing errors.

## E. Existing JWT / Authentication Mechanism
Authentication is handled via JWT. The application's `get_current_user` dependency (in `hiron/auth/dependencies.py`) expects the JWT to contain:
- `sub`: The UUID of the user.
- `tenantId`: The UUID of the tenant.
By successfully creating the `Tenant` and `User` records with a known password, the standard `POST /api/v1/auth/login` endpoint can be used natively during the E2E test to generate valid JWTs.

## F. Proposed Synthetic Test Account
**Tenant**:
- Name: `Hiron E2E Test Tenant`
- Slug: `e2e-test-tenant`
- Plan: `enterprise`

**User**:
- Email: `e2e-test@hiron.test`
- Name: `Hiron E2E Test User`
- Role: `org_admin`
- Password: A strong 32-character generated secret.

## G. Exact Bootstrap Approach
We will utilize the existing application services (`TenantService` and `UserService`) within a standalone async Python script (`scratch/bootstrap_prod_e2e_tenant.py`).
By injecting a SQLAlchemy `AsyncSession` initialized with the production `DATABASE_URL` environment variable, the script will safely invoke:
1. `TenantService.create_tenant()`
2. `UserService.create_user()`

Using the application services ensures all defaults, constraints, and hashes are handled identically to standard application flow.

## H. Idempotency & Safety Checks
The script will perform the following checks before mutations:
1. Query `TenantRepository.get_by_slug("e2e-test-tenant")`. If it exists, skip tenant creation.
2. Query `UserRepository.get_by_email_and_tenant("e2e-test@hiron.test", tenant.id)`. If it exists, skip user creation.
3. If `e2e-test@hiron.test` exists globally under a *different* tenant, the script will abort immediately to prevent cross-tenant contamination.
4. The script will never update an existing user's password.

## I. Exact Command that WOULD be executed
```bash
# Executed via uv run to ensure the virtual environment and application paths are loaded
export DATABASE_URL="<provided-in-memory-only>"
uv run python scratch/bootstrap_prod_e2e_tenant.py
```
*(The script will read `os.environ["DATABASE_URL"]` securely and will not print it).*

## J. Rollback / Removal Procedure
The schema enforces `ON DELETE CASCADE` for `User.tenant_id`. 
To remove the synthetic E2E account and all related records (including jobs, candidates, and resumes generated during the E2E test):
```sql
DELETE FROM tenants WHERE slug = 'e2e-test-tenant';
```

## K. Risks
1. **Credential Exposure**: The script requires the production `DATABASE_URL`. We mitigate this by passing it strictly via an ephemeral environment variable and ensuring the script performs no `print()` statements containing credentials.
2. **Accidental Production Data Modification**: Mitigated by strict hardcoded synthetic constraints (`e2e-test-tenant` and `e2e-test@hiron.test`) and the use of application service boundaries rather than raw SQL `UPDATE`s.
