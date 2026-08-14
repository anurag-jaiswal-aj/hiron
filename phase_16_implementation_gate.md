# Phase 16 Implementation Gate: Security Hardening

## 1. Phase 16 Objective
**Security audit, penetration testing, and hardening of all surfaces.**

## 2. Exact Roadmap Requirements
Extracted from `docs/IMPLEMENTATION_ROADMAP.md` (Phase 16):

**Backend Tasks:**
- Audit all endpoints for proper authorization checks
- Verify no raw SQL (all queries parameterized via SQLAlchemy)
- Verify no PII in error responses or logs
- Implement request size limits (1 MB JSON, 10 MB file upload)
- Add CORS configuration (allow only `*.hiron.ai` origins)
- Add security headers (HSTS, X-Content-Type-Options, X-Frame-Options, CSP)
- Rate limiting implementation verification on all endpoints
- Verify Argon2id configuration (memory cost, time cost, parallelism)
- Verify JWT RS256 key strength (minimum 2048-bit RSA)
- Verify refresh token rotation and revocation
- Implement input sanitization (prevent XSS in notes, candidate names)

**Frontend Tasks:**
- XSS prevention audit (no `dangerouslySetInnerHTML` without sanitization)
- CSP compliance verification
- Verify auth tokens not stored in localStorage (access token in memory, refresh in httpOnly cookie)
- Verify no sensitive data in browser console or network tab responses

**Database Tasks:**
- RLS policy audit: verify every tenant-scoped table has correct policy
- Verify no `SECURITY DEFINER` functions that bypass RLS
- Verify database user permissions (app user has minimal privileges)

**AI Tasks:**
- Audit prompt injection vectors (user-controlled text in prompts)
- Implement prompt injection detection in AI Service
- Verify no API keys in client-side code or logs

**Infrastructure Tasks:**
- Configure AWS WAF rules, VPC security groups, S3 encryption (AES-256), TLS 1.3 on ALB

**Testing Tasks:**
- OWASP Top 10 checklist verification, SQL injection testing, XSS testing, CORS validation, RLS bypass attempts, rate limiting validation

## 3. Authoritative Source References
- **`docs/IMPLEMENTATION_ROADMAP.md`**: Phase 16 definition.
- **`docs/ENGINEERING_GUIDELINES.md`**: §16 Security Guidelines (Argon2id, JWT TTLs, Secrets Management, Dependency Security).
- **`docs/API_CONTRACT.md`**: §17 API Security Standards (TLS 1.3, Auth mechanisms, Error masking).
- **`docs/DATABASE_DESIGN.md`**: §15 Row-Level Security Considerations.

## 4. Current Architecture Relevant to Phase 16
The current security posture utilizes:
- **Authentication**: JWT access tokens (RS256) and HTTPOnly refresh tokens.
- **Password Hashing**: Argon2id via `passlib`.
- **Database Isolation**: PostgreSQL Row-Level Security (RLS) bound to `app.current_tenant_id` at the middleware level.
- **CORS**: FastAPI `CORSMiddleware` reading from dynamic environment settings.

## 5. Existing Implementation Audit & Gap Analysis
**What is already implemented (Satisfies Phase 16 partially):**
- ✅ **Argon2id**: Configured correctly in `apps/api/hiron/core/security.py`.
- ✅ **JWT Expirations**: `access_token_expire_minutes` (15m) and `refresh_token_expire_days` (7d) strictly enforced in `config.py`.
- ✅ **SQL Injection**: SQLAlchemy Core/ORM parameterized queries are used exclusively. No raw SQL strings found.
- ✅ **CORS**: Registered in `main.py` using `CORSMiddleware`.
- ✅ **Tenant Isolation (RLS)**: Enforced via `app.current_tenant_id` session variables.

**What is missing (Must be changed):**
- ❌ **Security Headers**: No HSTS, X-Content-Type-Options, X-Frame-Options, or CSP headers are applied in FastAPI middleware.
- ❌ **Rate Limiting**: `RateLimitExceededException` exists, but no actual rate limiting interceptor (e.g., `slowapi`) is installed or registered on the routers.
- ❌ **Request Payload Size Limits**: No middleware exists to enforce the 1 MB JSON / 10 MB file upload limit.
- ❌ **XSS Vulnerabilities**: `dangerouslySetInnerHTML` is used in `apps/web/components/notes/CandidateNotesTab.tsx` without a sanitizer like `DOMPurify`.
- ❌ **AI Prompt Injection**: No detection mechanism or sanitization pipeline exists in the AI service layer.

## 6. Proposed Implementation Strategy & Checkpoint Sequence
Phase 16 will be executed via the following checkpoints:

- **Checkpoint 16.1: Backend Middleware Security**
  - Implement and register Security Headers middleware (HSTS, CSP, X-Frame-Options).
  - Implement Request Size Limiting middleware.
  - Integrate Redis-backed Rate Limiting (`slowapi`) across all endpoints.
- **Checkpoint 16.2: Frontend XSS & CSP Compliance**
  - Install `dompurify` in the web client.
  - Refactor `CandidateNotesTab.tsx` to sanitize raw HTML before rendering.
  - Implement strict CSP meta tags or headers for the frontend bundle.
- **Checkpoint 16.3: AI Prompt Injection Protection**
  - Implement sanitization and instruction-defense boundary wrappers in the `ai_usage` and AI scoring services to detect/neutralize prompt injection attempts.
- **Checkpoint 16.4: Infrastructure & Database Audit**
  - Formal RLS policy verification test script.
  - WAF/VPC/S3 security documentation and configuration validation (simulated/mocked if infrastructure is managed externally).

## 7. Exact Files Expected to Change
- `pyproject.toml` (Add rate limiting library e.g. `slowapi`)
- `apps/api/hiron/main.py` (Register new middlewares)
- `apps/api/hiron/core/middleware.py` (Implement headers and size limiters)
- `apps/api/hiron/core/config.py` (Add rate limit settings)
- `apps/web/package.json` (Add `dompurify` dependency)
- `apps/web/components/notes/CandidateNotesTab.tsx` (Apply DOMPurify)
- `apps/api/hiron/ai/service.py` (Add prompt injection filters)

## 8. Files That Must Remain Untouched
- Core business logic schemas and routing paths.
- Phase 15 performance optimizations (cursor pagination, index scans, dynamic imports).
- Existing database migrations (unless fixing an explicitly broken RLS policy).

## 9. Dependencies & Risks
- **Dependencies**: `slowapi` (Backend rate limiting), `dompurify` (Frontend XSS sanitization).
- **Risks**:
  - Rate limiting might block legitimate API traffic if burst thresholds are too low.
  - Request size limits might break edge-case resume uploads if not tuned correctly.
  - Aggressive CSP headers might break legitimate third-party scripts or dynamic inline styles in the frontend.

## 10. Explicit Scope Boundaries
- Do **NOT** rewrite the authentication mechanism (Argon2id and JWTs are already correct).
- Do **NOT** modify frontend visual designs or layouts.
- Do **NOT** change the database schema aside from permission/RLS tightening if necessary.

## 11. Final Readiness Verdict
**PASS**. The implementation gate is complete. The repository is ready to begin Phase 16 execution starting with Checkpoint 16.1.
