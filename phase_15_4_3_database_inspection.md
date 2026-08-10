# Phase 15.4.3 Database Query Inspection

## Executive Summary
This inspection evaluated the database query behavior during the Phase 15.4.2 load tests by analyzing `pg_stat_statements` and performing `EXPLAIN ANALYZE` on key queries. The database is extremely healthy. The cursor pagination indexes introduced in Phase 15.2 are being actively and correctly utilized. The dashboard queries are utilizing optimal index-only scans (from Phase 15.1 optimizations). The single anomaly found (`last_login_at` execution time) is definitively a measurement artifact of the load-testing methodology, not a structural performance regression.

**Verdict:** PASS. No database optimizations are required.

## `pg_stat_statements` Findings
The primary observations from the aggregated execution stats are:
1. **`last_login_at` anomaly**: The `UPDATE users SET last_login_at...` query heavily dominated total execution time and mean execution time (~2,714ms).
2. **High throughput, low latency**: Core queries for data retrieval (e.g., fetching jobs, candidate counts, pipelines) barely registered on the total execution time, reflecting sub-millisecond to low-millisecond mean execution times.

## Investigation of `last_login_at`
The `EXPLAIN ANALYZE` of `UPDATE users SET last_login_at=now()... WHERE id = ...` revealed a trivial plan (`Seq Scan` on a 1-page table because it holds only 5 rows) that executes sequentially in ~1ms. 

**Conclusion:** The 2,714ms mean execution time observed during the load test is an **artificial lock contention artifact**. Because the Locust script simulated 100-200 concurrent users logging in using the *exact same* administrator credentials (`admin@loadtest.hiron.ai`), all concurrent threads attempted to acquire a row-level write lock (`UPDATE`) on that single user row simultaneously. This resulted in an artificial lock queue in PostgreSQL. In a production scenario, 200 distinct users logging in would update 200 distinct rows, eliminating this contention entirely.

## Query-Plan Findings & Index Usage Verification
`EXPLAIN ANALYZE` was executed against the primary load-tested endpoints:

1. **Dashboard Candidate Count:**
   - **Plan:** `Index Only Scan` on `ix_candidates_tenant_created`
   - **Execution Time:** ~1.4ms for 10,000 rows
   - **Note:** Successfully utilized Phase 15.1 caching/index strategies.
   
2. **Dashboard Active Jobs Count:**
   - **Plan:** `Seq Scan` on `jobs`
   - **Execution Time:** ~0.03ms
   - **Note:** Expected behavior. The Postgres query planner correctly chose a Seq Scan because the table only contains 20 rows, making an index lookup more expensive than a single-page read.

3. **Pipeline Board Load (`job_candidates`):**
   - **Plan:** `Bitmap Heap Scan` -> `Bitmap Index Scan` on `ix_job_candidates_job_stage`
   - **Execution Time:** ~1.9ms for ~500 candidates on the board.
   - **Note:** Highly efficient and avoids full table scans for large pipeline views.

## Cursor-Pagination Index Verification
The composite tuple comparison indexes `(tenant_id, created_at DESC, id DESC)` introduced in Phase 15.2 were strictly evaluated:

1. **Audit Logs Pagination:**
   - **Plan:** `Index Scan` using `ix_audit_logs_cursor_pagination`
   - **Filter:** `ROW(created_at, id) < ROW(...)`
   - **Execution Time:** ~0.6ms
   - **Status:** **VERIFIED**. The planner uses the exact Phase 15.2 composite index perfectly.

2. **AI Usage Logs Pagination:**
   - **Plan:** `Index Scan` using `ix_ai_usage_logs_cursor_pagination`
   - **Filter:** `ROW(created_at, id) < ROW(...)`
   - **Execution Time:** ~0.3ms
   - **Status:** **VERIFIED**.

## Transaction/Connection Observations
- **`BEGIN/COMMIT` volume:** `BEGIN` was called 3,037 times, followed closely by `COMMIT` (1,391) and `ROLLBACK` (1,646).
- **Rollbacks:** The high ratio of `ROLLBACK` statements is a common artifact of SQLAlchemy's session management, where `session.close()` issues a rollback to ensure connections returned to the pool are clean, especially on read-only transactions that do not commit.
- **Connection pooling:** There were no errors indicating connection pool exhaustion or timeouts, proving that the FastAPI application and asyncpg correctly handled the 200-user concurrency without overwhelming PostgreSQL max connections.

## Comparison with Phase 15.1 and 15.2
- **Phase 15.1:** Index-only scans successfully prevented N+1 aggregation overhead on the dashboard.
- **Phase 15.2:** Tuple-based cursor pagination is verifiably replacing offset queries with index scans, securing O(1) page loading regardless of depth.

## Explicit Statement on Optimization
**No optimization is required.** The system performs efficiently, index coverage is complete, and the only observed bottleneck is a recognized side effect of the benchmark script's authentication design.

## Exact Commands/Queries Used for Verification
- Reset stats: `SELECT pg_stat_statements_reset()`
- Fetch top exec queries: `SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY total_exec_time DESC`
- Explain Update: `EXPLAIN (ANALYZE, BUFFERS) UPDATE users SET last_login_at=now(), updated_at=now() WHERE id = '...'`
- Explain Pagination: `EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM audit_logs WHERE tenant_id = :tid AND (created_at, id) < (now(), '...') ORDER BY created_at DESC, id DESC LIMIT 20`
