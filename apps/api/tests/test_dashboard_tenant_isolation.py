"""Multi-Tenant Isolation E2E test verifying zero cross-tenant data leakage for Dashboard API."""

import os
import uuid
import pytest
import psycopg
from httpx import ASGITransport, AsyncClient

from hiron.core.jwt import create_access_token
from hiron.main import app


def query_db(query: str) -> str:
    """Helper to provision test data using native psycopg connection."""
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://hiron_user:hiron_secure_password@localhost:5432/hiron_dev"
    ).replace("+asyncpg", "")
    with psycopg.connect(db_url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(query)
        if query.strip().upper().startswith("SELECT"):
            result = cur.fetchone()
            return str(result[0]) if result else ""
        return ""


@pytest.mark.asyncio
async def test_dashboard_tenant_isolation_zero_cross_tenant_leakage() -> None:
    """Verify Tenant B cannot access Tenant A metrics and activity."""
    # 1. Provision Tenant A and Tenant B
    tenant_a_id = str(uuid.uuid4())
    tenant_b_id = str(uuid.uuid4())
    query_db(
        f"INSERT INTO tenants (id, name, slug, created_at, updated_at) VALUES ('{tenant_a_id}', 'Tenant A Isolation', 't-a-{tenant_a_id[:6]}', NOW(), NOW());"
    )
    query_db(
        f"INSERT INTO tenants (id, name, slug, created_at, updated_at) VALUES ('{tenant_b_id}', 'Tenant B Isolation', 't-b-{tenant_b_id[:6]}', NOW(), NOW());"
    )

    # Get a valid password hash from an existing user to use for test users
    raw_pwd_hash = query_db(
        "SELECT password_hash FROM users WHERE email = 'admin@acme.com' LIMIT 1;"
    )
    pwd_hash = raw_pwd_hash.replace("'", "''").replace("$", "\\$")

    # 2. Provision Users
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    user_a_email = f"user_a_{user_a_id[:6]}@example.com"
    user_b_email = f"user_b_{user_b_id[:6]}@example.com"

    query_db(
        f"INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_email_verified, created_at, updated_at) VALUES ('{user_a_id}', '{tenant_a_id}', '{user_a_email}', '{pwd_hash}', 'User A', 'org_admin', true, true, NOW(), NOW());"
    )
    query_db(
        f"INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_email_verified, created_at, updated_at) VALUES ('{user_b_id}', '{tenant_b_id}', '{user_b_email}', '{pwd_hash}', 'User B', 'org_admin', true, true, NOW(), NOW());"
    )

    # 3. Create dashboard-relevant data belonging to Tenant A
    job_a_id = str(uuid.uuid4())
    candidate_a_id = str(uuid.uuid4())
    stage_id = str(uuid.uuid4())

    query_db(
        f"INSERT INTO jobs (id, tenant_id, title, description, status, created_by, created_at, updated_at) VALUES ('{job_a_id}', '{tenant_a_id}', 'Tenant A Top Secret Job', 'Test', 'open', '{user_a_id}', NOW(), NOW());"
    )
    query_db(
        f"INSERT INTO candidates (id, tenant_id, full_name, email, created_at, updated_at) VALUES ('{candidate_a_id}', '{tenant_a_id}', 'Candidate A Secret', 'canda_{candidate_a_id[:6]}@example.com', NOW(), NOW());"
    )
    query_db(
        f"INSERT INTO pipeline_stages (id, tenant_id, job_id, name, position) VALUES ('{stage_id}', '{tenant_a_id}', '{job_a_id}', 'Applied', 1);"
    )
    query_db(
        f"INSERT INTO job_candidates (id, tenant_id, job_id, candidate_id, current_stage_id) VALUES (gen_random_uuid(), '{tenant_a_id}', '{job_a_id}', '{candidate_a_id}', '{stage_id}');"
    )
    query_db(
        f"INSERT INTO scores (id, tenant_id, job_candidate_id, fit_score, confidence, breakdown, explanation, prompt_name, prompt_version, model_version, is_current) SELECT gen_random_uuid(), '{tenant_a_id}', id, 90, 0.9, '{{}}'::jsonb, 'Test', 'test', 'v1', 'gpt-4', true FROM job_candidates WHERE candidate_id = '{candidate_a_id}';"
    )
    query_db(
        f"INSERT INTO audit_logs (id, tenant_id, actor_id, action, entity_type, entity_id, created_at) VALUES (gen_random_uuid(), '{tenant_a_id}', '{user_a_id}', 'create', 'job', '{job_a_id}', NOW());"
    )

    # 4. Authenticate as Tenant B
    token_b = create_access_token(
        user_id=user_b_id,
        tenant_id=tenant_b_id,
        role="org_admin",
        email=user_b_email,
    )

    # 5. Call the real dashboard HTTP endpoint as Tenant B
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {token_b}"}
        )

    assert response.status_code == 200
    data = response.json()["data"]

    # 6. Verify Tenant B receives ONLY Tenant B metrics/activity
    # Tenant B has no jobs or candidates, so metrics should be 0
    assert data["metrics"]["openJobsCount"] == 0, (
        "Cross-tenant leak: Tenant B sees Tenant A job counts"
    )
    assert data["metrics"]["totalCandidatesCount"] == 0, (
        "Cross-tenant leak: Tenant B sees Tenant A candidates"
    )
    assert data["metrics"]["scoredCandidatesCount"] == 0
    assert data["metrics"]["hiredCandidatesCount"] == 0
    assert len(data["pipelineOverview"]) == 0
    assert data["scoreDistribution"]["totalScored"] == 0
    assert len(data["recentActivity"]) == 0

    # Verify Tenant A can see its own data (ensure the data was actually created properly)
    token_a = create_access_token(
        user_id=user_a_id,
        tenant_id=tenant_a_id,
        role="org_admin",
        email=user_a_email,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response_a = await client.get(
            "/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {token_a}"}
        )

    assert response_a.status_code == 200
    data_a = response_a.json()["data"]
    assert data_a["metrics"]["openJobsCount"] == 1
    assert data_a["metrics"]["totalCandidatesCount"] == 1

    # Targeted cleanup
    query_db(f"DELETE FROM audit_logs WHERE tenant_id IN ('{tenant_a_id}', '{tenant_b_id}')")
    query_db(f"DELETE FROM scores WHERE tenant_id IN ('{tenant_a_id}', '{tenant_b_id}')")
    query_db(f"DELETE FROM job_candidates WHERE tenant_id IN ('{tenant_a_id}', '{tenant_b_id}')")
    query_db(f"DELETE FROM pipeline_stages WHERE tenant_id IN ('{tenant_a_id}', '{tenant_b_id}')")
    query_db(f"DELETE FROM candidates WHERE tenant_id IN ('{tenant_a_id}', '{tenant_b_id}')")
    query_db(f"DELETE FROM jobs WHERE tenant_id IN ('{tenant_a_id}', '{tenant_b_id}')")
    query_db(f"DELETE FROM users WHERE tenant_id IN ('{tenant_a_id}', '{tenant_b_id}')")
    query_db(f"DELETE FROM tenants WHERE id IN ('{tenant_a_id}', '{tenant_b_id}')")
