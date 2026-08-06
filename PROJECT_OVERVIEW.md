# Hiron Project Overview

This document provides a factual overview of the Hiron codebase, system components, technical architecture, and current implementation status based strictly on repository inspection.

---

## 1. Repository Structure

Hiron is structured as a monorepo containing application services, infrastructure configurations, documentation, and operational scripts:

```
hiron/
├── apps/
│   ├── api/                    # FastAPI Core API backend application
│   └── web/                    # Next.js 14 App Router frontend
├── services/
│   └── ai/                     # Standalone FastAPI AI Microservice (spaCy/OpenAI)
├── workers/
│   └── celery/                 # Celery background worker module
├── infra/
│   └── docker/                 # Multi-stage Dockerfiles & Docker Compose manifests
├── docs/                       # Architecture, Database, API, and Operations specs
├── scripts/                    # Maintenance, setup, and database seeding scripts
└── .github/
    └── workflows/              # GitHub Actions CI/CD automation pipelines
```

---

## 2. Tech Stack Summary

- **Primary Languages**: Python 3.12+ / 3.13, TypeScript 5.5.4
- **Backend Stack**: FastAPI 0.115+, Pydantic v2, SQLAlchemy 2.0 Async, Alembic, `structlog`
- **Frontend Stack**: Next.js 14 (App Router), React 18, TypeScript, TailwindCSS
- **AI & NLP**: OpenAI API (`gpt-4o-2024-08-06`, `text-embedding-3-small`), spaCy 3.7+, `pdfplumber`, `python-docx`
- **Database & Search**: PostgreSQL 16, `pgvector` extension
- **Caching & Messaging**: Redis 7.2, Celery 5.4+
- **DevOps & Containerization**: Docker, Docker Compose, GitHub Actions
- **Package Managers**: `uv` (Python), `pnpm` (Node.js)

---

## 3. Applications

- **`apps/api`**: FastAPI core backend application serving REST API endpoints under `/api/v1/*`. Implements a 4-layer architecture ($\text{Router} \rightarrow \text{Service} \rightarrow \text{Repository} \rightarrow \text{Database}$).
- **`apps/web`**: Next.js 14 web frontend application built with React, TypeScript, and App Router.

---

## 4. Microservices

- **`services/ai`**: Standalone FastAPI microservice responsible for isolated spaCy NLP document entity extraction and OpenAI API interactions on port 8001.

---

## 5. Background Workers

- **`workers/celery`**: Celery background workers using Redis as the message broker for asynchronous resume parsing (`hiron.resumes.parse_resume`), background embedding generation, and notification tasks.

---

## 6. Docker Container Orchestration

Container definitions and orchestration manifests under `infra/docker/` and root `docker-compose.yml`:

- **`Dockerfile.api`**: Python 3.13-slim multi-stage build running the FastAPI core application as an unprivileged user (`hiron`, UID 10001) with HTTP health check probes.
- **`Dockerfile.ai`**: Python 3.13-slim multi-stage build running the standalone AI microservice as unprivileged user `hiron`.
- **`Dockerfile.web`**: Node 20 / pnpm multi-stage build producing the Next.js web application image.
- **`docker-compose.yml`**: Local development orchestration running 6 containers: `postgres` (pgvector), `redis`, `api`, `worker`, `ai`, and `web`.

---

## 7. Database & Vector Engine

- **Primary Database**: PostgreSQL 16 instance with 15 versioned Alembic migrations.
- **Vector Search Engine**: `pgvector` extension storing 1536-dimensional float vector embeddings for candidates and job requisitions.
- **Data Capabilities**: Relational OLTP tables, JSONB columns for semi-structured data, GIN indexes on tsvector columns for full-text keyword search, and PostgreSQL Row Level Security (RLS) policies.
- **Database Seeding**: Idempotent bootstrap script (`scripts/seed.py`) populating default Tenant and `org_admin` User.

---

## 8. Caching & Task Queuing

- **Distributed Cache & Broker**: Redis 7.2.
- **In-Memory Cache**: Thread-safe async LRU cache manager (`app_cache` in `hiron.core.cache`) providing hit/miss statistics and cache eviction methods.

---

## 9. AI Services

- **Candidate Fit Scoring**: OpenAI `gpt-4o-2024-08-06` model performing 3-dimensional candidate evaluation (Technical 40%, Experience 35%, Education 25%) generating fit scores (0–100), explanations, and recommendation bands (`strong_hire`, `hire`, `consider`, `no_hire`).
- **Vector Embedding Generation**: OpenAI `text-embedding-3-small` generating 1536-dimensional vector embeddings stored in `pgvector` columns.
- **Resume Text Extraction**: spaCy NLP pipelines combined with `pdfplumber` (PDF) and `python-docx` (DOCX) for entity extraction (skills, work history, education, contact details).
- **AI Usage Tracking**: `AIUsageLog` model tracking prompt/completion tokens, model operation breakdown, and USD cost accounting.

---

## 10. Storage Providers

- **Document Storage**: Local disk storage for development (`./storage/<tenant_id>/`) with S3 compatibility configured for AWS S3 document storage.

---

## 11. Authentication & Security

- **JWT Authentication**: Asymmetric RS256 signing using RSA 4096-bit keypairs with 15-minute access tokens and 7-day refresh token rotation.
- **Password Hashing**: Argon2id password hashing algorithm.
- **Multi-Tenant Isolation**: Header-enforced tenant context (`X-Tenant-ID`) via `TenantIsolationMiddleware` and database Row Level Security (RLS).
- **HTTP Hardening**: `SecurityHeadersMiddleware` enforcing HSTS, CSP, X-Frame-Options (`DENY`), and X-Content-Type-Options (`nosniff`).
- **Payload Limiting**: `RequestSizeLimitMiddleware` rejecting request bodies exceeding 10 MB.

---

## 12. Testing & Quality Gates

- **Python Quality Gates**:
  - `uv run ruff check`: 0 errors
  - `uv run mypy apps/api`: 0 errors across 239 source files
  - `uv run pytest`: **339 passed, 1 skipped** (340 total tests)
- **Web Quality Gates**:
  - `npx eslint .` (in `apps/web`): 0 errors
  - `npx tsc --noEmit` (in `apps/web`): 0 errors
  - `pnpm --filter @hiron/web build`: 0 errors (Next.js production build succeeds)
- **Docker Health**: All 6 containers (`postgres`, `redis`, `api`, `worker`, `ai`, `web`) up and healthy.

---

## 13. Current Implementation Status

- **Phase 0 (Scaffolding)**: **100% COMPLETE** (Monorepo, FastAPI probes, Alembic migrations, Docker Compose stack with all 6 services healthy, Next.js 14 App Router setup, zero quality gate errors).
- **Backend APIs (Phases 1–19)**: 60+ REST API endpoints implemented and fully tested across Auth, Tenants, Users, Jobs, Candidates, Resumes, Embeddings, AI Scoring, Vector Search, Kanban Pipeline, Notes, Tags, Dashboard Metrics, Audit Logs, and AI Usage.
- **Frontend Applications (Phases 1–14)**: Next.js 14 App Router web shell configured and passing build; UI component integration scheduled phase-by-phase starting with Phase 1 Frontend Auth.
