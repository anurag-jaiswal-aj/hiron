# HIRON MAINTENANCE & LONG-TERM SUPPORT (LTS) MANUAL

## 1. Overview & Long-Term Support Strategy

This operational manual defines the long-term support (LTS), routine maintenance procedures, AI quality monitoring, and system optimization tasks for the Hiron AI recruitment platform post-launch.

---

## 2. Routine Maintenance Tasks

### Automated Maintenance Purging

Post-launch maintenance API endpoints (`/api/v1/maintenance/*`) allow administrators (`org_admin`) to trigger cleanup tasks:

- **Expired Refresh Token Purging**: Remove invalid and expired tokens from `refresh_tokens`.
- **Soft-Deleted Note Purging**: Permanently prune archived candidate notes older than 90 days.
- **In-Memory Cache Flushing**: Clear LRU cache entries via `POST /api/v1/maintenance/cache/purge`.

### PostgreSQL Database Maintenance

Execute automated vacuum analyze and stat updates weekly via standard PostgreSQL cron:

```sql
VACUUM ANALYZE candidates;
VACUUM ANALYZE jobs;
VACUUM ANALYZE scores;
VACUUM ANALYZE audit_logs;
```

---

## 3. AI Quality Monitoring & Prompt Tuning

### AI Quality Diagnostics

Access post-launch quality metrics via `GET /api/v1/maintenance/metrics/quality`:

- **Average Confidence**: Mean AI scoring confidence score across candidates.
- **Score Variance**: Variance of generated fit scores (ensures AI output isn't stagnating or degenerate).
- **High-Confidence Ratio**: Fraction of candidate scores with confidence >= 0.80.

### Prompt Tuning Lifecycle

When adjusting candidate-job fit prompts:

1. Update `DEFAULT_PROMPT_VERSION` in `hiron/scores/engine.py` (e.g. `2.1.0`).
2. Run benchmark evaluation tests:
   ```bash
   uv run pytest apps/api/tests/test_ai_scoring_benchmark.py
   ```
3. Deploy new prompt version to staging and verify fit score distribution before production release.

---

## 4. Scaling & Disaster Recovery Guidelines

### Database Read Replica Offloading

If analytical query loads on `audit_logs` or `ai_usage_logs` exceed 60% CPU:

1. Provision an AWS RDS Read Replica.
2. Direct read-heavy analytics queries (`DashboardService`, `AuditService`) to `DATABASE_READ_REPLICA_URL`.

### Connection Pool Optimization (PgBouncer)

If active database connections exceed 100 concurrent workers:

- Deploy PgBouncer in transaction-pooling mode in front of RDS.
