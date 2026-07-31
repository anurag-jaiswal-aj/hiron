# HIRON PRODUCTION OPERATIONAL RUNBOOK

## 1. Overview & Architecture

Hiron is a multi-tenant AI recruitment platform deployed on AWS using containerized services (ECS Fargate), Multi-AZ PostgreSQL 16 (RDS), ElastiCache Redis, and S3 for document storage.

- **Primary Domains**: `https://hiron.ai` (App), `https://api.hiron.ai` (Core API)
- **Container Registry**: AWS Elastic Container Registry (ECR)
- **Orchestration**: AWS ECS Fargate (`hiron-production-cluster`)
- **Database**: AWS RDS PostgreSQL 16 Multi-AZ (`hiron_production`)
- **State Store / Queue**: ElastiCache Redis 7 (`hiron-prod-redis`)

---

## 2. Deployment Procedures

### Automated CI/CD Deployment
Deployments to `production` are triggered automatically on push to the `main` or `production` branch via GitHub Actions (`.github/workflows/deploy.yml`).

#### Workflow Steps:
1. Lint, type check (`mypy apps/api`), and run full unit/integration test suite.
2. Build production Docker container images (`Dockerfile.api`, `Dockerfile.ai`, `Dockerfile.web`).
3. Push version-tagged images to Amazon ECR.
4. Execute Alembic zero-downtime database migrations against production RDS:
   ```bash
   uv run alembic upgrade head
   ```
5. Trigger ECS service rolling update:
   ```bash
   aws ecs update-service --cluster hiron-production-cluster --service hiron-api-service --force-new-deployment
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

| Metric / Condition | Threshold | Severity | Notification Target | Action Required |
|---|---|---|---|---|
| API Error Rate | > 1.0% over 5m | Critical (P1) | PagerDuty | Check Datadog error trace logs, inspect Sentry |
| Response Time (p99) | > 5,000ms | Warning (P2) | Slack (`#ops-alerts`) | Inspect DB slow queries, check ECS CPU throttling |
| Database CPU Usage | > 80% over 10m | High (P2) | Slack (`#ops-alerts`) | Scale RDS instance or kill runaway queries |
| AI Service Errors | > 2% over 5m | High (P2) | Slack (`#ops-alerts`) | Check OpenAI API quota, status, and retry queues |
| Disk Storage Free | < 15% | High (P2) | Slack (`#ops-alerts`) | Expand RDS storage or clean old S3 temp files |

### Liveness and Readiness Probes
- **Liveness Probe**: `GET /api/v1/health` (Returns HTTP 200 `{"status": "healthy"}`)
- **Readiness Probe**: `GET /api/v1/health/ready` (Returns HTTP 200 `{"status": "ready"}` or HTTP 503 `{"status": "not_ready"}` if DB is unreachable)

---

## 4. Disaster Recovery & Backup Restoration

### Backup Configuration
- **RDS Backups**: Automated daily snapshots retained for **35 days**, Multi-AZ point-in-time recovery (PITR) enabled.
- **S3 Resume Buckets**: Versioning enabled, cross-region replication (CRR) to `us-west-2`.

### Database Point-in-Time Restore (PITR) Procedure
To restore the production database to a specific timestamp (e.g. before an incident):

```bash
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier hiron-production-db \
    --target-db-instance-identifier hiron-production-db-restored \
    --restore-time 2026-07-30T12:00:00.000Z \
    --db-instance-class db.r6g.large \
    --multi-az \
    --no-publicly-accessible
```

Once verified, update connection strings in AWS Systems Manager Parameter Store or Secrets Manager and restart ECS services.
