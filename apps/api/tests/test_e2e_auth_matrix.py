"""Authentication/Authorization E2E Matrix implementation covering real DB scenarios."""

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


from collections.abc import Generator


@pytest.fixture
def auth_matrix_setup() -> Generator[dict[str, str], None, None]:
    """Provisions Tenant A and Tenant B, users, and resources for the attack matrix."""
    tenant_a_id = str(uuid.uuid4())
    tenant_b_id = str(uuid.uuid4())
    query_db(
        f"INSERT INTO tenants (id, name, slug, created_at, updated_at) VALUES ('{tenant_a_id}', 'Tenant A', 't-a-{tenant_a_id[:6]}', NOW(), NOW());"
    )
    query_db(
        f"INSERT INTO tenants (id, name, slug, created_at, updated_at) VALUES ('{tenant_b_id}', 'Tenant B', 't-b-{tenant_b_id[:6]}', NOW(), NOW());"
    )

    # Use a known test password hash for "SecurePassword123!"
    raw_pwd_hash = query_db(
        "SELECT password_hash FROM users WHERE email = 'admin@acme.com' LIMIT 1;"
    )
    pwd_hash = raw_pwd_hash.replace("'", "''")

    # Provision Users
    user_a_admin = str(uuid.uuid4())
    user_b_admin = str(uuid.uuid4())
    user_a_recruiter = str(uuid.uuid4())
    user_b_recruiter = str(uuid.uuid4())

    query_db(
        f"INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_email_verified, created_at, updated_at) VALUES ('{user_a_admin}', '{tenant_a_id}', 'admin@tenant-a.com', '{pwd_hash}', 'Admin A', 'org_admin', true, true, NOW(), NOW());"
    )
    query_db(
        f"INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_email_verified, created_at, updated_at) VALUES ('{user_b_admin}', '{tenant_b_id}', 'admin@tenant-b.com', '{pwd_hash}', 'Admin B', 'org_admin', true, true, NOW(), NOW());"
    )
    query_db(
        f"INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_email_verified, created_at, updated_at) VALUES ('{user_a_recruiter}', '{tenant_a_id}', 'recruiter@tenant-a.com', '{pwd_hash}', 'Recruiter A', 'recruiter', true, true, NOW(), NOW());"
    )
    query_db(
        f"INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_email_verified, created_at, updated_at) VALUES ('{user_b_recruiter}', '{tenant_b_id}', 'recruiter@tenant-b.com', '{pwd_hash}', 'Recruiter B', 'recruiter', true, true, NOW(), NOW());"
    )

    # Provision Tenant A Job
    job_a_id = str(uuid.uuid4())
    query_db(
        f"INSERT INTO jobs (id, tenant_id, title, description, status, created_by, created_at, updated_at) VALUES ('{job_a_id}', '{tenant_a_id}', 'Tenant A Job', 'Test', 'open', '{user_a_admin}', NOW(), NOW());"
    )

    yield {
        "tenant_a_id": tenant_a_id,
        "tenant_b_id": tenant_b_id,
        "user_a_admin": user_a_admin,
        "user_b_admin": user_b_admin,
        "user_a_recruiter": user_a_recruiter,
        "user_b_recruiter": user_b_recruiter,
        "job_a_id": job_a_id,
    }

    # Cleanup
    query_db(
        f"DELETE FROM refresh_tokens WHERE user_id IN ('{user_a_admin}', '{user_b_admin}', '{user_a_recruiter}', '{user_b_recruiter}')"
    )
    query_db(f"DELETE FROM jobs WHERE tenant_id IN ('{tenant_a_id}', '{tenant_b_id}')")
    query_db(f"DELETE FROM users WHERE tenant_id IN ('{tenant_a_id}', '{tenant_b_id}')")
    query_db(f"DELETE FROM tenants WHERE id IN ('{tenant_a_id}', '{tenant_b_id}')")


@pytest.mark.asyncio
async def test_matrix_d_cross_tenant_mutation(auth_matrix_setup: dict[str, str]) -> None:
    """D. Verify Tenant B cannot PATCH/DELETE Tenant A's jobs."""
    setup = auth_matrix_setup

    token_b = create_access_token(
        user_id=uuid.UUID(setup["user_b_admin"]),
        tenant_id=uuid.UUID(setup["tenant_b_id"]),
        role="org_admin",
        email="admin@tenant-b.com",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Attempt PATCH
        patch_res = await client.patch(
            f"/api/v1/jobs/{setup['job_a_id']}",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"title": "Hacked by Tenant B"},
        )
        assert patch_res.status_code == 404, (
            "Cross-tenant PATCH should return 404 to avoid leaking existence"
        )

        # Attempt DELETE (if jobs support DELETE, usually 404)
        del_res = await client.delete(
            f"/api/v1/jobs/{setup['job_a_id']}", headers={"Authorization": f"Bearer {token_b}"}
        )
        # Assuming either 404 or 405 depending on router config, but if endpoint exists, it should be 404
        assert del_res.status_code in [404, 405]

    # Verify job title is unchanged via DB
    title = query_db(f"SELECT title FROM jobs WHERE id = '{setup['job_a_id']}';")
    assert title == "Tenant A Job", "Job was illegally mutated!"


@pytest.mark.asyncio
async def test_matrix_e_rbac_escalation(auth_matrix_setup: dict[str, str]) -> None:
    """E. Verify recruiter cannot perform org_admin operations (e.g. creating/updating users)."""
    setup = auth_matrix_setup

    token_a_recruiter = create_access_token(
        user_id=uuid.UUID(setup["user_a_recruiter"]),
        tenant_id=uuid.UUID(setup["tenant_a_id"]),
        role="recruiter",
        email="recruiter@tenant-a.com",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Attempt to create a user (org_admin only)
        create_res = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token_a_recruiter}"},
            json={
                "email": "hacker@tenant-a.com",
                "fullName": "Hacker",
                "role": "org_admin",
                "password": "Password123!",
            },
        )
        assert create_res.status_code == 403, "Recruiter should be forbidden from creating users"

        # Verify a legitimate recruiter action works (e.g., listing candidates, or reading me)
        me_res = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a_recruiter}"}
        )
        assert me_res.status_code == 200, "Legitimate GET /me should work for recruiter"


@pytest.mark.asyncio
async def test_matrix_f_other_user_boundary(auth_matrix_setup: dict[str, str]) -> None:
    """F. Verify a user cannot modify another user's profile/role."""
    setup = auth_matrix_setup

    token_a_recruiter = create_access_token(
        user_id=uuid.UUID(setup["user_a_recruiter"]),
        tenant_id=uuid.UUID(setup["tenant_a_id"]),
        role="recruiter",
        email="recruiter@tenant-a.com",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Attempt to PATCH the admin user
        patch_res = await client.patch(
            f"/api/v1/users/{setup['user_a_admin']}",
            headers={"Authorization": f"Bearer {token_a_recruiter}"},
            json={"role": "hiring_manager"},
        )
        assert patch_res.status_code == 403, (
            "Recruiter should be forbidden from patching another user"
        )

        # Verify role is unchanged
        role = query_db(f"SELECT role FROM users WHERE id = '{setup['user_a_admin']}';")
        assert role == "org_admin"


@pytest.mark.asyncio
async def test_matrix_gh_refresh_replay_and_logout(auth_matrix_setup: dict[str, str]) -> None:
    """G & H. Verify refresh token replay is blocked and logout works via real DB tokens."""
    setup = auth_matrix_setup

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@tenant-a.com",
                "password": "SecurePassword123!",
                "tenantId": setup["tenant_a_id"],
            },
        )
        assert login_res.status_code == 200
        refresh_token_cookie = login_res.cookies.get("refreshToken")
        assert refresh_token_cookie is not None

        # Refresh session
        client.cookies.set("refreshToken", refresh_token_cookie)
        refresh_res = await client.post("/api/v1/auth/refresh")
        assert refresh_res.status_code == 200
        new_refresh_token_cookie = refresh_res.cookies.get("refreshToken")
        assert new_refresh_token_cookie is not None
        assert new_refresh_token_cookie != refresh_token_cookie

        # Replay the OLD refresh token (should be rejected/401)
        client.cookies.set("refreshToken", refresh_token_cookie)
        replay_res = await client.post("/api/v1/auth/refresh")
        assert replay_res.status_code == 401, "Replaying a consumed refresh token must fail"

        # Logout using the NEW refresh token
        client.cookies.set("refreshToken", new_refresh_token_cookie)
        logout_res = await client.post("/api/v1/auth/logout")
        assert logout_res.status_code == 204

        # Try refreshing after logout
        after_logout_res = await client.post("/api/v1/auth/refresh")
        assert after_logout_res.status_code == 401, "Refreshing after logout must fail"


@pytest.mark.asyncio
async def test_matrix_i_deactivated_mid_session(auth_matrix_setup: dict[str, str]) -> None:
    """I. Verify that an active JWT is rejected if the user is deactivated in the DB."""
    setup = auth_matrix_setup

    token_a_recruiter = create_access_token(
        user_id=uuid.UUID(setup["user_a_recruiter"]),
        tenant_id=uuid.UUID(setup["tenant_a_id"]),
        role="recruiter",
        email="recruiter@tenant-a.com",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Verify token works initially
        me_res1 = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a_recruiter}"}
        )
        assert me_res1.status_code == 200

        # 2. Deactivate the user directly in DB
        query_db(f"UPDATE users SET is_active = false WHERE id = '{setup['user_a_recruiter']}';")

        # 3. Verify token is now rejected
        me_res2 = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a_recruiter}"}
        )
        assert me_res2.status_code == 403, "JWT should be rejected if user is deactivated in DB"
        assert me_res2.json()["error"]["code"] == "ACCOUNT_DISABLED"
