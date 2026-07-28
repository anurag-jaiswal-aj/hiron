# Hiron — AI-Powered Hiring Intelligence Platform

[![CI Pipeline](https://github.com/anurag-jaiswal-aj/hiron/actions/workflows/ci.yml/badge.svg)](https://github.com/anurag-jaiswal-aj/hiron/actions)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue.svg)](https://www.typescriptlang.org/)

Hiron is a production-grade AI-powered Hiring Intelligence Platform that helps recruiters evaluate candidates using NLP, semantic vector search, explainable AI fit scoring, and automated pipeline workflows.

---

## 📚 Governing Architecture & Specifications

All architectural and engineering decisions in this repository are strictly governed by frozen specification documents in [`docs/`](./docs/):

1. **Engineering Guidelines**: Coding standards, Python/TypeScript style guides, security rules, and AI standards ([`docs/ENGINEERING_GUIDELINES.md`](./docs/ENGINEERING_GUIDELINES.md))
2. **Database Design**: Production PostgreSQL + `pgvector` multi-tenant database design ([`docs/DATABASE_DESIGN.md`](./docs/DATABASE_DESIGN.md))
3. **API Contract**: REST API endpoints, schemas, status codes, and security contracts ([`docs/API_CONTRACT.md`](./docs/API_CONTRACT.md))
4. **UI/UX Design Specification**: Design tokens, component hierarchy, accessibility, and 17 screen wireframes ([`docs/UI_UX_DESIGN.md`](./docs/UI_UX_DESIGN.md))
5. **Implementation Roadmap**: 20-phase execution plan and sprint schedule ([`docs/IMPLEMENTATION_ROADMAP.md`](./docs/IMPLEMENTATION_ROADMAP.md))

---

## 🏗️ Repository Monorepo Structure

```
hiron/
├── apps/
│   ├── api/                    # FastAPI Core API backend application
│   └── web/                    # Next.js 15 App Router frontend
├── packages/
│   ├── shared-types/           # Shared TypeScript interfaces & API contracts
│   ├── ui/                     # Shared UI component primitives (shadcn/ui base)
│   ├── config/                 # Shared linting & configuration templates
│   └── utils/                  # Shared helper functions & formatters
├── services/
│   └── ai/                     # Standalone FastAPI AI Microservice (spaCy/OpenAI)
├── workers/
│   └── celery/                 # Celery background workers for async processing
├── infra/
│   ├── docker/                 # Container Dockerfiles & docker-compose manifests
│   └── terraform/              # Infrastructure as Code (IaC) AWS manifests
├── docs/                       # Frozen Architecture & Design Documents
├── scripts/                    # Development automation & database scripts
└── .github/
    └── workflows/              # GitHub Actions CI/CD automation pipelines
```

---

## ⚙️ Prerequisites

- **Python**: 3.12+ (managed with `uv` or `pip`)
- **Node.js**: 20.x LTS+
- **pnpm**: 9.x+
- **Docker & Docker Compose**: 24+

---

## 🚀 Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/anurag-jaiswal-aj/hiron.git
   cd hiron
   ```

2. **Initialize local environment file (`.env.local`)**:
   > ⚠️ **IMPORTANT**: You MUST run `make setup` before running `docker compose up` because `.env.local` is required by the container environment.
   ```bash
   make setup
   ```

3. **Start local development containers**:
   ```bash
   make dev
   ```

4. **Development Command Reference**:
   - Run type checks across monorepo:
     ```bash
     make type-check
     ```
   - Run linters:
     ```bash
     make lint
     ```
   - Code formatting:
     ```bash
     make format
     ```

---

## 📄 License

Distributed under the Apache 2.0 License. See [`LICENSE`](./LICENSE) for details.
