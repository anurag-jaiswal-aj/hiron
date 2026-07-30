#!/usr/bin/env python3
"""Database initialization script to create pgvector extension and verify database connectivity."""

import asyncio
import sys
from pathlib import Path

# Add apps/api to Python path for module resolution
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "apps" / "api"))

from sqlalchemy import text

from hiron.core.config import get_settings
from hiron.core.database import engine


async def initialize_database() -> None:
    """Initialize database extensions, verify connectivity, and prepare platform database infrastructure."""
    settings = get_settings()
    print(
        f"Connecting to database: {settings.postgres_db} at {settings.postgres_host}:{settings.postgres_port}"
    )

    try:
        async with engine.begin() as conn:
            # Create pgvector extension (§10 & Database Design §1)
            print("Creating extension: pgvector (vector)...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            print("✓ Extension 'vector' initialized successfully.")

        print("✓ Database initialization complete.")
    except Exception as exc:
        print(f"❌ Database initialization failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(initialize_database())
