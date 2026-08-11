# Phase 16.4 ECS Implementation Gate (Final Revision)

## 1. SELECTED EGRESS ARCHITECTURE
**Status: BLOCKER (To be implemented)**
The existing architecture contains private subnets (`aws_subnet.private_a` and `aws_subnet.private_b`) with absolutely no outbound connectivity.

**Option A: NAT Gateway** (Recommended)
- **Security:** Hides private IPs from the internet.
- **Cost:** ~$32/month per NAT Gateway.
- **Complexity:** Simple; one NAT Gateway provides universal outbound access.
- **Application Compatibility:** Highly appropriate. As an AI Recruitment platform, the application strictly requires outbound internet access to call external LLM providers (e.g., OpenAI/Anthropic APIs) using the `OPENAI_API_KEY`.
- **Selected Architecture:** We will implement **Option A** (NAT Gateway in `public_a` with a route table mapping private subnets to it) because VPC Endpoints (Option B) only provide access to AWS services (ECR, CloudWatch, S3) and would effectively break the application's core AI integrations by blocking internet-bound traffic.

## 2. SECRETS MANAGER DESIGN
**Secret State Claim:**
Secret values are excluded from Terraform configuration and state; secret metadata/ARN references may legitimately exist in state.

- **Secret Values:** The actual passwords and API keys will NEVER be placed in `.tf` files, Terraform variables, or the Terraform state file.
- **Secret Metadata:** Terraform will create the `aws_secretsmanager_secret` (the container/ARN) and the ECS task definition will reference this ARN in its configuration.
- **Manual Population:** An administrator must use the AWS CLI/Console to populate the `SecretString` post-deployment.

## 3. SECRET JSON FORMAT
Based on `apps/api/hiron/core/config.py` and `hiron/embeddings/generator.py`, the exact JSON structure expected by the ECS task is:

```json
{
  "DATABASE_URL": "postgresql+asyncpg://hiron_app:password@db.example.com/hiron_prod",
  "APP_SECRET_KEY": "your_secure_secret",
  "REDIS_URL": "redis://redis.example.com:6379/0",
  "OPENAI_API_KEY": "sk-proj-..."
}
```

No other variables will be invented. The ECS execution role will inject these into the container environment using `valueFrom` mappings to the secret ARN.

## 4. DATABASE ROLE
- **Migration Role:** The GitHub Actions CI/CD runs `alembic upgrade head` using `PROD_DATABASE_URL` (superuser role).
- **Application Role:** The ECS runtime uses `DATABASE_URL` (the `hiron_app` non-superuser role) via Secrets Manager.
- **Status:** **Production migration connectivity requires external verification.** There is no database defined in Terraform. We assume the database is externally hosted (e.g., Supabase) and accessible to both GitHub Actions runners and the NAT Gateway.

## 5. ECS TASK ROLE
**Status: LEAST PRIVILEGE PRESERVED**
A codebase inspection confirms `boto3` is not used. The application's `S3StorageProvider` is currently a mock implementation.
- **Decision:** We will **NOT** create an ECS task role. The container does not require any AWS API permissions at runtime. Granting `s3:*` would violate least privilege.

## 6. EXECUTION ROLE
The ECS Execution Role requires:
- `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`
- `logs:CreateLogStream`, `logs:PutLogEvents`
- `secretsmanager:GetSecretValue`

**Decision:** We will attach the AWS-managed `AmazonECSTaskExecutionRolePolicy` for ECR and CloudWatch access, plus an inline policy for Secrets Manager. The managed policy is strictly scoped to the exact ECR and Logs actions required for ECS bootstrap and is operationally standard.

## 7. ECS HARDENING
- **Readonly Root Filesystem:** FastAPI/Starlette spools large multi-part file uploads to `/tmp` using Python's `tempfile.SpooledTemporaryFile`. Additionally, `Dockerfile.api` creates `/app/storage`.
- **Decision:** Setting `readonlyRootFilesystem = true` is highly recommended, but it **requires** mounting an ephemeral `tmpfs` volume to `/tmp` and `/app/storage` in the ECS Task Definition to prevent upload and storage crashes. We will include this `tmpfs` mount in the implementation.

## 8. ALB HEALTH CHECK
**Status: DISCREPANCY VERIFIED**
The FastAPI router strictly exposes `/api/v1/health`. The Terraform target group currently points to `/api/health`. The implementation will correct the target group path.

## 9. ECS DEPLOYMENT SAFETY
- **Circuit Breaker:** Enabled (`enable = true`, `rollback = true`).
- **Rolling Update:** `minimum_healthy_percent = 100`, `maximum_percent = 200`.
- **Justification:** For a `desired_count` of 2, these settings ensure AWS provisions 2 NEW tasks (reaching 200% capacity) and waits for them to become healthy before terminating the 2 OLD tasks. This guarantees zero downtime and ensures capacity never drops below 2.

## 10. ECR IMAGE TAGGING
**Status: ACCEPTED EXISTING DESIGN**
We will maintain the `latest` tag mutation to preserve compatibility with `.github/workflows/deploy.yml`. Immutable SHA deployment is classified as **FUTURE HARDENING**.

## 11. AUTOSCALING
**Status: DEFERRED**
`ecs_min_capacity` and `ecs_max_capacity` describe desired capacity bounds in `variables.tf`, but do not automatically provision Application Auto Scaling. Autoscaling is deferred as it is not strictly required for the acceptance criteria of Phase 16.4.

## 12. MIGRATION CONNECTIVITY
**Status: UNRESOLVED DEPLOYMENT REQUIREMENT**
Production DB connectivity from GitHub-hosted runners is NOT verified and will not be solved via ECS implementation. It remains an explicit external dependency.

## 13. TERRAFORM PLAN SAFETY
The final implementation must include `terraform fmt`, `terraform validate`, and `terraform plan`. The implementation will STOP immediately if the plan proposes destructive changes (e.g., replacing the existing VPC, ALB, S3, or security groups).

## 14. FINAL IMPLEMENTATION SCOPE
The planned implementation will consist exclusively of:
- `infra/terraform/ecs.tf`
- `infra/terraform/iam.tf`
- `infra/terraform/network.tf` (To provision the NAT Gateway and route tables)
- Minimal correction to `infra/terraform/main.tf` (ALB health check path).

## 15. FINAL GATE STATUS

- **VERIFIED:** CI/CD compatibility, ALB architecture, Logging design, ECS compute variables, Task Definition design, Secret JSON format.
- **STATICALLY VERIFIED:** Existing VPC topography, Security Groups.
- **UNVERIFIED:** ECR Bootstrap capability, live ECS task spin-up.
- **BLOCKERS:** Private subnet egress is missing.
- **ASSUMPTIONS:** The production database is accessible from GitHub Actions runners for migrations.
- **SELECTED EGRESS ARCHITECTURE:** Option A (NAT Gateway) to ensure the AI recruitment application can reach OpenAI/Anthropic APIs.
- **SECURITY TRADEOFFS:** `latest` image tag mutability is accepted for CI/CD simplicity. Secret *metadata* exists in Terraform, but secret *values* are strictly excluded.
- **FUTURE HARDENING:** Immutable SHA image tags, ECS Autoscaling policies.
- **IMPLEMENTATION FILES:** `ecs.tf`, `iam.tf`, `network.tf`, `main.tf` modification.
- **VALIDATION PLAN:** `terraform validate` -> `terraform plan` -> Name match verification.
- **ACCEPTANCE CRITERIA:**
  - **A.** ECR `hiron-api` exists with scan-on-push.
  - **B.** ECS execution role exists with SecretsManager read access.
  - **C.** ECS task role is omitted (least privilege).
  - **D.** CloudWatch log group `/ecs/hiron-production-api` exists.
  - **E.** Fargate task definition exists with `tmpfs` mounts, fetching secrets safely.
  - **F.** ECS service `hiron-api-service` attaches to existing `hiron-production-api-tg`.
  - **G.** ECS tasks run only in private subnets.
  - **H.** ALB health check correctly polls `/api/v1/health`.
  - **I.** Private subnet egress blocker is resolved via NAT Gateway.
  - **J.** Terraform state remains free of all secret values.
  - **K.** CI/CD names match exactly.
