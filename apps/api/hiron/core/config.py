"""Application environment configuration management via Pydantic BaseSettings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

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

    # 2. Authentication & JWT Tokens (§16.1)
    jwt_algorithm: str = Field(default="RS256", description="JWT signing algorithm")
    jwt_private_key_path: str = Field(
        default="keys/jwt_private.pem", description="Path to RSA private key"
    )
    jwt_public_key_path: str = Field(
        default="keys/jwt_public.pem", description="Path to RSA public key"
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
    db_pool_size: int = Field(default=10, description="SQLAlchemy connection pool size")
    db_max_overflow: int = Field(default=20, description="SQLAlchemy connection max overflow")
    db_pool_timeout: int = Field(default=30, description="SQLAlchemy pool timeout in seconds")

    # 4. Redis & Task Queue
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", description="Celery backend URL"
    )

    # 5. Security & Password Hashing Configuration (§16)
    argon2_time_cost: int = Field(default=3, description="Argon2id time cost iterations")
    argon2_memory_cost: int = Field(
        default=65536, description="Argon2id memory cost in KiB (64 MiB)"
    )
    argon2_parallelism: int = Field(default=4, description="Argon2id parallelism threads")
    argon2_hash_len: int = Field(default=32, description="Argon2id hash output length in bytes")
    argon2_salt_len: int = Field(default=16, description="Argon2id salt length in bytes")

    @property
    def is_production(self) -> bool:
        """Return True if running in production environment."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
