import asyncio
import os
import time

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_supabase_sqlalchemy():
    database_url = os.getenv("SUPABASE_DATABASE_URL")
    if not database_url:
        print("ERROR: SUPABASE_DATABASE_URL environment variable is missing.")
        return

    print("Discovered Configuration: Using `asyncpg` with Transaction Pooler compatibility.")
    
    # We must set statement_cache_size=0 when using PgBouncer in transaction mode
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": 0,
        }
    )

    try:
        # 1. Connection & Basic Selects
        async with engine.connect() as conn:
            print("[PASS] AsyncEngine Connection")
            
            # 2. version()
            result = await conn.execute(text("SELECT version();"))
            print(f"[PASS] version(): {result.scalar()}")

            # 3. current_database()
            result = await conn.execute(text("SELECT current_database();"))
            print(f"[PASS] current_database(): {result.scalar()}")

            # 4. SELECT 1
            result = await conn.execute(text("SELECT 1;"))
            print(f"[PASS] SELECT 1: {result.scalar()}")

            # 5. UUID and JSONB
            result = await conn.execute(text("SELECT gen_random_uuid(), '{\"test\": \"ok\"}'::jsonb;"))
            row = result.fetchone()
            print(f"[PASS] UUID: {row[0]} | JSONB: {row[1]}")

        # 6. Transaction Behavior
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TEMP TABLE _hiron_test_tx (id int);"))
            await conn.execute(text("INSERT INTO _hiron_test_tx VALUES (1);"))
            print("[PASS] Transaction begin and execution")
            # implicitly commits on exit of `engine.begin()`
        
        async with engine.connect() as conn:
            # check if temp table exists across connections (temp tables are session-bound, 
            # with transaction pooling, the underlying connection might be different!)
            # Actually, TEMP tables are dangerous with transaction poolers because the connection 
            # might be returned to the pool and another client might get it. 
            # However, for an isolated test, we can create a permanent table and drop it to be safe, 
            # or keep it strictly in one transaction block to avoid pollution.
            pass

        # 7. pgvector and HNSW
        async with engine.begin() as conn:
            # We'll use a real table but drop it immediately to avoid session-bound issues with PgBouncer
            await conn.execute(text("DROP TABLE IF EXISTS _hiron_test_vector;"))
            await conn.execute(text("""
                CREATE TABLE _hiron_test_vector (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    metadata jsonb,
                    embedding vector(3)
                );
            """))
            print("[PASS] Create vector table")
            
            # Insert vector
            await conn.execute(text("INSERT INTO _hiron_test_vector (metadata, embedding) VALUES ('{\"name\": \"test\"}', '[1, 2, 3]');"))
            print("[PASS] Insert vector")

            # Retrieve vector
            result = await conn.execute(text("SELECT id, embedding FROM _hiron_test_vector LIMIT 1;"))
            row = result.fetchone()
            print(f"[PASS] Retrieve vector: ID={row[0]}")

            # Similarity query
            result = await conn.execute(text("SELECT id FROM _hiron_test_vector ORDER BY embedding <-> '[1, 2, 3]' LIMIT 1;"))
            print(f"[PASS] Vector similarity query: MATCH={result.scalar()}")

            # HNSW index
            await conn.execute(text("CREATE INDEX _test_hnsw ON _hiron_test_vector USING hnsw (embedding vector_l2_ops);"))
            print("[PASS] HNSW index creation")

            # Cleanup
            await conn.execute(text("DROP TABLE _hiron_test_vector;"))
            print("[PASS] Cleanup")

        # 8. Repeated Connections (Transaction Pooling Test)
        async def fetch_one():
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1;"))

        await asyncio.gather(*(fetch_one() for _ in range(50)))
        print("[PASS] Repeated concurrent connections (Transaction Pooling check)")
        
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await engine.dispose()
        print("[PASS] Engine disposal")

if __name__ == "__main__":
    asyncio.run(test_supabase_sqlalchemy())
