# Hiron Environment Variables Reference

This document provides a comprehensive reference of all environment variables used across Hiron applications (`apps/api`, `apps/web`), microservices (`services/ai`), background workers (`workers/celery`), and deployment templates (`.env.production.example`).

---

## 1. Core Application Settings

| Variable Name     | Status               | Default Value               | Service(s)                                   | Purpose                                                                             |
| ----------------- | -------------------- | --------------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------- |
| `ENVIRONMENT`     | Optional             | `development`               | Core API, AI Service, Web                    | Sets deployment environment mode (`development`, `staging`, `production`).          |
| `LOG_LEVEL`       | Optional             | `INFO`                      | Core API, AI Service, Workers                | Configures `structlog` logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`).     |
| `PORT`            | Optional             | `8000`                      | Core API (`8000`), AI (`8001`), Web (`3000`) | HTTP server listening port.                                                         |
| `API_V1_PREFIX`   | Optional             | `/api/v1`                   | Core API                                     | Global REST API route prefix for all endpoints.                                     |
| `APP_SECRET_KEY`  | **Required** in Prod | `your_app_secret_key_here`  | Core API                                     | Application secret key used for session cryptography and state validation.          |
| `ALLOWED_ORIGINS` | Optional             | `["http://localhost:3000"]` | Core API                                     | JSON array of origins permitted by Cross-Origin Resource Sharing (CORS) middleware. |

---

## 2. Authentication & Security Settings

| Variable Name                 | Status               | Default Value          | Service(s) | Purpose                                                                  |
| ----------------------------- | -------------------- | ---------------------- | ---------- | ------------------------------------------------------------------------ |
| `JWT_ALGORITHM`               | Optional             | `RS256`                | Core API   | Asymmetric signing algorithm for JWT access tokens.                      |
| `JWT_PRIVATE_KEY_PATH`        | **Required** in Prod | `keys/jwt_private.pem` | Core API   | File system path to RSA 4096-bit private key for signing access tokens.  |
| `JWT_PUBLIC_KEY_PATH`         | **Required** in Prod | `keys/jwt_public.pem`  | Core API   | File system path to RSA 4096-bit public key for verifying access tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional             | `15`                   | Core API   | Expiration time-to-live (TTL) for JWT access tokens in minutes.          |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | Optional             | `7`                    | Core API   | Expiration time-to-live (TTL) for refresh tokens in days.                |
| `ARGON2_TIME_COST`            | Optional             | `3`                    | Core API   | Argon2id password hashing time iterations parameter.                     |
| `ARGON2_MEMORY_COST`          | Optional             | `65536` (64 MiB)       | Core API   | Argon2id password hashing memory cost in KiB.                            |
| `ARGON2_PARALLELISM`          | Optional             | `4`                    | Core API   | Argon2id password hashing thread parallelism count.                      |

---

## 3. Database Settings (PostgreSQL & pgvector)

| Variable Name       | Status               | Default Value                 | Service(s)              | Purpose                                                        |
| ------------------- | -------------------- | ----------------------------- | ----------------------- | -------------------------------------------------------------- |
| `POSTGRES_HOST`     | Optional             | `localhost`                   | Core API, Setup Scripts | Hostname of PostgreSQL 16 database server.                     |
| `POSTGRES_PORT`     | Optional             | `5432`                        | Core API                | Port of PostgreSQL 16 database server.                         |
| `POSTGRES_DB`       | Optional             | `hiron_dev`                   | Core API, Alembic       | Target database name.                                          |
| `POSTGRES_USER`     | Optional             | `hiron_user`                  | Core API                | Username for database connection authentication.               |
| `POSTGRES_PASSWORD` | **Required** in Prod | `your_postgres_password_here` | Core API                | Password for database connection authentication.               |
| `DATABASE_URL`      | **Required** in Prod | `postgresql+asyncpg://...`    | Core API, Alembic       | Complete async SQLAlchemy database connection string URL.      |
| `DB_POOL_SIZE`      | Optional             | `10`                          | Core API                | SQLAlchemy engine connection pool size.                        |
| `DB_MAX_OVERFLOW`   | Optional             | `20`                          | Core API                | SQLAlchemy engine max overflow connection count.               |
| `DB_POOL_TIMEOUT`   | Optional             | `30`                          | Core API                | SQLAlchemy engine connection pool checkout timeout in seconds. |

---

## 4. Redis, Caching & Task Queue Settings

| Variable Name           | Status   | Default Value              | Service(s)         | Purpose                                                           |
| ----------------------- | -------- | -------------------------- | ------------------ | ----------------------------------------------------------------- |
| `REDIS_URL`             | Optional | `redis://localhost:6379/0` | Core API, Cache    | Connection URL for Redis cache and rate limiting database.        |
| `CELERY_BROKER_URL`     | Optional | `redis://localhost:6379/1` | Background Workers | Message broker connection URL for Celery asynchronous task queue. |
| `CELERY_RESULT_BACKEND` | Optional | `redis://localhost:6379/2` | Background Workers | Result backend storage connection URL for Celery task outcomes.   |

---

## 5. AI Services & Provider Settings

| Variable Name             | Status               | Default Value            | Service(s)           | Purpose                                                                        |
| ------------------------- | -------------------- | ------------------------ | -------------------- | ------------------------------------------------------------------------------ |
| `OPENAI_API_KEY`          | **Required** in Prod | `None` / `""`            | Core API, AI Service | API key for OpenAI LLM fit scoring and vector embedding generation.            |
| `DEFAULT_LLM_MODEL`       | Optional             | `gpt-4o-2024-08-06`      | Core API, AI Service | OpenAI model identifier used for 3D candidate evaluation.                      |
| `DEFAULT_EMBEDDING_MODEL` | Optional             | `text-embedding-3-small` | Core API, AI Service | OpenAI model identifier used for 1536-dimensional vector embedding generation. |

---

## 6. Observability & Monitoring Settings

| Variable Name     | Status   | Default Value | Service(s)       | Purpose                                                                |
| ----------------- | -------- | ------------- | ---------------- | ---------------------------------------------------------------------- |
| `DATADOG_API_KEY` | Optional | `None`        | Production Infra | Datadog API key for APM metric and log telemetry collection.           |
| `SENTRY_DSN`      | Optional | `None`        | Core API, Web    | Sentry Data Source Name (DSN) for error tracking and crash monitoring. |
