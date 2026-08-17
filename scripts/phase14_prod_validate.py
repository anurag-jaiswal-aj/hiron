#!/usr/bin/env python3
"""Phase 14 Production Validation Harness for AI Usage Analytics."""

import asyncio
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx

# Add apps/api to Python path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "apps" / "api"))

from sqlalchemy import text

from hiron.core.config import get_settings
from hiron.core.database import AsyncSessionLocal
from hiron.core.security import hash_password

API_BASE = "https://hiron-api.vercel.app/api/v1"
EXPECTED_PROD_PROJECT_ID = "bpizcvzqehvbzwkuscfe"

TENANT_A_ID = "00000000-0000-4000-a000-000000000014"
TENANT_B_ID = "00000000-0000-4000-b000-000000000014"

# Deterministic User IDs
USER_A_ADMIN_ID = "00000000-0000-4000-a001-000000000014"
USER_A_REC_ID = "00000000-0000-4000-a002-000000000014"
USER_B_ADMIN_ID = "00000000-0000-4000-b001-000000000014"

SYNTHETIC_PASSWORD = "ValPassword123!"

class ValidationError(Exception):
    pass

def expect_eq(name, actual, expected):
    if actual != expected:
        raise ValidationError(f"Expected {name} to be {expected}, got {actual}")

def expect_near(name, actual, expected, tol=1e-5):
    if abs(float(actual) - float(expected)) > tol:
        raise ValidationError(f"Expected {name} to be near {expected}, got {actual}")

async def verify_safety():
    if os.getenv("ENABLE_PHASE14_PROD_VALIDATION") != "true":
        print("CRITICAL: ENABLE_PHASE14_PROD_VALIDATION=true not set.")
        sys.exit(1)

    parsed_api = urlparse(API_BASE)
    if parsed_api.scheme != "https" or parsed_api.hostname != "hiron-api.vercel.app":
        print("CRITICAL FAILURE: API target is not https://hiron-api.vercel.app. Aborting BEFORE database mutation.")
        sys.exit(1)

    settings = get_settings()
    db_url = str(settings.database_url)

    # Resolve project identity
    if EXPECTED_PROD_PROJECT_ID not in db_url:
        print(f"CRITICAL: Target database does not match expected production identity ({EXPECTED_PROD_PROJECT_ID}).")
        sys.exit(1)

    supabase_url = str(settings.supabase_url) if settings.supabase_url else ""
    if EXPECTED_PROD_PROJECT_ID not in supabase_url:
        print(f"CRITICAL: SUPABASE_URL identity does not match expected production identity ({EXPECTED_PROD_PROJECT_ID}).")
        sys.exit(1)

    print(f"Verified target project identity: {EXPECTED_PROD_PROJECT_ID}")

async def cleanup_data():
    print("\nExecuting cleanup...")
    async with AsyncSessionLocal() as session:
        try:
            # Delete tenants, cascading will handle the rest
            await session.execute(
                text("DELETE FROM tenants WHERE id IN (:ta, :tb)"),
                {"ta": TENANT_A_ID, "tb": TENANT_B_ID},
            )
            await session.commit()

            # Verify cleanup
            result = await session.execute(
                text(
                    "SELECT count(*) FROM ai_usage_logs WHERE tenant_id IN (:ta, :tb)"
                ),
                {"ta": TENANT_A_ID, "tb": TENANT_B_ID},
            )
            ai_logs_count = result.scalar()

            result = await session.execute(
                text("SELECT count(*) FROM tenants WHERE id IN (:ta, :tb)"),
                {"ta": TENANT_A_ID, "tb": TENANT_B_ID},
            )
            tenants_count = result.scalar()

            result = await session.execute(
                text("SELECT count(*) FROM users WHERE tenant_id IN (:ta, :tb)"),
                {"ta": TENANT_A_ID, "tb": TENANT_B_ID},
            )
            users_count = result.scalar()

            if ai_logs_count != 0 or tenants_count != 0 or users_count != 0:
                print(f"CRITICAL FAILURE: Cleanup failed. Found {ai_logs_count} logs, {tenants_count} tenants, and {users_count} users remaining.")
                return False

            print("Cleanup verified successfully.")
            return True
        except Exception as e:
            print(f"CRITICAL FAILURE: Exception during cleanup: {e}")
            return False

async def insert_synthetic_data(session, now: datetime):
    print("Inserting synthetic data...")
    hashed_password = hash_password(SYNTHETIC_PASSWORD)

    # Check if unexpected IDs exist
    result = await session.execute(
        text("SELECT id FROM tenants WHERE id IN (:ta, :tb)"),
        {"ta": TENANT_A_ID, "tb": TENANT_B_ID},
    )
    if result.fetchall():
        raise Exception("Synthetic tenants already exist before insertion. Aborting.")

    result = await session.execute(
        text("SELECT id FROM users WHERE id IN (:ua1, :ua2, :ub1)"),
        {"ua1": USER_A_ADMIN_ID, "ua2": USER_A_REC_ID, "ub1": USER_B_ADMIN_ID},
    )
    if result.fetchall():
        raise Exception("Synthetic users already exist before insertion. Aborting.")

    result = await session.execute(
        text("SELECT id FROM ai_usage_logs WHERE tenant_id IN (:ta, :tb) LIMIT 1"),
        {"ta": TENANT_A_ID, "tb": TENANT_B_ID},
    )
    if result.fetchall():
        raise Exception("Synthetic ai_usage_logs already exist before insertion. Aborting.")

    # Create Tenants
    await session.execute(
        text("""
        INSERT INTO tenants (id, name, slug, plan, is_active, created_at, updated_at)
        VALUES
        (:ta, 'Val Tenant A', 'val-tenant-a-14', 'enterprise', true, :now, :now),
        (:tb, 'Val Tenant B', 'val-tenant-b-14', 'enterprise', true, :now, :now)
    """),
        {"ta": TENANT_A_ID, "tb": TENANT_B_ID, "now": now},
    )

    # Create Users
    await session.execute(
        text("""
        INSERT INTO users (id, tenant_id, email, full_name, role, password_hash, is_active, created_at, updated_at)
        VALUES
        (:ua1, :ta, 'admin-a-val14@example.com', 'Admin A', 'org_admin', :pw, true, :now, :now),
        (:ua2, :ta, 'rec-a-val14@example.com', 'Rec A', 'recruiter', :pw, true, :now, :now),
        (:ub1, :tb, 'admin-b-val14@example.com', 'Admin B', 'org_admin', :pw, true, :now, :now)
    """),
        {
            "ua1": USER_A_ADMIN_ID,
            "ua2": USER_A_REC_ID,
            "ub1": USER_B_ADMIN_ID,
            "ta": TENANT_A_ID,
            "tb": TENANT_B_ID,
            "pw": hashed_password,
            "now": now,
        },
    )

    # Create AI Usage Logs
    logs = [
        # Tenant A - Record 1 (now - 2 days)
        {
            "t": TENANT_A_ID,
            "op": "generate_candidate_score",
            "dt": now - timedelta(days=2),
            "in_t": 1000,
            "out_t": 200,
            "tot_t": 1200,
            "cost": 0.135,
            "lat": 1500,
            "hit": False,
            "stat": "success",
        },
        # Tenant A - Record 2 (now - 10 days)
        {
            "t": TENANT_A_ID,
            "op": "semantic_search",
            "dt": now - timedelta(days=10),
            "in_t": 50,
            "out_t": 0,
            "tot_t": 50,
            "cost": 0.000001,
            "lat": 100,
            "hit": False,
            "stat": "success",
        },
        # Tenant A - Record 3 (now - 40 days)
        {
            "t": TENANT_A_ID,
            "op": "generate_candidate_embedding",
            "dt": now - timedelta(days=40),
            "in_t": 0,
            "out_t": 0,
            "tot_t": 0,
            "cost": 0,
            "lat": 0,
            "hit": True,
            "stat": "success",
        },
        # Tenant A - Record 4 (now - 100 days)
        {
            "t": TENANT_A_ID,
            "op": "resume_parsing",
            "dt": now - timedelta(days=100),
            "in_t": 2000,
            "out_t": 500,
            "tot_t": 2500,
            "cost": 0.30,
            "lat": 4000,
            "hit": False,
            "stat": "success",
        },
        # Tenant B - Record 5 (now - 1 day)
        {
            "t": TENANT_B_ID,
            "op": "generate_candidate_score",
            "dt": now - timedelta(days=1),
            "in_t": 1000,
            "out_t": 0,
            "tot_t": 1000,
            "cost": 0.10,
            "lat": 1000,
            "hit": False,
            "stat": "success",
        },
    ]

    for log in logs:
        await session.execute(
            text("""
            INSERT INTO ai_usage_logs (tenant_id, operation, model_version, input_tokens, output_tokens, total_tokens, cost_usd, latency_ms, status, is_cache_hit, created_at)
            VALUES (:t, :op, 'val-model', :in_t, :out_t, :tot_t, :cost, :lat, :stat, :hit, :dt)
        """),
            log,
        )

    await session.commit()
    print("Synthetic data inserted.")

async def login(client, email, password, tenant_id):
    resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"email": email, "password": password, "tenant_id": tenant_id},
    )
    if resp.status_code != 200:
        raise ValidationError(f"Login failed for {email}: {resp.text}")
    return resp.json()["data"]["accessToken"]

async def validate_api(now: datetime):
    print("Validating API...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Authenticate
        token_a_admin = await login(client, "admin-a-val14@example.com", SYNTHETIC_PASSWORD, TENANT_A_ID)
        token_a_rec = await login(client, "rec-a-val14@example.com", SYNTHETIC_PASSWORD, TENANT_A_ID)
        token_b_admin = await login(client, "admin-b-val14@example.com", SYNTHETIC_PASSWORD, TENANT_B_ID)

        headers_a_admin = {"Authorization": f"Bearer {token_a_admin}"}
        headers_a_rec = {"Authorization": f"Bearer {token_a_rec}"}
        headers_b_admin = {"Authorization": f"Bearer {token_b_admin}"}

        # 1. 30d Summary for Tenant A
        t0 = time.time()
        resp = await client.get(f"{API_BASE}/ai-usage/summary?period=30d", headers=headers_a_admin)
        if resp.status_code != 200:
            raise ValidationError(f"Failed 30d summary: {resp.text}")
        data = resp.json()["data"]
        latency = (time.time() - t0) * 1000
        print(f"  Summary endpoint latency: {latency:.2f}ms")

        expect_near("30d totalCostUsd", data["totalCostUsd"], 0.14)
        expect_eq("30d totalTokens", data["totalTokens"], 1250)
        expect_eq("30d totalOperations", data["totalOperations"], 2)
        expect_near("30d cacheHitRate", data["cacheHitRate"], 0.0)

        # 1.1 30d Daily Trend Validation
        by_day = data["byDay"]
        day_minus_2 = (now - timedelta(days=2)).strftime("%Y-%m-%d")
        day_minus_10 = (now - timedelta(days=10)).strftime("%Y-%m-%d")

        day2_data = next((d for d in by_day if d["date"] == day_minus_2), None)
        if not day2_data:
            raise ValidationError(f"Missing day -2 data ({day_minus_2}) in byDay")
        expect_near("day -2 costUsd", day2_data["costUsd"], 0.14)
        expect_eq("day -2 operations", day2_data["operations"], 1)

        day10_data = next((d for d in by_day if d["date"] == day_minus_10), None)
        if not day10_data:
            raise ValidationError(f"Missing day -10 data ({day_minus_10}) in byDay")
        expect_near("day -10 costUsd", day10_data["costUsd"], 0.0)
        expect_eq("day -10 operations", day10_data["operations"], 1)

        # 1.2 30d Operation Breakdown Validation
        by_op = data["byOperation"]
        score_op = next((op for op in by_op if op["operation"] == "generate_candidate_score"), None)
        if not score_op:
            raise ValidationError("Missing generate_candidate_score in byOperation")
        expect_eq("score_op count", score_op["count"], 1)
        expect_near("score_op costUsd", score_op["costUsd"], 0.1350)
        expect_eq("score_op avgLatencyMs", score_op["avgLatencyMs"], 1500)

        search_op = next((op for op in by_op if op["operation"] == "semantic_search"), None)
        if not search_op:
            raise ValidationError("Missing semantic_search in byOperation")
        expect_eq("search_op count", search_op["count"], 1)
        expect_near("search_op costUsd", search_op["costUsd"], 0.0)
        expect_eq("search_op avgLatencyMs", search_op["avgLatencyMs"], 100)

        # 2. 90d Summary for Tenant A
        resp = await client.get(f"{API_BASE}/ai-usage/summary?period=90d", headers=headers_a_admin)
        if resp.status_code != 200:
            raise ValidationError("Failed 90d summary")
        data = resp.json()["data"]
        expect_near("90d totalCostUsd", data["totalCostUsd"], 0.14)
        expect_eq("90d totalTokens", data["totalTokens"], 1250)
        expect_eq("90d totalOperations", data["totalOperations"], 3)
        expect_near("90d cacheHitRate", data["cacheHitRate"], 0.3333)

        # 3. 365d (Invalid)
        resp = await client.get(f"{API_BASE}/ai-usage/summary?period=365d", headers=headers_a_admin)
        expect_eq("365d status_code", resp.status_code, 422)

        # 4. Logs filtering for Tenant A
        t0 = time.time()
        resp = await client.get(
            f"{API_BASE}/ai-usage/logs?operation=semantic_search", headers=headers_a_admin
        )
        if resp.status_code != 200:
            raise ValidationError("Failed logs search")
        data = resp.json()["data"]
        latency = (time.time() - t0) * 1000
        print(f"  Logs endpoint latency: {latency:.2f}ms")
        expect_eq("logs count", len(data), 1)
        expect_eq("logs operation", data[0]["operation"], "semantic_search")

        # 5. Pagination
        resp = await client.get(f"{API_BASE}/ai-usage/logs?limit=1", headers=headers_a_admin)
        page = resp.json()
        expect_eq("pagination count", len(page["data"]), 1)
        expect_eq("pagination has_more", page["pagination"]["hasMore"], True)
        if page["pagination"]["nextCursor"] is None:
            raise ValidationError("Expected pagination nextCursor to not be None")

        # 6. Recruiter Denial
        resp = await client.get(f"{API_BASE}/ai-usage/summary?period=30d", headers=headers_a_rec)
        expect_eq("recruiter status_code", resp.status_code, 403)

        # 7. Tenant Isolation (Tenant B)
        resp = await client.get(f"{API_BASE}/ai-usage/summary?period=30d", headers=headers_b_admin)
        data = resp.json()["data"]
        expect_eq("tenant B totalOperations", data["totalOperations"], 1)

        resp = await client.get(f"{API_BASE}/ai-usage/logs", headers=headers_b_admin)
        data = resp.json()["data"]
        expect_eq("tenant B logs count", len(data), 1)
        expect_eq("tenant B logs operation", data[0]["operation"], "generate_candidate_score")

    print("API Validation Passed.")


async def main():
    await verify_safety()
    validation_error = None
    cleanup_success = False

    now = datetime.now(UTC)

    try:
        async with AsyncSessionLocal() as session:
            await insert_synthetic_data(session, now)
        await validate_api(now)
    except Exception as e:
        validation_error = e
        print(f"\nVALIDATION FAILED: {e}")
    finally:
        cleanup_success = await cleanup_data()
        print("\nFrontend validation is intentionally separate and requires a dedicated hardened Playwright production validator.")
        print("\nNOT EXECUTED AGAINST PRODUCTION")

    if validation_error is None and cleanup_success:
        print("\nPASS — validation and cleanup succeeded")
        sys.exit(0)
    elif validation_error is not None and cleanup_success:
        print("\nFAIL — validation failed; cleanup succeeded")
        sys.exit(1)
    elif validation_error is None and not cleanup_success:
        print("\nCRITICAL FAILURE — cleanup verification failed")
        sys.exit(2)
    else:
        print("\nCRITICAL FAILURE — cleanup verification failed")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
