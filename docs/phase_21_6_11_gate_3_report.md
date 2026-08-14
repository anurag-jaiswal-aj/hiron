# Phase 21.6.11 Gate 3: AWS Legacy Infrastructure Cleanup Plan

## Executive Summary
This report outlines the cleanup plan for the obsolete AWS infrastructure following the successful confirmation in Gate 2 that the AWS environment is completely empty and no production data is at risk. The `infra/terraform` directory and `.github/workflows/deploy.yml` are marked for safe removal, but with careful preservation of the non-AWS database migration step (Alembic) present in the deployment workflow. The S3 state bucket `hiron-terraform-state-prod` holds an empty state file and will be intentionally preserved.

## AWS Cleanup Inventory
- **Compute/Networking/DB**: All actual AWS resources have already been deleted or never existed.
- **S3 Bucket `hiron-terraform-state-prod`**: Verified to contain a 181-byte `terraform.tfstate` file, confirming an empty state. **MUST BE PRESERVED**.

## Terraform Cleanup Inventory
- **Obsolete Files**: All files within `infra/terraform/` (`autoscaling.tf`, `backend.tf`, `ecs.tf`, `iam.tf`, `main.tf`, `network.tf`, `outputs.tf`, `rds.tf`, `redis.tf`, `route53.tf`, `variables.tf`).
- **Hidden Functionality**: None. The Terraform files contain only AWS provisioning definitions.

## GitHub Actions Cleanup Inventory
- **Obsolete Workflow**: `.github/workflows/deploy.yml` heavily relies on AWS (`configure-aws-credentials`, `amazon-ecr-login`, `aws ecs update-service`).
- **Hidden Functionality**: Yes. Steps 31-36 perform Python linting and testing (`pytest`, `mypy`). Step 57-61 performs Alembic Database Migrations (`alembic upgrade head`). These steps are crucial for the application lifecycle and must be preserved or migrated to a new workflow.

## Terraform State Findings
- **Status**: The bucket `hiron-terraform-state-prod` exists and contains `production/terraform.tfstate`.
- **Purpose**: It was used as the remote backend for Terraform state storage and DynamoDB locking.
- **Action**: Do not delete this bucket. The state file confirms the infrastructure is empty, providing an audit trail.

## AWS Documentation References
The following documentation contains AWS references that must be updated to reflect the new architecture:
- `README.md` (ECS, RDS, S3 mentions)
- `SECURITY.md` (AWS Secrets Manager)
- `RUNBOOK.md` (AWS ECS update commands, RDS restore commands)
- `IMPLEMENTATION_ROADMAP.md` (AWS ECS provisioning)
- `DATABASE_DESIGN.md` (minor references)

## Vercel Readiness Assessment
- **Architecture Required**: The FastAPI backend requires a `vercel.json` configuration utilizing the `@vercel/python` builder (often exposing the `app` instance via an `api/index.py` or similar). The Next.js frontend uses Vercel's standard deployment natively.
- **Serverless Compatibility**: The application is highly compatible. The shift from Celery to QStash ensures background tasks are handled via stateless webhooks, and the cache layer already falls back gracefully to in-memory or can connect to an external Redis.
- **Status**: Vercel CLI is installed, but the project is unauthenticated and `vercel.json` is currently absent.

## Supabase Readiness Assessment
- **Setup Required**: A Supabase PostgreSQL 16 instance with `pgvector` enabled, and a Supabase Storage bucket replacing the `S3StorageProvider`.
- **Status**: Documentation confirms successful PoCs, but local environment variables and connection strings are currently pointing to local instances.

## Upstash Readiness Assessment
- **Setup Required**: Upstash Redis for ephemeral caching (optional but recommended) and Upstash QStash for background jobs.
- **Status**: QStash is fully integrated and tested.

## Required Environment Variables
The Vercel deployment will require the following configured secrets:
- `DATABASE_URL` (Supabase)
- `OPENAI_API_KEY`
- `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`
- `JWT_PRIVATE_KEY_PATH` / `JWT_PRIVATE_KEY_CONTENT`
- `REDIS_URL` (Upstash)

## Potential Deployment Blockers
- **Database Migrations**: Vercel does not inherently run Alembic migrations on deployment. We must either create a new GitHub Action to run `alembic upgrade head` upon merge to `main`, or use a Vercel build command hook.
- **FastAPI Routing on Vercel**: Vercel serverless functions handle routing differently than a long-running Uvicorn process.

## Proposed Deletion Sequence
1. Extract the linting/testing and Alembic migration steps from `deploy.yml` into a new `ci-cd.yml` workflow.
2. Delete `.github/workflows/deploy.yml`.
3. Delete `infra/terraform/` entirely.

## Exact File Classifications
- **SAFE TO DELETE**: `infra/terraform/*.tf`
- **SHOULD BE MODIFIED INSTEAD OF DELETED**: `.github/workflows/deploy.yml` (Rewrite to remove AWS steps, keeping Alembic).
- **MUST BE PRESERVED**: `hiron-terraform-state-prod` S3 bucket.

## Proposed Replacement/Deployment Sequence
1. Extract Alembic migrations to a GitHub Action.
2. Link Vercel project (`npx vercel link`).
3. Inject environment variables into Vercel.
4. Add `vercel.json` configuration for FastAPI.
5. Deploy to Vercel.

## Rollback Strategy
Since the AWS resources are already non-existent, there is no infrastructure to roll back. If Vercel deployment fails, local development via `uv run uvicorn` and Docker remains completely unaffected.

**STATUS: READY FOR CLEANUP APPROVAL**
