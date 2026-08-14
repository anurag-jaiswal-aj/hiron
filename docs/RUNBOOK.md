# HIRON PRODUCTION OPERATIONAL RUNBOOK

## 1. Overview & Architecture

Hiron is a multi-tenant AI recruitment platform transitioning to a serverless architecture (Vercel, Supabase PostgreSQL, Upstash Redis/QStash). The legacy AWS production infrastructure has been decommissioned.

- **Primary Domains**: `https://hiron.ai` (App), `https://api.hiron.ai` (Core API)
- **Container Registry**: Vercel (Native)
- **Orchestration**: Vercel Serverless Functions
- **Database**: Supabase PostgreSQL 16 Multi-AZ (`hiron_production`)
- **State Store / Queue**: Upstash Redis / QStash

---

## 2. Deployment Procedures

### Automated CI/CD Deployment

Deployments to `production` are triggered automatically on push to the `main` or `production` branch via GitHub Actions (`.github/workflows/deploy.yml`).

#### Workflow Steps:

1. Lint, type check (`mypy apps/api`), and run full unit/integration test suite.
2. Build and deploy via Vercel GitHub integration.
3. Execute Alembic zero-downtime database migrations against production Supabase:
   ```bash
   uv run alembic upgrade head
   ```

### Zero-Downtime Database Migration Guidelines

- Never drop a column or table in a single release step. Use expanding and contracting migration phases.
- Column additions must be non-nullable only if default values are provided.
- Execute heavy index creation concurrently via PostgreSQL:
  ```sql
  CREATE INDEX CONCURRENTLY ix_candidates_tenant_created ON candidates (tenant_id, created_at DESC);
  ```

---

## 3. Incident Management & Alert Escalation

### Alert Thresholds & Notification Channels

| Metric / Condition  | Threshold      | Severity      | Notification Target   | Action Required                                   |
| ------------------- | -------------- | ------------- | --------------------- | ------------------------------------------------- |
| API Error Rate      | > 1.0% over 5m | Critical (P1) | PagerDuty             | Check Datadog error trace logs, inspect Sentry    |
| Response Time (p99) | > 5,000ms      | Warning (P2)  | Slack (`#ops-alerts`) | Inspect DB slow queries, check Vercel function limits |
| Database CPU Usage  | > 80% over 10m | High (P2)     | Slack (`#ops-alerts`) | Scale Supabase instance or kill runaway queries        |
| AI Service Errors   | > 2% over 5m   | High (P2)     | Slack (`#ops-alerts`) | Check OpenAI API quota, status, and retry queues  |
| Disk Storage Free   | < 15%          | High (P2)     | Slack (`#ops-alerts`) | Expand Supabase storage or clean old temp files     |

### Liveness and Readiness Probes

- **Liveness Probe**: `GET /api/v1/health` (Returns HTTP 200 `{"status": "healthy"}`)
- **Readiness Probe**: `GET /api/v1/health/ready` (Returns HTTP 200 `{"status": "ready"}` or HTTP 503 `{"status": "not_ready"}` if DB is unreachable)

---

## 4. Disaster Recovery & Backup Restoration

### Backup Configuration

- **Supabase Backups**: Automated daily snapshots retained, Point-in-Time Recovery (PITR) enabled.
- **Supabase Storage Buckets**: Versioning enabled.

### Database Point-in-Time Restore (PITR) Procedure

To restore the production database to a specific timestamp (e.g. before an incident), use the Supabase Dashboard PITR controls.

Once verified, update connection strings in Vercel Environment Variables.
