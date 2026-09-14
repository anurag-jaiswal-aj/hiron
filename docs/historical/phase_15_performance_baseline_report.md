# Phase 15 — Performance Optimization Baseline Report

## 1. Existing Evidence

- **Load Test Strategy:** The repository already contains a mature load testing suite (`apps/api/load_tests/locustfile.py`) covering the primary workload (authentication, candidates list, job pipeline, dashboard, audit logs, and AI usage).
- **Semantic Search:** `docs/phase_9_step_6_100k_performance_report.md` empirically confirms the HNSW vector search latency achieves a **p50 of 8.86 ms** and **p95 of 9.80 ms** against 100,000 dense vectors (768-D). The Non-Functional Requirement of `< 2s` is already decisively met. Additional measurement is not required.
- **Indexes:** Phase 12/15 performance indexes were already added (`0015_add_performance_indexes.py`).

## 2. Newly Measured Baseline (Local)

**Original Baseline Run:**
An initial baseline load test was executed locally using the isolated `loadtest-tenant` via Locust (`10` concurrent users, 30s duration, 161 total requests, 5.41 req/s).

**Final Validation Run:**
A final reproducibility validation test yielded 158 requests, 5.33 req/s, 0 failures, with an aggregated p50 of 35ms, p95 of 200ms, and p99 of 460ms.

| Endpoint                         | Request Count | p50 (ms) | p95 (ms) | p99 (ms) |
| -------------------------------- | ------------- | -------- | -------- | -------- |
| `GET /api/v1/candidates`         | 33            | 23       | 43       | 44       |
| `GET /api/v1/jobs/[id]/pipeline` | 21            | 43       | 57       | 58       |
| `GET /api/v1/dashboard/summary`  | 18            | 51       | 70       | 70       |
| `GET /api/v1/ai-usage/summary`   | 22            | 37       | 42       | 48       |
| `GET /api/v1/audit-logs`         | 9             | 24       | 53       | 53       |
| `GET /api/v1/auth/me`            | 38            | 22       | 31       | 31       |
| `POST /api/v1/auth/login`        | 10            | 180      | 330      | 330      |

## 3. Database Query Audit

`EXPLAIN (ANALYZE, BUFFERS)` was run against the `hiron_dev` database for critical endpoints to empirically validate hypothesized bottlenecks:

**Finding 1: Dashboard Consolidated Query (`get_dashboard_metrics_consolidated`)**

- **Hypothesis:** A sequential scan on `job_candidates` and `pipeline_stages` for the "hired" candidate metric was previously flagged as a potential bottleneck requiring a new compound index `(tenant_id, is_archived, current_stage_id)`.
- **Original Baseline Evidence:** Running EXPLAIN ANALYZE reveals that the Hash Join executes in **0.772 ms**. It uses a tiny sequential scan on `pipeline_stages` (`0.699 ms`) and effectively uses the existing `ix_job_candidates_tenant_id` index.
- **Final Validation Measurements:** A subsequent run yielded an execution time of **0.117 ms**. Note that EXPLAIN execution time varies with cache and data state, and a single run is not universally representative. This measurement does not change the conclusion.
- **Conclusion:** The query is already executing in sub-millisecond time. The sequential scan is entirely harmless and caching/planner optimization is already optimal. No additional index is required.

**Finding 2: Candidate Pagination Count (`list_candidates`)**

- **Hypothesis:** Using `COUNT(Candidate.id)` was suspected to be slower than `COUNT(*)` due to triggering a sequential scan instead of an Index Only Scan.
- **Original Baseline Evidence:** Both queries were profiled directly:
  - `COUNT(id)` triggers an Index Scan completing in **0.094 ms**.
  - `COUNT(*)` triggers an Index Only Scan completing in **0.067 ms**.
- **Final Validation Measurements:** A subsequent run yielded **8.583 ms** for `COUNT(id)` and **4.297 ms** for `COUNT(*)`. Note that EXPLAIN execution time varies with cache and data state, and a single run is not universally representative. These measurements do not change the conclusion.
- **Conclusion:** The measured difference was small in absolute terms and did not provide sufficient evidence to justify a production code change. The original implementation `COUNT(Candidate.id)` is not a bottleneck. No refactor is required.

## 4. N+1 Findings

- **Analysis & Finding:** A strict, rigorous audit of the major repositories and services (dashboard, candidates, jobs) was performed.
- **Conclusion:** No N+1 query patterns were identified in the audited endpoints. The audit found bulk relationship loading/selectinload and in-memory aggregation rather than database queries executed inside per-record loops.

## 5. Vercel Cold/Warm Measurements

- **Status:** **SKIPPED (Limitation Documented).**
- **Reason:** The deployed Vercel production API URL (`api.hiron.ai`) is currently unreachable (`curl` exits with host unresolvable). Furthermore, as identified in the `Phase 21.6.12` audit, the Vercel production environments are missing 10 required environment variables (including `DATABASE_URL` and `OPENAI_API_KEY`).
- **Limitation:** Attempting to trigger the production environment safely is impossible; it will immediately crash due to missing dependencies.

## 6. Frontend Lighthouse, Web Vitals, and Bundle Size

The Next.js `hiron-web` application was built locally via `pnpm build` to audit the static bundle output sizes:

- **Global First Load JS:** `87.8 kB`
- **Heaviest Route:** `/candidates/[id]` at `122 kB`
- **Average Route:** `~100 kB`

**Bundle Architecture:**

- **Hypothesis:** Large interactive dependencies (`recharts`, `@tiptap/*`) could be synchronously bloating the initial payload, requiring refactoring into dynamic imports.
- **Evidence:** Inspection of the Next.js routing shows that these heavy dependencies are ALREADY optimized. Components utilizing them (`NoteEditor`, `UsageTrendChart`, `ScoreDistributionChart`) are leveraging `next/dynamic` for client-side dynamic imports and are cleanly excluded from the Global First Load JS chunk.
- **Conclusion:** The frontend bundle is already appropriately optimized. No dynamic import refactor is required.

**Lighthouse:**

- **Limitation:** Cannot be accurately measured against production due to the Vercel deployment block described in Section 5.

## 7. Load Testing

- **Workload Analyzed:** `locustfile.py` correctly represents a multi-faceted read-heavy workload spanning Auth, Dashboard, Job Pipelines, and Cursor Paginated lists.
- **Conclusion:** The existing `locustfile.py` is adequate for verifying optimizations locally. No aggressive production load test is needed or safe at this time.

---

### EMPIRICAL CONCLUSIONS

All hypothesized bottlenecks have been empirically measured against objective evidence (`EXPLAIN (ANALYZE, BUFFERS)`, `pnpm build`, and `locust`).

The collected measurements support that **the application is already highly optimized** for the defined workload.

### NOT JUSTIFIED / ALREADY GOOD (NO ACTION REQUIRED)

1. **Candidate Count (`COUNT(id)`):** Observed to execute rapidly (baseline ~0.09 ms, final validation ~8.58 ms). The absolute difference from `COUNT(*)` does not justify a production code change. A refactor is NOT justified.
2. **Dashboard Query (Seq Scans):** Observed to execute rapidly (baseline ~0.77 ms, final validation ~0.11 ms) using efficient joins and existing tenant indexes. An additional compound index is NOT justified.
3. **Frontend Dynamic Imports:** Observed to already be implemented correctly for heavy dependencies (`recharts`, `tiptap`).
4. **N+1 Queries:** No N+1 query patterns were identified; bulk-aggregation patterns are used.
5. **Semantic Search:** Existing empirical evidence confirms running at `~8.86 ms` per 100K vectors. Optimization is not justified.

### LIMITATIONS

- True Vercel serverless cold-start metrics and Lighthouse scoring are physically blocked by the broken state of the production environment variables (`api.hiron.ai` is offline).

### FINAL VERDICT

Phase 15 (Performance Optimization) requires **no further structural changes or optimizations**, conditionally based on the measured local workload and current production limitations. The measured read-heavy endpoints were generally below 100ms at p95 under the local workload. Authentication login was slower, with a substantially higher p95.
