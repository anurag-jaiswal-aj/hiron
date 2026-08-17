# Phase 9 Step 6 — 100K HNSW Performance Validation Report

## 1. Objective
Empirically validate the Phase 9 Non-Functional Requirement (NFR): "Search completes in < 2 seconds on 100K pool." This validation must test the optimized semantic search query executing against a PostgreSQL database containing 100,000 dense 768-dimensional candidate embeddings, without relying on extrapolation from smaller datasets.

## 2. Dataset
A clean synthetic local dataset was generated containing:
- 1 Isolated Benchmark Tenant
- 100,000 Candidate records
- 100,000 CandidateEmbedding records
- Dimensions: 768 per vector
- Model: `gemini-embedding-2`

## 3. Data Loading Method
To avoid ORM and application layer insertion bottlenecks, the data was generated in-memory via Python, written locally to CSV files, and bulk-inserted into the PostgreSQL database using the `\copy` command via `psql`. This allowed all 100,000 vectors to be generated and indexed securely within ~20 minutes locally.

## 4. Tenant Isolation Validation
Prior to the 100K dataset test, a strict cross-tenant contamination test was performed on two tenants (Tenant A and Tenant B, 100 candidates each). Despite Tenant B's vectors being artificially designed to be closer to the query vector, the search performed as Tenant A returned strictly 0 records from Tenant B and successfully respected limit constraints, mathematically validating that driving the query from `CandidateEmbedding` maintains proper data boundary integrity.

## 5. EXPLAIN ANALYZE
The query planner execution plan for the unfiltered 100K candidate search confirmed optimal usage of indices across the `INNER JOIN` configuration.

```sql
Limit  (cost=1380.51..1433.65 rows=20 width=1595) (actual time=1.096..1.199 rows=20 loops=1)
  ->  Nested Loop  (cost=1380.51..267087.84 rows=100000 width=1595) (actual time=1.096..1.198 rows=20 loops=1)
        ->  Index Scan using ix_candidate_embeddings_vector on candidate_embeddings  (cost=1380.09..208660.00 rows=100000 width=34) (actual time=1.081..1.088 rows=20 loops=1)
              Order By: (embedding <=> '[...]'::vector)
              Filter: ((model_version)::text = 'gemini-embedding-2'::text)
        ->  Index Scan using pk_candidates on candidates  (cost=0.42..0.58 rows=1 width=1579) (actual time=0.001..0.001 rows=1 loops=20)
              Index Cond: (id = candidate_embeddings.candidate_id)
              Filter: ((is_archived IS FALSE) AND (tenant_id = '...'::uuid))
```

## 6. HNSW Utilization
The `EXPLAIN ANALYZE` unequivocally demonstrates an `Index Scan using ix_candidate_embeddings_vector`. The planner correctly leveraged the Approximate Nearest Neighbor (HNSW) index rather than falling back to sequential scans or heapsorts on the 100,000 vector scale.

## 7. 100K Benchmark Results

The benchmark executed 10 warm search queries dynamically generating random 768-D query vectors per run:

| Metric | Result |
|---|---:|
| Candidates | 100,000 |
| Runs | 10 |
| Min | 7.27 ms |
| p50 | 8.86 ms |
| p95 | 9.80 ms |
| Max | 9.80 ms |
| Target | <2000 ms |
| Result count | 20 |

## 8. Filtered Search Benchmark
A secondary benchmark simulating real-world hybrid metadata filtering (e.g., `experience_min=3`, `location="New York"`) was executed.

**Performance summary:**
- **p50 Latency:** 6.11 ms
- **Max Latency:** 7.35 ms

PostgreSQL maintained usage of the `ix_candidate_embeddings_vector` HNSW index for ordering, relying on the `Nested Loop` with the `pk_candidates` index scan filtering the required metadata constraints locally on matched subsets.

## 9. Regression Tests
Automated test coverage (`pytest` on `test_search_api.py`, `test_search_repository.py`, and `test_search_service.py`) was executed to guarantee that the query refactoring did not break logical contracts.
**Result:** 8/8 tests passed successfully.

## 10. Cleanup Verification
A script was executed to issue `DELETE CASCADE` on all synthetic benchmark tenants, successfully clearing all 100,000 candidate and embedding rows. Row counts for residual benchmark vectors were verified to be strictly 0, maintaining complete local database hygiene.

## 11. Performance Conclusion
The Phase 9 100K Semantic Search performance NFR of `< 2 seconds` was **empirically demonstrated and decisively met**. With a p50 latency of `~8.86 ms` on 100,000 documents, the current HNSW query structure provides headroom that vastly exceeds the baseline threshold requirement.

## 12. Remaining Risks
None identified related to performance or logical isolation at the 100K tier. Operational behavior under heavy concurrent write loads while rebuilding vectors remains subject to generic PostgreSQL VACUUM lifecycle maintenance.

## 13. Acceptance Criteria
- [x] Query driven from CandidateEmbedding
- [x] EXPLAIN ANALYZE shows `Index Scan using ix_candidate_embeddings_vector`
- [x] Tenant isolation strictness verified
- [x] Performance < 2000ms verified against 100,000 records
- [x] Regression tests passing
- [x] No modifications to production environment

## 14. Final Status
PHASE 9 STEP 6: PASS
