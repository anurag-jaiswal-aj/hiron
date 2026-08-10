# Phase 15.4 Implementation Gate

## 1. Objective
Establish a reproducible load testing and benchmarking framework to validate that the performance optimizations implemented in Phases 15.1, 15.2, and 15.3 successfully meet the system's non-functional requirements under concurrent load.

## 2. Exact Phase 15.4 Requirements
*(Sourced strictly from `docs/IMPLEMENTATION_ROADMAP.md`)*
**Testing Tasks:**
- Performance: API response time benchmarks (all endpoints < target per API Contract)
- Performance: semantic search at 100K candidates < 2s
- Performance: dashboard load < 500ms
- Performance: Kanban board load with 200 candidates < 1s
- Load testing: simulate 100 concurrent users

**Acceptance Criteria (Performance relevant):**
- Performance meets the NFRs from the Architecture Document.

## 3. Existing Benchmark Infrastructure
An audit of the repository reveals **no dedicated load-testing framework** is currently installed.
- **Python**: Uses `pytest` for unit/integration tests, but lacks `locust` or `pytest-benchmark`.
- **Node**: Uses `playwright` for E2E tests, but lacks `k6`, `artillery`, or `autocannon`.
- **Infrastructure**: `docker-compose.yml` exists and successfully configures `pg_stat_statements` on PostgreSQL and a Redis instance, meaning production-like resource limits and monitoring are theoretically possible locally.

## 4. Existing Performance Baselines
*(These are previously measured metrics, not NFRs)*
- **Phase 15.1**: N+1 and caching optimizations were merged (O(N) -> O(1) query reduction).
- **Phase 15.2**: Cursor pagination tuple comparison `tuple_()` indexes were added. A pgvector 100K benchmark script ran sequentially.
- **Phase 15.3**: Frontend dynamic imports reduced the Dashboard by `102 kB` and Candidate Detail by `144 kB`.

## 5. Official Performance NFRs
*(Sourced strictly from `docs/API_CONTRACT.md` and Roadmap)*
- Semantic search on 100K pool: `< 2000ms`
- Dashboard load: `< 500ms`
- Kanban board load (200 candidates): `< 1000ms`
- Standard endpoints (e.g., Auth, GETs): Typically `< 50ms` to `< 150ms`.

## 6. API Workload Inventory
The following endpoints reflect the actual FastAPI implementations mapped to the performance tasks:
1. `GET /api/v1/auth/me`
   - **Auth**: JWT required.
   - **Purpose**: Baseline cached read.
2. `GET /api/v1/dashboard/summary`
   - **Auth**: JWT required, `org_admin` role.
   - **Purpose**: Heavy aggregate dashboard queries.
3. `GET /api/v1/candidates`
   - **Auth**: JWT required.
   - **Parameters**: `cursor`, `limit` (cursor pagination).
   - **Purpose**: Verifies cursor pagination performance.
4. `GET /api/v1/jobs/{job_id}/pipeline`
   - **Auth**: JWT required.
   - **Purpose**: Validates Kanban board data retrieval.
5. `GET /api/v1/audit/audit-logs` & `GET /api/v1/ai-usage/summary`
   - **Auth**: JWT required, `org_admin` role.
   - **Purpose**: Verifies time-series performance.

## 7. Frontend Performance Test Inventory
- `apps/web/e2e/` contains comprehensive Playwright tests.
- **Lighthouse is ENVIRONMENT BLOCKED**: Lighthouse requires a fully populated, authenticated browser session rendering the Next.js production build. The local Playwright mock auth infrastructure fails against real API calls without a seeded database, preventing valid Lighthouse profiling.

## 8. Current Environment
- **Local Env**: Mac OSX, sufficient CPU/Memory for local concurrency testing.
- **Docker**: Full environment available (`docker-compose.yml` supports Postgres, Redis, API, AI, Celery, Next.js).
- **Backend Load Testing**: Feasible by directly targeting the FastAPI container over HTTP with authenticated JWTs.

## 9. Dataset Readiness & Representative Design
Currently, only a minimal `seed.py` exists. A representative dataset must be generated focusing on a realistic relationship distribution for a single mid-sized organization:
- **1 Tenant** (`loadtest_tenant`)
- **5 Users** (1 admin, 4 recruiters)
- **20 Jobs** (representing active recruitment)
- **10,000 Candidates** (~500 per job to simulate heavy pipeline volume)
- **50,000 Pipeline Stage Histories** (5 movements per candidate)
- **50,000 Scores** (5 AI evaluation records per candidate)
- **10,000 AI Usage Logs & Audit Logs** (historical system activity)

*(Note: We will test 10K candidates rather than 100K for the general load test to respect local Docker memory limits, as 100K was exclusively mandated for the isolated semantic search benchmark).*

## 10. Proposed Load-Test Methodology
1. **Tool**: Propose installing **Locust** (`pip install locust`) in `apps/api/requirements-dev.txt`.
2. **Setup**: Boot `docker-compose up -d`.
3. **Seeding**: Run `apps/api/load_tests/seed_loadtest.py` to provision the `loadtest_tenant`.
4. **Execution**: Run headless Locust targeting `http://localhost:8000`.
5. **Disclaimer**: Local docker-compose results are not production capacity guarantees; they validate query efficiency, cache hit rates, and regression absence under artificial local constraints.

## 11. Concurrency Matrix
- **Warm-up**: 1 user, 30 seconds (primes caches and connections).
- **Baseline**: 10 users, 2 minutes.
- **Moderate**: 50 users, 3 minutes.
- **Peak**: 100 users, 3 minutes (Roadmap requirement).
- **Stress (Optional)**: 200 users, 3 minutes (to observe breaking points).

## 12. Proposed Benchmark Thresholds
*(These are proposed local targets to measure success, NOT official NFRs)*
- Zero OOM (Out of Memory) kills.
- Error rate < 0.1%.
- Local p95 dashboard load < 500ms (verifying the NFR holds even locally).
- Local p95 candidate list < 200ms.

## 13. Risks
- Running Locust locally alongside Docker can cause CPU contention, artificially inflating latency measurements compared to a real cloud deployment.

## 14. Environment Blockers
- **Lighthouse**: **ENVIRONMENT BLOCKED**. We cannot perform valid frontend Lighthouse analysis locally without a guaranteed seeded session. We will NOT substitute bundle sizes for Lighthouse metrics.

## 15. Exact Files Expected to Change
- `apps/api/requirements-dev.txt` (or pyproject.toml equivalents if used)
- `apps/api/load_tests/locustfile.py` (New)
- `apps/api/load_tests/seed_loadtest.py` (New)
- `phase_15_4_load_test_results.md` (New)

## 16. Proposed Implementation Checkpoints
- **15.4.1**: Install Locust & Create Seed Script
- **15.4.2**: Execute Load Test & Measure API Metrics
- **15.4.3**: Database Query Inspection (`pg_stat_statements`)

## 17. Targeted Cleanup Strategy
We will **NOT** use `docker-compose down -v`. Instead, the `seed_loadtest.py` script will create a dedicated `loadtest_tenant`. Post-test cleanup will consist of a targeted deletion of the `loadtest_tenant`, relying on `ON DELETE CASCADE` to flush the 10,000 candidates and associated logs without destroying the developer's normal `hiron_dev` data.

## 18. Strict Scope Boundaries
- Do **NOT** modify any application code (FastAPI routes or Next.js components).
- Do **NOT** modify database schemas or migrations.
- Do **NOT** modify production configuration.
- Do **NOT** execute the load test during this gate step.
- Do **NOT** install Locust yet.

## 19. Readiness Decision
**READY TO PROCEED**
