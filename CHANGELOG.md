# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-31

### Added

- Multi-tenant architecture with context-scoped isolation and database Row Level Security (RLS).
- Asymmetric RS256 JWT authentication, Argon2id password hashing, and Role-Based Access Control (RBAC).
- Job requisition management with automated 5-stage pipeline generation.
- Candidate profiles and candidate-job pipeline tracking (`JobCandidate`).
- Multi-format document upload (PDF/DOCX) and spaCy NLP text extraction pipeline.
- 3-dimensional AI candidate fit scoring engine (`gpt-4o-2024-08-06`) with breakdown metrics and score explanations.
- pgvector 1536-dimensional cosine similarity search engine (`text-embedding-3-small`).
- Interactive Kanban pipeline board and candidate stage movement tracking (`CandidateStageHistory`).
- Recruitment dashboard analytics, score distribution stats, and activity feeds.
- Immutable audit log recording actions, actor identities, IP addresses, and state changes.
- AI token consumption tracking, operation logging, and USD cost accounting.
- Post-launch operational maintenance subsystem, cache flushing (`app_cache`), and health diagnostics.

### Security

- Added `SecurityHeadersMiddleware` enforcing HSTS, CSP, X-Frame-Options, and X-Content-Type-Options headers.
- Added `RequestSizeLimitMiddleware` restricting HTTP request payloads to 10 MB.

### Infrastructure

- Declarative AWS Terraform IaC specifying VPC, public/private subnets, ECS Fargate cluster, RDS PostgreSQL 16 Multi-AZ, ElastiCache Redis, S3 bucket storage, and ALB.
- Multi-stage Python 3.13 Docker container builds running under unprivileged non-root service accounts (`hiron` UID 10001).
- Automated GitHub Actions CI/CD workflows for linting, MyPy type checks, pytest execution, ECR image push, Alembic migrations, and ECS rolling updates.

### Testing

- Automated test suite comprising 333 unit, integration, multi-tenant isolation, RBAC, AI scoring benchmark, and end-to-end recruitment workflow tests.

---

For complete technical details, see:  
[docs/releases/v1.0.0.md](docs/releases/v1.0.0.md)
