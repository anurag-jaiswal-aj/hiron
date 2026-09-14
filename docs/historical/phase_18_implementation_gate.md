# Phase 18 Implementation Gate: Production Deployment

## 1. Phase 18 Objective
The objective of Phase 18 is the full production deployment of the Hiron platform to AWS infrastructure. This encompasses establishing monitoring, alerting, backup and restore protocols, CI/CD pipelines, Vercel frontend configuration, TLS, DNS, and achieving complete operational readiness as defined by the project roadmap.

## 2. Dependencies
- **Strict Prerequisites**: All work from Phase 1 through Phase 17 must be fully complete and verified. 
- **Phase 17 Finalization**: The Phase 17 repository state is definitively locked at commit `c9281b3f133e782c5e472363e8b90f815955bed4`. Under no circumstances may Phase 17 work be modified, deleted, or altered during Phase 18.

## 3. Formal Gate Structure
To safely manage the massive surface area of a production deployment, Phase 18 is decomposed into the following strict, verifiable gates:

- **Gate 1**: Implementation Specification (This Document)
- **Gate 2**: AWS Infrastructure Provisioning (Terraform)
- **Gate 3**: CI/CD Pipelines and Application Deployment
- **Gate 4**: Monitoring, Logging, and Alerting Configurations
- **Gate 5**: Database Operations & Disaster Recovery Verification
- **Gate 6**: Production Launch Readiness & Smoke Tests
- **Gate 7**: Final Phase 18 Sign-off & Commit

---

## 4. Gate Definitions

### Gate 1 — Implementation Specification (Current)
- **Objective**: Define the rigid rules of engagement, requirements, and missing data for Phase 18.
- **Scope**: Authoring `phase_18_implementation_gate.md`.
- **Prerequisites**: Phase 17 finalized (`c9281b3f133e782c5e472363e8b90f815955bed4`).
- **Implementation Responsibilities**: Generate this exact specification file.
- **Expected Files**: `phase_18_implementation_gate.md`.
- **Commands**: Read-only Git inspection.
- **Verification Requirements**: User audit of this file against `docs/IMPLEMENTATION_ROADMAP.md`.
- **Acceptance Criteria**: This specification accurately reflects the roadmap without assuming missing variables.
- **Failure Conditions**: Hallucinating missing infrastructure variables or secrets.
- **Rollback Considerations**: Delete the markdown file.
- **Must NOT Change**: Any application source code, Terraform configurations, or previous documentation.
- **Required Evidence**: The presence of this complete markdown file.
- **Explicit Approval Required**: YES.

### Gate 2 — AWS Infrastructure Provisioning
- **Objective**: Provision the baseline AWS environment.
- **Scope**: 
  - Terraform state management (S3 backend, DynamoDB locking)
  - AWS VPC
  - ECS Fargate cluster
  - RDS PostgreSQL 16 (Multi-AZ, 35-day retention)
  - ElastiCache Redis
  - Encrypted S3 bucket
  - ALB and WAF
  - Route 53
  - ACM TLS certificates
- **Prerequisites**: Gate 1 PASS. All Unknowns/Missing Information for AWS resources must be supplied.
- **Implementation Responsibilities**: Author and apply Terraform configurations.
- **Expected Files**: `infra/terraform/*.tf`
- **Commands**: `terraform init`, `terraform plan`, `terraform apply`.
- **Verification Requirements**: AWS Console or CLI verification that all scoped resources exist exactly as defined.
- **Acceptance Criteria**: Infrastructure is provisioned without manual console clicks; Terraform state is safely locked in S3/DynamoDB.
- **Failure Conditions**: `terraform apply` fails, IAM permission errors, resource quota limits hit.
- **Rollback Considerations**: `terraform destroy` (ONLY if strictly approved and no production data exists).
- **Must NOT Change**: Application source code.
- **Required Evidence**: Clean `terraform apply` output, successful resource verification.
- **Explicit Approval Required**: YES (Especially before `terraform apply`).

### Gate 3 — CI/CD Pipelines and Application Deployment
- **Objective**: Automate production deployments.
- **Scope**: 
  - GitHub Actions → ECR → ECS deployment flow.
  - Vercel production deployment and configuration.
- **Prerequisites**: Gate 2 PASS. AWS infrastructure running.
- **Implementation Responsibilities**: Configure GitHub Actions workflows and initialize the Vercel project.
- **Expected Files**: `.github/workflows/deploy.yml`, `vercel.json` or equivalent configurations.
- **Commands**: `git push` to trigger workflows, Vercel CLI deployment.
- **Verification Requirements**: A successful automated deployment from GitHub Actions to ECS, and Vercel to edge.
- **Acceptance Criteria**: Commits to the main branch automatically deploy the API to ECS and frontend to Vercel.
- **Failure Conditions**: Action failures, ECR authentication issues, Vercel build failures.
- **Rollback Considerations**: Revert GitHub Actions workflow file. Re-deploy previous stable tag.
- **Must NOT Change**: Terraform infrastructure files.
- **Required Evidence**: Link to passing GitHub Actions run and successful Vercel deployment logs.
- **Explicit Approval Required**: YES.

### Gate 4 — Monitoring, Logging, and Alerting
- **Objective**: Ensure deep observability of the production environment.
- **Scope**: 
  - Datadog dashboards (Configuration)
  - Sentry (Configuration)
  - CloudWatch (Configuration)
  - PagerDuty (Integration for API error rate >1%)
  - Slack alerts (Integration for p99 >5s, DB CPU >80%)
- **Prerequisites**: Gate 3 PASS. Required third-party credentials externally supplied.
- **Implementation Responsibilities**: Add Datadog agents/sidecars to ECS, configure application-level Sentry SDK, setup CloudWatch log groups, create Terraform/API definitions for alerts.
- **Expected Files**: Updates to `ecs.tf`, application configuration files.
- **Commands**: `terraform apply` for monitoring infrastructure, test alert scripts.
- **Verification Requirements**: Verify dashboards are receiving live data and alerts trigger successfully.
- **Acceptance Criteria**: All scoped monitoring systems are active.
- **Failure Conditions**: No data appearing in Datadog/CloudWatch, Slack/PagerDuty Webhooks failing.
- **Rollback Considerations**: Remove monitoring sidecars/agents if they cause task failures.
- **Must NOT Change**: Core application business logic.
- **Required Evidence**: Screenshots/logs of triggered test alerts and live dashboard data.
- **Explicit Approval Required**: YES.

### Gate 5 — Database Operations & Disaster Recovery
- **Objective**: Safely transition the database to a production-ready state and prove recovery capabilities.
- **Scope**: Final migration dry-run, backup creation, restoration into staging, disaster recovery verification.
- **Prerequisites**: Gate 2 PASS (RDS exists).
- **Implementation Responsibilities**: Execute database migrations against production, execute manual snapshot, restore snapshot to a temporary staging instance.
- **Expected Files**: None (Operation execution).
- **Commands**: `alembic upgrade head`, AWS CLI snapshot commands.
- **Verification Requirements**: The restored staging database contains exactly the schema and data of the production snapshot.
- **Acceptance Criteria**: Migrations succeed, backups work, and DR restore is proven.
- **Failure Conditions**: Migration conflicts, snapshot failures, restore timeouts.
- **Rollback Considerations**: Immediate restoration from the pre-migration snapshot.
- **Must NOT Change**: Infrastructure definitions, CI/CD pipelines.
- **Required Evidence**: Logs of the successful migration, AWS CLI output showing completed snapshot and successful restoration.
- **Explicit Approval Required**: YES.

### Gate 6 — Production Launch Readiness & Smoke Tests
- **Objective**: Verify the live platform from an end-user perspective.
- **Scope**:
  - Production health endpoint check
  - Production login verification
  - Core application workflow verification
  - TLS 1.3 and valid certificate verification
- **Prerequisites**: Gates 1-5 PASS.
- **Implementation Responsibilities**: Execute manual and automated smoke tests against the live domains.
- **Expected Files**: None (Verification only).
- **Commands**: `curl`, browser tests, Playwright (configured for prod URL).
- **Verification Requirements**: All acceptance criteria pass against `api.hiron.ai` and `app.hiron.ai`.
- **Acceptance Criteria**: Application is 100% functional in production.
- **Failure Conditions**: 500 errors, SSL certificate warnings, CORS failures.
- **Rollback Considerations**: Depends on failure (e.g., DNS rollback).
- **Must NOT Change**: Any configurations (unless fixing a direct launch bug).
- **Required Evidence**: Execution logs of the smoke tests showing PASS.
- **Explicit Approval Required**: YES.

### Gate 7 — Final Phase 18 Sign-off & Commit
- **Objective**: Commit the Phase 18 configuration changes to the repository.
- **Scope**: All modified Terraform, CI/CD, and configuration files.
- **Prerequisites**: Gate 6 PASS.
- **Implementation Responsibilities**: Finalize the git state.
- **Expected Files**: All untracked/modified Phase 18 files.
- **Commands**: `git add`, `git commit`.
- **Verification Requirements**: Clean `git status`.
- **Acceptance Criteria**: Phase 18 work is securely versioned.
- **Failure Conditions**: Accidental staging of secrets or state files.
- **Required Evidence**: `git show` output of the final commit.
- **Explicit Approval Required**: YES.

---

## 5. Production Safety Rules
Phase 18 touches real production infrastructure. The following safeguards are absolute:
- **Terraform State**: Must never be committed to Git. It must reside in S3 with DynamoDB locking.
- **Secrets**: Must never be committed. Must be injected via AWS Secrets Manager, Vercel UI, or GitHub Environments.
- **Database Migrations**: Must be executed only during approved maintenance windows after a manual snapshot is taken.
- **Production Data**: Must never be deleted, truncated, or modified via automated test scripts.
- **DNS & Certificates**: TTLs must be lowered to 300s or less prior to DNS changes.
- **Destructive Terraform Operations**: `terraform destroy` or replacing stateful resources (RDS, S3) requires dual-approval.
- **Rollback**: Every infrastructure change must have a documented rollback command before execution.
- **Explicit Approval**: NO destructive production action may be performed without explicit user approval.

---

## 6. Commit Strategy
The project roadmap does not currently define an official commit boundary or message for Phase 18.
- **Proposed Policy**: Phase 18 should utilize a single unified commit (similar to Phase 17) to encapsulate all infrastructure and deployment configurations. 
- **Proposed Commit Message**: `chore: implement production AWS infrastructure and deployment pipelines`
- **Requirement**: This commit boundary and message must be explicitly approved or modified by the user before Gate 7 finalization.

---

## 7. Unknowns / Missing Information
The roadmap does not provide the following critical details. These values **must not be invented**; they must be provided by the user before the relevant gate can proceed:
- Exact AWS account ID and Target Environment.
- AWS Region (e.g., `us-east-1`).
- Terraform backend S3 bucket name.
- Terraform DynamoDB lock table name.
- Domain ownership specifics and DNS provider details.
- Production secrets (Database passwords, JWT secrets, OpenAI API keys).
- ECR repository names.
- ECS service and task sizing (CPU/Memory allocations).
- Desired production capacity and autoscaling thresholds.
- Datadog, Sentry, PagerDuty, and Slack API keys/webhook URLs.
- Vercel project configuration and team scopes.
- Exact production database migration execution procedure (e.g., via bastion host vs. CI/CD task).

---

## 8. Phase 18 Final Acceptance Checklist
- [ ] `api.hiron.ai` accessible
- [ ] `app.hiron.ai` accessible
- [ ] TLS 1.3 configured
- [ ] Valid certificate active
- [ ] Health endpoints return 200
- [ ] Login workflow succeeds
- [ ] Core workflow (job creation, parsing, scoring) succeeds
- [ ] Monitoring dashboards show live data
- [ ] Alerts fire correctly
- [ ] Backup tested successfully
- [ ] Restore to staging verified successfully
- [ ] Runbook complete
- [ ] Incident response procedures documented

---

## 9. Gate Transition Rules
- A gate **CANNOT** be declared PASS based on assumptions.
- Each gate requires **concrete evidence** (e.g., command output, screenshots, explicit logs).
- If a gate fails or hits a blocker, execution must **STOP** immediately and the failure must be reported.
- Do **NOT** automatically proceed to the next gate under any circumstances.
- Wait for **explicit user approval** before beginning the subsequent gate.
