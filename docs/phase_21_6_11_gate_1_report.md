# Phase 21.6.11 Gate 1: AWS Legacy Infrastructure Read-Only Audit

## Executive Summary
This report provides a read-only assessment of the current AWS infrastructure in the Hiron project, evaluating its necessity against the target $0/month serverless architecture (Vercel, Supabase, Upstash, Google AI Studio). The audit reveals that while the codebase has largely been decoupled from AWS-specific SDKs (e.g., no `boto3` dependencies exist), an extensive Terraform configuration remains that defines a full AWS production environment. Due to expired AWS credentials, live production verification was blocked. Certain stateful resources (RDS, S3) are marked as strictly requiring data migration verification before deletion.

## Current AWS Resource Inventory
Based on Terraform definitions, the AWS footprint includes:
- **Compute**: ECS Fargate Cluster, ECS Task Definition, ECS Service.
- **Networking**: VPC, Public/Private Subnets, Internet Gateway, NAT Gateway, Route Tables, Application Load Balancer (ALB), Target Groups.
- **Security**: Security Groups (ALB, ECS, RDS, Redis), WAFv2, IAM Roles (Execution Role).
- **Stateful Data**: RDS PostgreSQL 16 Instance, ElastiCache Redis Cluster (single node), S3 Bucket (Resumes), Secrets Manager.
- **Observability**: CloudWatch Log Group.

## Terraform Resource Inventory
Below is the categorized inventory of all resources found in `infra/terraform/*.tf`:

| Resource Type | Resource Name | Terraform File |
|---|---|---|
| VPC | `aws_vpc.production` | `main.tf` |
| Subnet | `aws_subnet.public_a`, `public_b`, `private_a`, `private_b` | `main.tf` |
| Internet Gateway | `aws_internet_gateway.production` | `network.tf` |
| NAT Gateway | `aws_nat_gateway.production` (and EIP) | `network.tf` |
| Route Tables | `aws_route_table.public`, `.private` | `network.tf` |
| Security Group | `aws_security_group.alb`, `.ecs`, `.rds`, `.redis` | `main.tf`, `rds.tf`, `redis.tf` |
| ALB & Listener | `aws_lb.production`, `aws_lb_target_group.api`, `aws_lb_listener.http_redirect`, `.https` | `main.tf` |
| WAF | `aws_wafv2_web_acl.production` | `main.tf` |
| ECS Cluster | `aws_ecs_cluster.production` | `main.tf` |
| ECR | `aws_ecr_repository.hiron_api` | `ecs.tf` |
| ECS Task/Service | `aws_ecs_task_definition.hiron_api`, `aws_ecs_service.hiron_api` | `ecs.tf` |
| Autoscaling | `aws_appautoscaling_target.ecs_target`, `aws_appautoscaling_policy.ecs_policy_cpu` | `autoscaling.tf` |
| IAM Roles | `aws_iam_role.ecs_execution_role` | `iam.tf` |
| Secrets Manager | `aws_secretsmanager_secret.api_secrets` | `ecs.tf` |
| RDS | `aws_db_instance.production` | `rds.tf` |
| ElastiCache | `aws_elasticache_replication_group.production` | `redis.tf` |
| S3 | `aws_s3_bucket.resumes` | `main.tf` |
| CloudWatch | `aws_cloudwatch_log_group.ecs_api` | `ecs.tf` |

## Application Dependency Map
A comprehensive search was performed across the application codebase for AWS dependencies:
- **`boto3` / AWS SDKs**: ZERO references found. The application relies entirely on standard REST clients or abstracted interfaces.
- **Storage / S3**: `apps/api/hiron/storage/provider.py` contains string formatting logic that loosely mimics S3 URIs (`s3://...` and `amazonaws.com` URLs) for mocking, but does not use any AWS libraries to perform network requests.
- **ElastiCache / Redis**: `apps/api/hiron/core/cache.py` uses `redis.from_url()`. This is completely agnostic to ElastiCache and seamlessly supports Upstash Redis. It also contains an in-memory fallback.
- **Secrets Manager**: Referenced in `.github/workflows/deploy.yml` and `SECURITY.md`, but the API strictly consumes standard environment variables.
- **Deployment**: `.github/workflows/deploy.yml` explicitly logs into Amazon ECR and updates the ECS service (`aws ecs update-service`).

## Production Runtime Findings
- **Status**: **BLOCKED**
- `aws sts get-caller-identity` returned: `[ERROR]: Your session has expired. Please reauthenticate using 'aws login'.`
- `terraform init` and `terraform plan` failed to execute because the backend (S3) could not be accessed due to the expired credentials.
- As a result, no live inspection of S3 contents, RDS data, or Secrets Manager could be performed.

## Replacement Mapping
To achieve the $0/month architecture, the current AWS resources map directly to the target stack:
- **ECS, ECR, ALB, VPC, NAT Gateway, WAF, CloudWatch** → **Vercel** (Serverless compute, edge routing, edge security, and logging natively included).
- **RDS PostgreSQL** → **Supabase PostgreSQL** (Free tier DB with pgvector).
- **S3 Bucket (Resumes)** → **Supabase Storage** (Direct drop-in for 10MB file storage).
- **Background Jobs (formerly Celery/ECS Workers)** → **Upstash QStash** (Already migrated).
- **ElastiCache Redis** → **Upstash Redis** (Required for distributed caching in Vercel's ephemeral serverless environment, as the current in-memory fallback will not persist state across invocations).

## Data/Storage Migration Verification
- **S3 Resumes**: UNVERIFIED. Live AWS inspection was blocked. It is unknown if existing PDFs/resumes have been copied to Supabase Storage.
- **RDS Database**: UNVERIFIED. It is unknown if production tenant data, candidates, or vector embeddings have been dumped and restored to Supabase.
- **ElastiCache Data**: Generally safe to destroy without migration as it acts as an LRU cache, but ideally confirmed prior to deletion.

## Resource Classification Table

| Resource Type | Classification | Reason |
|---|---|---|
| **ECS / ECR** | LEGACY | Application compute shifting to Vercel. |
| **ALB / WAF** | LEGACY | Traffic shifting to Vercel Edge. |
| **VPC / NAT / Subnets** | LEGACY | Vercel and Supabase do not require these AWS networking components. |
| **CloudWatch / IAM** | LEGACY | Associated purely with ECS deployment. |
| **Secrets Manager** | UNCERTAIN | Needs verification if Vercel Environment Variables have been fully populated. |
| **RDS PostgreSQL** | UNCERTAIN | Requires explicit data migration confirmation. |
| **S3 Bucket** | UNCERTAIN | Requires explicit file migration confirmation. |
| **ElastiCache** | LEGACY / UNCERTAIN | Caching layer will shift to Upstash, but must ensure no critical persistent state exists. |

## Unknowns/Blockers
1. **AWS Credentials**: Cannot authenticate to verify live infrastructure.
2. **Data Migration Status**: Cannot confirm if RDS and S3 data have been safely migrated to Supabase.
3. **Vercel Readiness**: Cannot confirm if Vercel is fully configured with production environment variables to take over traffic immediately upon ALB teardown.
4. **DNS Management**: Route53 `.tf` files exist but mention external management. Must verify DNS cutover strategy.

## Potential Deletion Order
When deletion is approved, it should follow this dependency order:
1. GitHub Actions deployment workflows (preventing new ECS deployments).
2. ECS Services and Task Definitions.
3. ALB, WAF, and Target Groups.
4. ECR Repositories.
5. ElastiCache Redis and its Security Group.
6. VPC, Subnets, NAT Gateways, Internet Gateway.
7. RDS (ONLY after verified data migration).
8. S3 (ONLY after verified file migration).

## Risks
- **Data Loss**: Deleting RDS or S3 before confirming Supabase migration will result in irrecoverable data loss.
- **Downtime**: Tearing down ECS/ALB before DNS is pointed to a healthy Vercel deployment will cause a production outage.

## Explicit Lists

### SAFE TO PROPOSE FOR DELETION
The following resources hold no persistent state and are strictly tied to the obsolete compute layer:
- GitHub Actions AWS deployment workflows (`deploy.yml`).
- `infra/terraform/ecs.tf` (ECS Cluster, Services, Tasks).
- `infra/terraform/autoscaling.tf` (App Autoscaling).
- `infra/terraform/iam.tf` (Execution Roles).
- `infra/terraform/network.tf` (NAT Gateway, IGW, Route Tables).
- `infra/terraform/main.tf` components related to VPC, Subnets, ALB, WAF, and Target Groups.

### MUST NOT BE DELETED
- `aws_db_instance.production` (RDS)
- `aws_s3_bucket.resumes` (S3)
- `aws_secretsmanager_secret.api_secrets` (Secrets)

### REQUIRING FURTHER VERIFICATION
- `aws_elasticache_replication_group.production`: Needs confirmation that it is purely ephemeral cache and safely replaceable by Upstash Redis without data migration.
- `deploy.yml` secrets (need to verify if they are still used for anything else before removal).

## Recommended Next Phase
**Gate 2 (Blocked)**: We must first acquire valid AWS credentials to verify the live RDS and S3 states, confirm Supabase data migration, and ensure Vercel is handling production traffic before we can safely execute any Terraform teardowns.

**STATUS: BLOCKED**
