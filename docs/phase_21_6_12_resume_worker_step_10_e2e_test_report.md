# Phase 21.6.12 — Resume Worker Step 10: E2E Test Report

## 1. Test Objective
Perform ONE controlled real end-to-end resume-processing test on the production Vercel API -> QStash -> Railway Worker -> Supabase flow.

## 2. Test Fixture Used
A synthesized `test_resume.txt` was created based on the uploaded mock resume image. 

## 3. Authentication & Sign-Up Audit
I inspected the production authentication flow in `apps/api/hiron/auth/router.py`, `apps/api/hiron/tenants/router.py`, and `apps/api/hiron/users/router.py`. 
- There is **no public or self-service signup endpoint**. 
- The `POST /api/v1/tenants` and `POST /api/v1/users` endpoints are strictly protected by `dependencies=[Depends(require_role("org_admin"))]`.
- Creating a new tenant or user requires an already-authenticated user with the `org_admin` role. 
- There are no documented bootstrap scripts in the repository (`scripts/` does not exist, and `docs/RUNBOOK.md` lacks bootstrap instructions).

## Status
As per your strict instructions: *"If no safe self-service test-account creation flow exists, STOP and tell me exactly what account/credential is required. Do not invent one."*

**BLOCKED — SAFE PRODUCTION TEST CREDENTIALS REQUIRED**

**Exactly what is required to unblock:**
To proceed with this production test, you must provide one of the following:
1. The **Email** and **Password** of a pre-existing safe test account in the production database (must have `org_admin` or `recruiter` role).
2. A valid, unexpired **JWT Access Token** for a safe test account.
3. Explicit authorization and a documented SQL/Python bootstrap script to safely seed the very first "root/admin" test tenant and user directly into the production database.
