"""Integration tests to verify job persistence across request boundaries against a real database."""

import os
import subprocess
import uuid

import pytest
import requests

# We test against the running API server (e.g., http://localhost:8000)
# This proves that requests hitting the actual router are persisted to the database.

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")


@pytest.fixture(scope="module")
def auth_token() -> tuple[str, str]:
    """Logs in and returns a tuple of (token, tenant_id)."""
    try:
        tenant_id = subprocess.check_output(
            ["docker", "exec", "hiron-postgres", "psql", "-U", "hiron_user", "-d", "hiron_dev", "-t", "-c", "SELECT id FROM tenants LIMIT 1;"]  # noqa: S607
        ).decode().strip()
    except Exception as e:
        pytest.skip(f"Failed to fetch tenant ID from database: {e}")

    login_data = {
        "email": "admin@acme.com",
        "password": "SecurePassword123!",
        "tenant_id": tenant_id,
    }

    try:
        response = requests.post(f"{API_URL}/auth/login", json=login_data, timeout=5)
        if response.status_code != 200:
            pytest.skip(f"Test database not seeded or server down. Status: {response.status_code}")

        token = response.json()["data"]["accessToken"]
        return token, login_data["tenant_id"]
    except requests.exceptions.ConnectionError:
        pytest.skip(f"API server at {API_URL} is not reachable.")


def test_job_persistence_across_requests(auth_token: tuple[str, str]) -> None:
    token, _ = auth_token
    headers = {"Authorization": f"Bearer {token}"}

    job_title = f"Persistence Test Job {uuid.uuid4()}"

    # 1. POST job (Request 1 - its own transaction)
    create_resp = requests.post(
        f"{API_URL}/jobs",
        json={
            "title": job_title,
            "description": "This job must persist across transactions.",
            "department": "Engineering",
            "requiredSkills": ["Python", "Testing"],
            "employmentType": "full_time"
        },
        headers=headers,
        timeout=15,
    )
    assert create_resp.status_code == 201, f"Create failed: {create_resp.text}"
    created_data = create_resp.json()["data"]
    job_id = created_data["id"]

    # 2. Issue a separate GET request for the specific job (Request 2)
    get_resp = requests.get(f"{API_URL}/jobs/{job_id}", headers=headers, timeout=15)
    assert get_resp.status_code == 200, "Job was not found in a separate request (Transaction rollback bug?)"
    assert get_resp.json()["data"]["title"] == job_title

    # Check default pipeline stages persisted
    stages = get_resp.json()["data"].get("pipelineStages", [])
    assert len(stages) > 0, "Default pipeline stages were not created/persisted"

    # 3. PATCH persists (Request 3)
    patch_resp = requests.patch(
        f"{API_URL}/jobs/{job_id}",
        json={"title": f"{job_title} UPDATED"},
        headers=headers,
        timeout=5,
    )
    assert patch_resp.status_code == 200

    # Verify PATCH with another GET (Request 4)
    get_patch_resp = requests.get(f"{API_URL}/jobs/{job_id}", headers=headers, timeout=5)
    assert get_patch_resp.json()["data"]["title"] == f"{job_title} UPDATED"

    # 4. Open persists (Request 5)
    open_resp = requests.post(f"{API_URL}/jobs/{job_id}/open", headers=headers, timeout=5)
    assert open_resp.status_code == 200

    get_open_resp = requests.get(f"{API_URL}/jobs/{job_id}", headers=headers, timeout=5)
    assert get_open_resp.json()["data"]["status"] == "open"

    # 5. Close persists (Request 6)
    close_resp = requests.post(f"{API_URL}/jobs/{job_id}/close", headers=headers, timeout=5)
    assert close_resp.status_code == 200

    get_close_resp = requests.get(f"{API_URL}/jobs/{job_id}", headers=headers, timeout=5)
    assert get_close_resp.json()["data"]["status"] == "closed"

    # 6. Archive persists (Request 7)
    archive_resp = requests.post(f"{API_URL}/jobs/{job_id}/archive", headers=headers, timeout=5)
    assert archive_resp.status_code == 200

    get_archive_resp = requests.get(f"{API_URL}/jobs/{job_id}", headers=headers, timeout=5)
    assert get_archive_resp.json()["data"]["status"] == "archived"
    assert get_archive_resp.json()["data"]["isArchived"] is True

    # Verify archived jobs are excluded from default list view
    list_resp = requests.get(f"{API_URL}/jobs", headers=headers, timeout=5)
    assert list_resp.status_code == 200
    listed_jobs = list_resp.json()["data"]["data"]
    assert all(j["id"] != job_id for j in listed_jobs), "Archived job appeared in default list view"
