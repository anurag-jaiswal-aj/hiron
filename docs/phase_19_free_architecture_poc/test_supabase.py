import asyncio
import os
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

async def test_supabase_compatibility():
    database_url = os.getenv("SUPABASE_DATABASE_URL")
    if not database_url:
        print("ERROR: SUPABASE_DATABASE_URL environment variable is missing.")
        return

    # Using asyncpg driver
    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as conn:
            print("1. Successfully connected to PostgreSQL.")

            # Test vector extension
            await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))
            print("2. pgvector extension successfully enabled/verified.")

            # Test UUID generation and JSONB
            result = await conn.execute(sa.text("SELECT gen_random_uuid(), '{\"key\": \"value\"}'::jsonb;"))
            row = result.fetchone()
            print(f"3. gen_random_uuid() and JSONB work. Sample UUID: {row[0]}")

            # Test RLS and standard features
            await conn.execute(sa.text("CREATE TABLE IF NOT EXISTS _test_poc (id UUID PRIMARY KEY, data JSONB);"))
            await conn.execute(sa.text("ALTER TABLE _test_poc ENABLE ROW LEVEL SECURITY;"))
            print("4. Row Level Security successfully enabled on test table.")

            # Test vector column
            await conn.execute(sa.text("ALTER TABLE _test_poc ADD COLUMN IF NOT EXISTS embedding vector(3);"))
            print("5. Vector column successfully added.")

            # Clean up
            await conn.execute(sa.text("DROP TABLE _test_poc;"))
            print("6. Cleaned up test resources.")

        print("ALL SUPABASE COMPATIBILITY TESTS PASSED.")
    except Exception as e:
        print(f"ERROR during Supabase compatibility test: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_supabase_compatibility())
