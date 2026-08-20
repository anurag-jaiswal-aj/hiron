"""Integration tests to verify candidate persistence across request boundaries against a real database."""

import os
import subprocess
import uuid

import pytest
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")


@pytest.fixture(scope="module")
def auth_tokens() -> tuple[str, str, str]:
    """Logs in and returns a tuple of (token, tenant_id, tenant_2_token)."""

    try:
        # Dynamically fetch the tenant ID from the running database container
        tenant_id = (
            subprocess.check_output(
                [
                    "docker",
                    "exec",
                    "hiron-postgres",
                    "psql",
                    "-U",
                    "hiron_user",
                    "-d",
                    "hiron_dev",
                    "-t",
                    "-c",
                    "SELECT id FROM tenants LIMIT 1;",
                ]  # noqa: S607
            )
            .decode()
            .strip()
        )
    except Exception as e:
        pytest.skip(f"Failed to fetch tenant ID from database: {e}")

    # Tenant 1 Login
    login_data = {
        "email": "admin@acme.com",
        "password": "SecurePassword123!",
        "tenant_id": tenant_id,
    }

    # We don't have a second tenant seeded by default in seed.py,
    # but the test can still verify basic login. If seed creates multiple tenants, we'll use it.
    try:
        response = requests.post(f"{API_URL}/auth/login", json=login_data, timeout=15)
        if response.status_code != 200:
            pytest.skip(f"Test database not seeded or server down. Status: {response.status_code}")

        token = response.json()["data"]["accessToken"]
        tenant_id = login_data["tenant_id"]

        # Create Tenant B and an admin user for Tenant B via psql
        tenant_b_id = str(uuid.uuid4())
        user_b_id = str(uuid.uuid4())
        email_b = f"admin_b_{str(uuid.uuid4())[:6]}@acme.com"

        insert_sql = f"""
        INSERT INTO tenants (id, name, slug, created_at, updated_at) VALUES ('{tenant_b_id}', 'Tenant B', 'tenant-b-{tenant_b_id[:8]}', NOW(), NOW());
        INSERT INTO users (id, email, password_hash, full_name, tenant_id, role, created_at, updated_at)
        VALUES ('{user_b_id}', '{email_b}', '$argon2id$v=19$m=65536,t=3,p=4$UGWvDbS9C2rEGsUtIVIvRQ$j++SovLzPKuZhxWY6L4rovdEgCEPwnPVDha18Cnhxik', 'Admin B', '{tenant_b_id}', 'org_admin', NOW(), NOW());
        """  # noqa: S608
        subprocess.check_call(  # noqa: S603
            [
                "docker",
                "exec",
                "hiron-postgres",
                "psql",
                "-U",
                "hiron_user",
                "-d",
                "hiron_dev",
                "-c",
                insert_sql,
            ]  # noqa: S607
        )

        # Login to Tenant B
        login_b_data = {
            "email": email_b,
            "password": "SecurePassword123!",
            "tenant_id": tenant_b_id,
        }
        resp_b = requests.post(f"{API_URL}/auth/login", json=login_b_data, timeout=15)
        assert resp_b.status_code == 200, f"Login B failed: {resp_b.text}"
        token_b = resp_b.json()["data"]["accessToken"]

        return token, tenant_id, token_b
    except requests.exceptions.ConnectionError:
        pytest.skip(f"API server at {API_URL} is not reachable.")


def test_candidate_persistence_across_requests(auth_tokens: tuple[str, str, str]) -> None:
    token, _tenant_id, _ = auth_tokens
    headers = {"Authorization": f"Bearer {token}"}

    unique_suffix = str(uuid.uuid4())[:8]
    email = f"test_{unique_suffix}@example.com"
    full_name = f"Persistence Test Candidate {unique_suffix}"

    # TEST 1 - CREATE PERSISTENCE
    create_resp = requests.post(
        f"{API_URL}/candidates",
        json={
            "fullName": full_name,
            "email": email,
            "phone": "555-1234",
            "skills": ["Python", "Docker"],
            "totalExperienceYears": 5,
        },
        headers=headers,
        timeout=15,
    )
    assert create_resp.status_code == 201, f"Create failed: {create_resp.text}"
    created_data = create_resp.json()["data"]
    candidate_id = created_data["id"]

    # Verify via separate GET
    get_resp = requests.get(f"{API_URL}/candidates/{candidate_id}", headers=headers, timeout=15)
    assert get_resp.status_code == 200, "Candidate was not found (Transaction rollback bug?)"
    assert get_resp.json()["data"]["fullName"] == full_name

    # TEST 2 - UPDATE PERSISTENCE
    patch_resp = requests.patch(
        f"{API_URL}/candidates/{candidate_id}",
        json={"fullName": f"{full_name} UPDATED"},
        headers=headers,
        timeout=5,
    )
    assert patch_resp.status_code == 200

    get_patch_resp = requests.get(
        f"{API_URL}/candidates/{candidate_id}", headers=headers, timeout=5
    )
    assert get_patch_resp.json()["data"]["fullName"] == f"{full_name} UPDATED"

    # TEST 4 & 5 - CANDIDATE -> JOB ASSOCIATION PERSISTENCE & INITIAL PIPELINE STAGE
    # Create a job first
    job_resp = requests.post(
        f"{API_URL}/jobs",
        json={
            "title": f"Test Job {unique_suffix}",
            "description": "Test Job Description",
            "department": "Engineering",
            "requiredSkills": ["Python"],
            "employmentType": "full_time",
        },
        headers=headers,
        timeout=5,
    )
    assert job_resp.status_code == 201, f"Job creation failed: {job_resp.text}"
    job_id = job_resp.json()["data"]["id"]

    # Add candidate to job
    add_resp = requests.post(
        f"{API_URL}/jobs/{job_id}/candidates",
        json={"candidateId": candidate_id},
        headers=headers,
        timeout=5,
    )
    assert add_resp.status_code == 201, f"Add to job failed: {add_resp.text}"
    job_candidate_data = add_resp.json()["data"]
    current_stage_id = job_candidate_data["currentStage"]["id"]

    # Get the job details to verify the first pipeline stage ID matches the assigned one
    get_job_resp = requests.get(f"{API_URL}/jobs/{job_id}", headers=headers, timeout=5)
    pipeline_stages = get_job_resp.json()["data"]["pipelineStages"]
    first_stage = min(pipeline_stages, key=lambda s: s["position"])
    assert current_stage_id == first_stage["id"], (
        "Candidate was not placed in the first pipeline stage"
    )

    # Verify association persists by fetching candidate details (should include jobs)
    get_assoc_resp = requests.get(
        f"{API_URL}/candidates/{candidate_id}", headers=headers, timeout=5
    )
    jobs_associated = get_assoc_resp.json()["data"].get("jobs", [])
    assert any(j["jobId"] == job_id for j in jobs_associated), (
        f"Job association did not persist across requests. Got: {jobs_associated}"
    )

    # TEST 6 - DUPLICATE EMAIL
    duplicate_resp = requests.post(
        f"{API_URL}/candidates",
        json={
            "fullName": "Duplicate Tester",
            "email": email,  # Exact same email
        },
        headers=headers,
        timeout=5,
    )
    assert duplicate_resp.status_code == 409, (
        "Duplicate email in same tenant should return 409 Conflict"
    )

    # TEST 3 - ARCHIVE PERSISTENCE
    archive_resp = requests.post(
        f"{API_URL}/candidates/{candidate_id}/archive", headers=headers, timeout=5
    )
    assert archive_resp.status_code == 200

    get_archive_resp = requests.get(
        f"{API_URL}/candidates/{candidate_id}", headers=headers, timeout=5
    )
    assert get_archive_resp.json()["data"]["isArchived"] is True

    # Verify archived candidates are excluded from default list view
    list_resp = requests.get(f"{API_URL}/candidates", headers=headers, timeout=5)
    assert list_resp.status_code == 200
    listed_candidates = list_resp.json()["data"]["data"]
    assert all(c["id"] != candidate_id for c in listed_candidates), (
        "Archived candidate appeared in default list view"
    )

    # TEST - SKILL FILTER REGRESSION
    # We create a new candidate with specific skills to avoid clashes
    skill_suffix = str(uuid.uuid4())[:8]
    requests.post(
        f"{API_URL}/candidates",
        json={
            "fullName": "Python Developer",
            "email": f"py_{skill_suffix}@example.com",
            "skills": ["Python", "FastAPI"],
        },
        headers=headers,
        timeout=5,
    )

    # Filter by exact match
    skill_resp = requests.get(f"{API_URL}/candidates?skills=Python", headers=headers, timeout=5)
    assert skill_resp.status_code == 200, "Skill filter API returned error"
    skill_cands = skill_resp.json()["data"]["data"]
    assert any(c["email"] == f"py_{skill_suffix}@example.com" for c in skill_cands), (
        "Skill filter did not return the expected candidate"
    )

    # Filter by no-match
    no_skill_resp = requests.get(f"{API_URL}/candidates?skills=Rust", headers=headers, timeout=5)
    assert no_skill_resp.status_code == 200
    no_skill_cands = no_skill_resp.json()["data"]["data"]
    assert not any(c["email"] == f"py_{skill_suffix}@example.com" for c in no_skill_cands), (
        "Skill filter returned candidate without the requested skill"
    )

    # TEST - FULL TEXT SEARCH
    search_resp = requests.get(
        f"{API_URL}/candidates?q={unique_suffix}", headers=headers, timeout=5
    )
    assert search_resp.status_code == 200
    # Search finds by name/email/skills, our name has unique_suffix
    # But it is archived! So we must include archived or search another candidate
    # The python dev has skill_suffix.
    search2_resp = requests.get(
        f"{API_URL}/candidates?q=Python Developer", headers=headers, timeout=5
    )
    search2_cands = search2_resp.json()["data"]["data"]
    assert any(c["email"] == f"py_{skill_suffix}@example.com" for c in search2_cands), (
        "Full-text search did not find candidate"
    )

    # TEST 7 - CROSS-TENANT SAFETY
    token_b = auth_tokens[2]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant B attempts to GET Candidate A
    get_b_resp = requests.get(f"{API_URL}/candidates/{candidate_id}", headers=headers_b, timeout=5)
    assert get_b_resp.status_code == 404, "Tenant B could retrieve Tenant A's candidate"

    # Tenant B attempts to PATCH Candidate A
    patch_b_resp = requests.patch(
        f"{API_URL}/candidates/{candidate_id}",
        json={"fullName": "Hacked"},
        headers=headers_b,
        timeout=5,
    )
    assert patch_b_resp.status_code == 404, "Tenant B could update Tenant A's candidate"

    # Tenant B attempts to Archive Candidate A
    archive_b_resp = requests.post(
        f"{API_URL}/candidates/{candidate_id}/archive", headers=headers_b, timeout=5
    )
    assert archive_b_resp.status_code == 404, "Tenant B could archive Tenant A's candidate"

    # Tenant B attempts to add Candidate A to Job B
    job_b_resp = requests.post(
        f"{API_URL}/jobs",
        json={
            "title": "Job B",
            "description": "Job B Description",
            "department": "Eng",
            "employmentType": "full_time",
        },
        headers=headers_b,
        timeout=5,
    )
    assert job_b_resp.status_code == 201, f"Job B creation failed: {job_b_resp.text}"
    job_b_id = job_b_resp.json()["data"]["id"]
    assoc_b_resp = requests.post(
        f"{API_URL}/jobs/{job_b_id}/candidates",
        json={"candidateId": candidate_id},
        headers=headers_b,
        timeout=5,
    )
    assert assoc_b_resp.status_code == 404, (
        "Tenant B could associate Tenant A's candidate with Job B"
    )

    # Verify Candidate A is unchanged by checking via Tenant A
    verify_a_resp = requests.get(f"{API_URL}/candidates/{candidate_id}", headers=headers, timeout=5)
    assert verify_a_resp.json()["data"]["fullName"] == f"{full_name} UPDATED"
