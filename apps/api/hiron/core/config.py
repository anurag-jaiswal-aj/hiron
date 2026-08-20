"""Application environment configuration management via Pydantic BaseSettings."""

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Rate Limiting & Security
    rate_limit_requests_per_minute: int = Field(
        default=600, description="Rate limit requests per minute per IP"
    )
    trusted_proxies: list[str] = Field(
        default=["127.0.0.1", "::1"],
        description="List of trusted proxy IPs/CIDRs for resolving X-Forwarded-For",
    )

    """Application settings loaded from environment variables and .env files."""

    gemini_api_key: str | None = Field(default=None, description="Google Gemini API key")
    gemini_embedding_model: str = Field(
        default="gemini-embedding-2", description="Gemini text embedding model"
    )
    qstash_current_signing_key: str | None = Field(default=None, repr=False)
    qstash_next_signing_key: str | None = Field(default=None, repr=False)
    qstash_webhook_url: str | None = Field(default=None)
    qstash_token: str | None = Field(default=None, repr=False)
    worker_url: str | None = Field(
        default=None, description="Base public URL of the deployed worker"
    )

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate required settings for production environment."""
        if self.environment == "production":
            if not self.worker_url:
                raise ValueError("WORKER_URL is required in production environment")
        return self

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # 1. Application Core
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application deployment environment",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging verbosity level",
    )
    port: int = Field(default=8000, description="HTTP server listening port")
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 route prefix")
    app_secret_key: str = Field(
        default="your_app_secret_key_here",
        description="Application secret key for security",
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed origins for CORS policy",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        """Parse allowed origins from JSON array or comma-separated string."""
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                import json

                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if str(origin).strip()]
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
            return [origin.strip() for origin in v_str.split(",") if origin.strip()]
        if isinstance(v, list):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        return []

    # 2. Authentication & JWT Tokens (§16.1)
    jwt_algorithm: str = Field(default="RS256", description="JWT signing algorithm")
    jwt_private_key_path: str = Field(
        default="keys/jwt_private.pem", description="Path to RSA private key for local development"
    )
    jwt_public_key_path: str = Field(
        default="keys/jwt_public.pem", description="Path to RSA public key for local development"
    )
    jwt_private_key_content: str | None = Field(
        default=None, repr=False, description="RSA private key PEM content (production)"
    )
    jwt_public_key_content: str | None = Field(
        default=None, repr=False, description="RSA public key PEM content (production)"
    )
    access_token_expire_minutes: int = Field(default=15, description="Access token TTL in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token TTL in days")

    # 3. Database & PostgreSQL Configuration (§10 & Database Design)
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="hiron_dev", description="PostgreSQL database name")
    postgres_user: str = Field(default="hiron_user", description="PostgreSQL user")
    postgres_password: str = Field(
        default="your_postgres_password_here", description="PostgreSQL password"
    )
    database_url: str = Field(
        default="postgresql+asyncpg://hiron_user:your_postgres_password_here@localhost:5432/hiron_dev",
        description="Async SQLAlchemy database connection URL",
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def ensure_async_dialect(cls, v: str) -> str:
        """Ensure the database URL uses the asyncpg dialect."""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    db_pool_size: int = Field(default=10, description="SQLAlchemy connection pool size")
    db_max_overflow: int = Field(default=20, description="SQLAlchemy connection max overflow")
    db_pool_timeout: int = Field(default=30, description="SQLAlchemy pool timeout in seconds")

    # 4. Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # 5. Security & Password Hashing Configuration (§16)
    argon2_time_cost: int = Field(default=3, description="Argon2id time cost iterations")
    argon2_memory_cost: int = Field(
        default=65536, description="Argon2id memory cost in KiB (64 MiB)"
    )
    argon2_parallelism: int = Field(default=4, description="Argon2id parallelism threads")
    argon2_hash_len: int = Field(default=32, description="Argon2id hash output length in bytes")
    argon2_salt_len: int = Field(default=16, description="Argon2id salt length in bytes")

    # 6. Supabase Storage Configuration
    supabase_url: str | None = Field(default=None, description="Supabase API URL")
    supabase_service_role_key: str | None = Field(
        default=None, repr=False, description="Supabase Service Role Key"
    )
    supabase_storage_bucket: str = Field(
        default="resumes", description="Supabase storage bucket name"
    )

    @property
    def is_production(self) -> bool:
        """Return True if running in production environment."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
