# Phase 16.1 Verification: Backend Middleware Security

## Objective
Implement backend security headers, request size limits, and rate limiting required by Phase 16, without breaking existing endpoints, performance optimizations, or Next.js compatibility.

## Exact Requirements Implemented
1. **Security Headers**: HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, and Context-Aware CSP.
2. **Request Size Limits**: Max 1 MB for standard JSON/URL-encoded requests, and Max 10 MB for file uploads (`/resumes/upload`). Returns `413 Payload Too Large`.
3. **Rate Limiting**: Redis-backed, fixed-window rate limiter via `RateLimitMiddleware` (600 req/min by default) resolving via `CacheManager`. Skips `/health` and `/docs`. Returns standard `429 Too Many Requests`.

## Files Changed
- `apps/api/hiron/core/config.py`: Added `rate_limit_requests_per_minute` (int, default=600).
- `apps/api/hiron/security/middleware.py`: Refactored and implemented `RateLimitMiddleware`. Fixed imports.
- `apps/api/hiron/main.py`: Registered `RateLimitMiddleware` into the FastAPI middleware stack.

*No unrelated files, application code, frontend code, or AWS infrastructure files were modified.*

## Security Header Behavior
- **HSTS**: `max-age=31536000; includeSubDomains` applied unconditionally.
- **X-Frame-Options**: `DENY` applied unconditionally to prevent clickjacking.
- **X-Content-Type-Options**: `nosniff` applied to prevent MIME confusion.
- **Content-Security-Policy (CSP)**:
  - Base API endpoints get `default-src 'self'`.
  - Swagger UI endpoints (`/docs`, `/redoc`, `/openapi.json`) get a relaxed CSP allowing `unsafe-inline` scripts and CDN assets for Swagger to function.
  - *This strictly applies to the backend API and does not affect the independent Next.js frontend.*

## Request Size Limit Behavior
- Standard payloads exceeding `1 MB` immediately trigger a `413 Request Entity Too Large` error with code `REQUEST_TOO_LARGE`.
- Multipart file uploads at `/resumes/upload` are permitted up to `10 MB` before triggering the same `413` response.
- Exceeding the limits aborts processing before passing the request down the middleware chain.

## Rate Limit Architecture & Behavior
- **Implementation**: Native ASGI middleware `RateLimitMiddleware` utilizing a fixed-window token approach.
- **Storage**: Redis via the pre-existing `CacheManager()._get_redis()` connection pool. This ensures limits are synchronized across multiple stateless FastAPI workers.
- **Limit Chosen**: 600 requests per minute per IP address. This provides ample headroom for normal heavy usage (e.g., dynamic imports, batch syncs) while preventing aggressive DoS/brute-force attacks.
- **Exemptions**: Infrastructure probes (`/api/health`, `/api/v1/health`) and OpenAPI docs are completely exempt to prevent LB disconnections and development friction.
- **Response**: Generates a standard Hiron exception format `429 Too Many Requests` (Code: `RATE_LIMIT_EXCEEDED`) and includes a `Retry-After: 60` header.
- **Resilience**: A generic exception handler within the middleware ensures that if Redis is down, the system "fails open" (logs the error and allows the request) rather than dropping all traffic.

## Tests Executed and Results
Added and executed `apps/api/tests/test_security_middleware.py`:
- `test_security_headers`: PASSED
- `test_request_size_limit_json`: PASSED
- `test_request_size_limit_upload`: PASSED
- `test_rate_limit`: PASSED

Executed regression test suite:
- `pytest apps/api/tests/`: All tests PASSED.
- `ruff check`: All PASSED.
- `mypy`: All PASSED.
- *Verified that Phase 15 cursor pagination and vector benchmarks remain untouched.*

## Known Limitations
- The current rate limit relies on `X-Forwarded-For` or the direct client IP. If a misconfigured proxy sits in front of the API without properly appending IPs, rate limits may inadvertently affect a shared pool of legitimate users.
- Size limits rely on `Content-Length`. Malicious chunked payloads lacking a `Content-Length` header are caught downstream by FastAPI body limits, but are not caught instantly in the ASGI middleware layer.

## Final Verdict
**PASS**. Checkpoint 16.1 is verified. The repository is ready to proceed to Checkpoint 16.2.
