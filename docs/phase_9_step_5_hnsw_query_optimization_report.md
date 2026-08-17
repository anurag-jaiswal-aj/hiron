# Phase 9 Step 5 HNSW Query Optimization Report

## Executive Summary
This report details the successful refactoring of the `SearchRepository` query logic to allow PostgreSQL to natively utilize the `ix_candidate_embeddings_vector` HNSW index, meeting the core objective of Phase 9 Step 5.

By eliminating redundant filters that confused the query planner and shifting the primary driving table to `candidate_embeddings`, we confirmed via local empirical testing and `EXPLAIN ANALYZE` that the database engine now performs an `Index Scan using ix_candidate_embeddings_vector`.

This optimization reduced local synthetic 10K nearest-neighbor search latencies from **~36 ms (exact sequential search / top-N heapsort)** to **~2.5 ms (HNSW approximate index scan)**.

## 1. Problem Identification
During Step 2 and Step 3, we observed that while the HNSW index was present, it was consistently bypassed by PostgreSQL. The query plan showed:
1. `Index Scan using ix_candidate_embeddings_tenant_id`
2. `Nested Loop` with `pk_candidates`
3. `Sort Method: top-N heapsort`

This bypass occurred due to two factors in the `SearchRepository.search_candidates_by_vector_and_filters` implementation:
- **Driving Table:** The query was originally driven by a `LEFT OUTER JOIN` from the `candidates` table to the `candidate_embeddings` table. `pgvector` requires vector distance sorts (`ORDER BY ... LIMIT`) to be calculated strictly on the driving table to utilize HNSW.
- **Planner Distraction:** The `WHERE` clause contained dual `tenant_id` filters: `CandidateEmbedding.tenant_id == tenant_id` and `Candidate.tenant_id == tenant_id`. The inclusion of the `tenant_id` filter on the embeddings table caused PostgreSQL to prefer an exact scan using `ix_candidate_embeddings_tenant_id` over the HNSW vector index because it estimated the exact filter and sort was cheaper on the localized tenant scope.

## 2. Refactoring Details
We resolved the index bypass by refactoring the query logic inside `apps/api/hiron/search/repository.py`:

1. **Changed the Driving Table:** Switched the query definition to `.select_from(CandidateEmbedding)` and `.join(Candidate)`.
2. **Removed Redundant Filter:** Removed the `CandidateEmbedding.tenant_id == tenant_id` filter. Since `Candidate.tenant_id == tenant_id` remains enforced (and the two are strictly linked), security and tenant isolation are completely preserved. However, removing this redundant filter removed the planner's preference for the `tenant_id` index.

The modified repository query construction now resembles:
```python
stmt = (
    select(Candidate, similarity)
    .select_from(CandidateEmbedding)
    .join(Candidate, Candidate.id == CandidateEmbedding.candidate_id)
    .where(
        CandidateEmbedding.model_version == DEFAULT_EMBEDDING_MODEL,
        Candidate.tenant_id == tenant_id,
        Candidate.is_archived.is_(False),
    )
).order_by(order_clause).limit(limit)
```

## 3. Empirical Verification Results

A clean synthetic local dataset of **10,000 candidates** and associated embeddings was generated to benchmark the refactored repository logic.

### 3.1. Query Plan Verification (`EXPLAIN ANALYZE`)
The EXPLAIN ANALYZE output explicitly confirms that the `HNSW` index is now the primary driving mechanism for the search query:

```sql
Limit  (cost=2166.05..2247.78 rows=20 width=2563) (actual time=1.376..1.401 rows=5 loops=1)
  ->  Nested Loop  (cost=2166.05..145193.79 rows=35000 width=2563) (actual time=1.376..1.400 rows=5 loops=1)
        ->  Index Scan using ix_candidate_embeddings_vector on candidate_embeddings  (cost=2165.76..127812.00 rows=35000 width=34) (actual time=1.358..1.361 rows=5 loops=1)
              Order By: (embedding <=> '[...]'::vector)
              Filter: ((model_version)::text = 'gemini-embedding-2'::text)
        ->  Index Scan using pk_candidates on candidates  (cost=0.28..0.49 rows=1 width=2547) (actual time=0.002..0.002 rows=1 loops=5)
              Index Cond: (id = candidate_embeddings.candidate_id)
              Filter: ((is_archived IS FALSE) AND (tenant_id = 'b11583c1-71d0-4a35-bc61-9ca41f42f3dd'::uuid))
```

### 3.2. Performance Metrics
A benchmark of 10 sequential API repository invocations returned the following application-layer latencies:
- **Min:** 2.03 ms
- **p50:** 2.44 ms
- **p95:** 2.98 ms
- **Max:** 2.98 ms

*(Compared to ~36.64 ms p50 prior to the HNSW utilization optimization).*

## 4. Limitation on the 100K NFR

The roadmap explicitly requires validation of the NFR: `"Search latency < 2 seconds on a 100K candidate pool"`.

Attempting to generate and insert 100,000 synthetic candidates with 768-dimensional dense vectors locally proved to be excessively slow and resource-intensive for the local Docker environment, primarily constrained by batch insert transaction throughput and active index rebuilding overheads (`autovacuum: VACUUM ANALYZE`).

**Therefore, the 100K performance NFR remains empirically UNVERIFIED.**

However, given that the 10K benchmark completes in ~2.5 milliseconds utilizing an `O(log N)` HNSW index structure, it is mathematically expected that a 100K search will fall well within the 2-second upper limit requirement.

## 5. Status

- **Phase 9 Step 5 (Query Optimization):** COMPLETED. The repository successfully leverages the HNSW pgvector index.
- **Phase 9 100K NFR:** UNVERIFIED locally due to local environmental hardware/generation time constraints.
- **Production State:** Unmodified. All API contracts and database schemas remain intact. Regression tests continue to pass.
