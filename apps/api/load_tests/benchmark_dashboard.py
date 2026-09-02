# ruff: noqa: T201
import asyncio
import os
import time
import uuid

import httpx
import numpy as np
import psycopg


def get_loadtest_tenant_and_token(base_url: str) -> tuple[str, str]:
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://hiron_user:hiron_secure_password@localhost:5432/hiron_dev"
    )
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM tenants WHERE slug = 'loadtest-tenant'")
        result = cur.fetchone()
        if not result:
            raise RuntimeError("loadtest-tenant not found. Run seed_loadtest.py first.")
        tenant_id = str(result[0])

    response = httpx.post(
        f"{base_url}/api/v1/auth/login",
        json={
            "email": "admin@loadtest.hiron.ai",
            "password": "LoadTestPassword123!",
            "tenantId": tenant_id,
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"Login failed: {response.text}")

    token = response.json().get("data", {}).get("accessToken")
    return tenant_id, str(token)


async def benchmark_dashboard(
    base_url: str, token: str, iterations: int = 100, concurrency: int = 10
) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    latencies: list[float] = []

    async def fetch(client: httpx.AsyncClient) -> None:
        start = time.perf_counter()
        res = await client.get("/api/v1/dashboard/summary")
        end = time.perf_counter()
        if res.status_code == 200:
            latencies.append((end - start) * 1000)
        else:
            print(f"Error {res.status_code}: {res.text}")

    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=60.0) as client:
        # Warmup
        for _ in range(3):
            await client.get("/api/v1/dashboard/summary")

        # Benchmark
        tasks = []
        for _ in range(iterations):
            tasks.append(fetch(client))
            if len(tasks) >= concurrency:
                await asyncio.gather(*tasks)
                tasks.clear()
        if tasks:
            await asyncio.gather(*tasks)

    if latencies:
        print(
            f"--- Dashboard Summary Benchmark ({iterations} requests, {concurrency} concurrency) ---"
        )
        print(f"Min: {np.min(latencies):.2f} ms")
        print(f"Max: {np.max(latencies):.2f} ms")
        print(f"Avg: {np.mean(latencies):.2f} ms")
        print(f"P95: {np.percentile(latencies, 95):.2f} ms")
    else:
        print("No successful requests recorded.")


if __name__ == "__main__":
    base_url = os.getenv("API_URL", "http://localhost:8000")
    tenant_id, token = get_loadtest_tenant_and_token(base_url)
    asyncio.run(benchmark_dashboard(base_url, token))
