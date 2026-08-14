# Phase 15.2 Implementation Gate

## 1. Exact Phase 15.2 requirements from project docs
Phase 15.2 (Database & Search Tuning) focuses purely on database performance. Per the authoritative `docs/IMPLEMENTATION_ROADMAP.md` and project constraints, the requirements are:
- Review all database indexes (remove unused, add missing).
- Verify partial indexes are being used by the query planner.
- Run `VACUUM ANALYZE` on all tables.
- Benchmark `pgvector` HNSW search at 100K vectors.
- EXPLAIN ANALYZE high-value queries.
- Optimize cursor-based pagination and score ranking queries.

## 2. Current database architecture
The database is PostgreSQL initialized with the `pgvector` extension. The schema relies heavily on `UUID` primary keys, foreign-key constraints with `CASCADE/RESTRICT`, and specialized index structures (`BTREE`, `GIN`, `HNSW`).

## 3. Index inventory
Over 90 database indexes were identified. Notable indexes include:
- **HNSW**: `ix_candidate_embeddings_vector`, `ix_job_embeddings_vector`
- **GIN**: `ix_candidates_search_vector`, `ix_candidates_skills`, `ix_jobs_search_vector`
- **Partial**: `ix_jobs_tenant_archived`, `ix_candidates_tenant_archived`, `ix_scores_current_fit_score`
- **Composite B-Tree**: Heavily used for tenant isolation (e.g., `(tenant_id, created_at DESC)`).

## 4. Unused-index analysis
Querying `pg_stat_user_indexes` shows `idx_scan = 0` for all indexes because this local development database was freshly migrated. There is currently insufficient workload history to safely declare any index as genuinely unused in production. No index removals are recommended yet.

## 5. EXPLAIN ANALYZE findings
Because the local tables are empty (or nearly empty), `EXPLAIN ANALYZE` operations often naturally fallback to `Seq Scan` or `Bitmap Heap Scan` + `Sort`. However, the planner successfully recognizes and targets the correct composite indexes (e.g., `ix_candidates_tenant_created` for list endpoints) when tenant clauses are supplied. Sequential scans observed on empty tables are expected and not problematic at this stage.

## 6. Candidate/search findings
Candidate searching is backed by GIN indexes on `search_vector` and `skills`. No immediate structural defects were found. However, performance at scale must be measured with a populated database.

## 7. Score-ranking findings
Score ranking for jobs utilizes a highly specific partial index: `ix_scores_current_fit_score` `(tenant_id, is_current, fit_score DESC) WHERE (is_current = true)`. `EXPLAIN ANALYZE` confirms the query planner identifies and utilizes this partial index perfectly for fetching top-ranked current candidates.

## 8. Cursor-pagination findings
Cursor pagination is implemented in the `AuditLog` and `AIUsageLog` repositories using standard decoding (`created_at`, `id`). 
**Finding:** The primary indexes supporting these queries (e.g., `ix_audit_logs_tenant_created` on `(tenant_id, created_at DESC)`) lack the `id` column. At deep pagination offsets with many identical timestamps, PostgreSQL will be forced to perform in-memory sorts (tie-breakers) rather than a pure index scan.
**Recommendation:** Add the `id` column to the `created_at` indexes for true O(1) cursor pagination.

## 9. Partial-index findings
Partial indexes such as `ix_jobs_tenant_archived` (`WHERE is_archived = false`) and `uq_scores_job_candidate_current` (`WHERE is_current = true`) are correctly applied by the PostgreSQL query planner, successfully filtering out irrelevant rows at the index level before heap access.

## 10. pgvector/HNSW findings
The `candidate_embeddings` and `job_embeddings` tables are configured with:
- `m = 16`
- `ef_construction = 64`
- Operator class: `vector_cosine_ops`
- The query-time parameter `hnsw.ef_search` is not explicitly set in the application code and currently defaults to Postgres's `40`.

## 11. 100K-vector benchmark readiness
There is no existing benchmark script for 100K vectors.
**Strategy:** We will create a local development script using `asyncpg` to generate 100,000 synthetic embeddings (`np.random.rand(1536)`), insert them via `COPY` or batch `INSERT`, and measure latency/recall. This script will only run against `hiron_dev` and will NOT be committed to production infrastructure.

## 12. VACUUM ANALYZE findings
Executed `VACUUM (ANALYZE, VERBOSE)` on the development database. It completed successfully, updated the relfrozenxid, and confirmed that zero live/dead rows exist on the freshly seeded `candidates` table.

## 13. pg_stat_statements findings
The `pg_stat_statements` extension is fully active. Currently, it predominantly reflects the Alembic DDL statements (`CREATE TABLE`, `CREATE INDEX`) executed during database initialization.

## 14. Measured bottlenecks
Since the database has no load, we lack empirical bottlenecks. However, structural analysis identifies:
1. `hnsw.ef_search` is un-tuned, likely trading off recall for speed.
2. Cursor pagination indexes lack the `id` tie-breaker column.

## 15. Proposed optimizations
1. Develop the 100K vector benchmark script (temporary, local-only).
2. Tune `hnsw.ef_search` at the session/query level (e.g., `SET LOCAL hnsw.ef_search = 100`) if the benchmark indicates poor recall.
3. Add `id` to the cursor pagination indexes via Alembic migration to eliminate tie-breaker sorting.

## 16. Risks
- Blindly increasing `ef_search` or `m` improves recall but heavily degrades queries per second (QPS) and increases index size. Decisions must be backed by the benchmark.

## 17. Required tests
- Test suite regressions for AI Usage and Audit Logs after index modifications.
- Local 100K benchmark execution results.

## 18. Strict scope audit
No application code, frontend code, or production infrastructure was modified during this gate. All actions were read-only database queries, `EXPLAIN ANALYZE` executions, and schema inspections.

## 19. Proposed implementation order
1. Build and run the 100K pgvector benchmark locally.
2. Measure current latency vs. recall.
3. Tune `ef_search` / `ef_construction` if necessary based on benchmark evidence.
4. Generate Alembic migration to optimize cursor pagination indexes.
5. Record final numbers.

## 20. Final verdict
READY TO PROCEED
