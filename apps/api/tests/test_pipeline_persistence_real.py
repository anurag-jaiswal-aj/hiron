"""Integration tests to verify pipeline stage transitions and history across request boundaries against a real database using requests."""

import os
import subprocess
import uuid
import pytest
import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

@pytest.fixture(scope="module")
def auth_setup() -> tuple[str, str, str]:
    """Logs in and returns a tuple of (token, tenant_id, user_id)."""
    try:
        tenant_and_user = subprocess.check_output(
            ["docker", "exec", "hiron-postgres", "psql", "-U", "hiron_user", "-d", "hiron_dev", "-t", "-c", "SELECT tenant_id, id FROM users WHERE email = 'recruiter@acme.com' LIMIT 1;"]  # noqa: S607
        ).decode().strip().split("|")
        tenant_id = tenant_and_user[0].strip()
        user_id = tenant_and_user[1].strip()
    except Exception as e:
        pytest.skip(f"Failed to fetch user from database: {e}")

    try:
        login_resp = requests.post(
            f"{API_URL}/auth/login",
            json={
                "email": "recruiter@acme.com",
                "password": "SecurePassword123!",
                "tenant_id": tenant_id,
            },
            timeout=3,
        )
        if login_resp.status_code == 200:
            token = login_resp.json()["data"]["accessToken"]
        else:
            import datetime
            from hiron.core.jwt import create_access_token
            token = create_access_token(
                user_id=user_id,
                tenant_id=tenant_id,
                email="recruiter@acme.com",
                role="recruiter",
                expires_delta=datetime.timedelta(days=1)
            )
    except requests.exceptions.ConnectionError:
        pytest.skip(f"API server at {API_URL} is not reachable.")

    return token, tenant_id, user_id

def create_job(headers: dict[str, str], title: str) -> str:
    resp = requests.post(
        f"{API_URL}/jobs",
        json={
            "title": title,
            "description": "Integration test job",
            "department": "Engineering",
            "requiredSkills": ["Python"],
            "employmentType": "full_time"
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Failed to create job: {resp.text}"
    return resp.json()["data"]["id"]

def create_candidate_and_apply(headers: dict[str, str], job_id: str) -> tuple[str, str]:
    resp = requests.post(
        f"{API_URL}/candidates",
        json={
            "fullName": f"Jane Doe {uuid.uuid4()}",
            "email": f"jane_{uuid.uuid4()}@example.com",
            "phone": "555-0100",
            "skills": ["Python", "SQL"],
            "totalExperienceYears": 5
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Failed to create candidate: {resp.text}"
    candidate_id = resp.json()["data"]["id"]
    
    apply_resp = requests.post(
        f"{API_URL}/jobs/{job_id}/candidates",
        json={"candidateId": candidate_id},
        headers=headers,
    )
    assert apply_resp.status_code == 201, f"Failed to apply candidate: {apply_resp.text}"
    job_candidate_id = apply_resp.json()["data"]["id"]
    return candidate_id, job_candidate_id

def test_pipeline_integration_flows(auth_setup: tuple[str, str, str]) -> None:
    token, tenant_id, user_id = auth_setup
    headers = {"Authorization": f"Bearer {token}"}
    
    # Setup Data
    job_a_id = create_job(headers, f"Job A {uuid.uuid4()}")
    job_b_id = create_job(headers, f"Job B {uuid.uuid4()}")
    
    cand_id, jc_id = create_candidate_and_apply(headers, job_a_id)
    
    # Fetch stages for Job A
    board_a_resp = requests.get(f"{API_URL}/jobs/{job_a_id}/pipeline", headers=headers)
    assert board_a_resp.status_code == 200
    stages_a = board_a_resp.json()["data"]
    
    applied_stage = next(s for s in stages_a if "applied" in s["stageName"].lower())
    screening_stage = next(s for s in stages_a if "screening" in s["stageName"].lower())
    
    board_b_resp = requests.get(f"{API_URL}/jobs/{job_b_id}/pipeline", headers=headers)
    stages_b = board_b_resp.json()["data"]
    job_b_screening_stage = next(s for s in stages_b if "screening" in s["stageName"].lower())
    
    # ---------------------------------------------------------
    # SCENARIO A: Valid Move (Applied -> Screening)
    # ---------------------------------------------------------
    move_resp = requests.post(
        f"{API_URL}/pipeline/move",
        json={
            "job_candidate_id": jc_id,
            "to_stage_id": screening_stage["stageId"],
            "note": "Initial screening move"
        },
        headers=headers,
    )
    assert move_resp.status_code == 200, move_resp.text
    
    # Verify via Stage History API
    hist_resp = requests.get(f"{API_URL}/jobs/{job_a_id}/candidates/{cand_id}/stage-history", headers=headers)
    assert hist_resp.status_code == 200
    history_items = hist_resp.json()["data"]
    
    try:
        move_item = next(item for item in history_items if item["toStage"]["id"] == screening_stage["stageId"])
    except StopIteration:
        print("FAILED TO FIND MOVE ITEM IN HISTORY:", history_items)
        raise
    assert move_item["fromStage"]["id"] == applied_stage["stageId"]
    assert move_item["movedBy"]["id"] == user_id
    assert move_item["note"] == "Initial screening move"
    assert move_item["createdAt"] is not None
    
    # Check current_stage_id via DB directly to be absolutely certain of persistence
    db_check = subprocess.check_output([
        "docker", "exec", "hiron-postgres", "psql", "-U", "hiron_user", "-d", "hiron_dev", "-t", "-c",
        f"SELECT current_stage_id FROM job_candidates WHERE id = '{jc_id}';"
    ]).decode().strip()
    assert db_check == screening_stage["stageId"]
    
    # ---------------------------------------------------------
    # SCENARIO B: Same-stage Move
    # ---------------------------------------------------------
    same_resp = requests.post(
        f"{API_URL}/pipeline/move",
        json={"job_candidate_id": jc_id, "to_stage_id": screening_stage["stageId"]},
        headers=headers,
    )
    assert same_resp.status_code == 422
    assert "already in the requested" in same_resp.text
    
    hist_resp2 = requests.get(f"{API_URL}/jobs/{job_a_id}/candidates/{cand_id}/stage-history", headers=headers)
    assert len(hist_resp2.json()["data"]) == len(history_items) # No new record
    
    # ---------------------------------------------------------
    # SCENARIO C: Wrong Job Stage
    # ---------------------------------------------------------
    wrong_resp = requests.post(
        f"{API_URL}/pipeline/move",
        json={"job_candidate_id": jc_id, "to_stage_id": job_b_screening_stage["stageId"]},
        headers=headers,
    )
    assert wrong_resp.status_code == 422
    assert "does not belong to candidate's job" in wrong_resp.text
    
    hist_resp3 = requests.get(f"{API_URL}/jobs/{job_a_id}/candidates/{cand_id}/stage-history", headers=headers)
    assert len(hist_resp3.json()["data"]) == len(history_items) # No new record
    
    # ---------------------------------------------------------
    # SCENARIO D: Cross Tenant Stage
    # ---------------------------------------------------------
    random_resp = requests.post(
        f"{API_URL}/pipeline/move",
        json={"job_candidate_id": jc_id, "to_stage_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert random_resp.status_code == 404
    
    # ---------------------------------------------------------
    # SCENARIO E: Shortlist Candidate
    # ---------------------------------------------------------
    shortlist_resp = requests.post(
        f"{API_URL}/jobs/{job_a_id}/candidates/{cand_id}/shortlist",
        headers=headers
    )
    assert shortlist_resp.status_code == 200
    assert shortlist_resp.json()["data"]["isShortlisted"] is True
    
    db_shortlist_check = subprocess.check_output([
        "docker", "exec", "hiron-postgres", "psql", "-U", "hiron_user", "-d", "hiron_dev", "-t", "-c",
        f"SELECT is_shortlisted FROM job_candidates WHERE id = '{jc_id}';"
    ]).decode().strip()
    assert db_shortlist_check == "t"
    
    # ---------------------------------------------------------
    # SCENARIO F: Reject Workflow
    # ---------------------------------------------------------
    reject_reason = "Lacks required experience"
    reject_resp = requests.post(
        f"{API_URL}/jobs/{job_a_id}/candidates/{cand_id}/reject",
        json={"reason": reject_reason},
        headers=headers,
    )
    assert reject_resp.status_code == 200, reject_resp.text
    assert reject_resp.json()["data"]["status"] == "rejected"
    assert reject_resp.json()["data"]["rejectionReason"] == reject_reason
    
    hist_resp_final = requests.get(f"{API_URL}/jobs/{job_a_id}/candidates/{cand_id}/stage-history", headers=headers)
    history_items_final = hist_resp_final.json()["data"]
    
    reject_item = history_items_final[-1]
    assert "Rejected" in reject_item["toStage"]["name"] or "Disqualified" in reject_item["toStage"]["name"]
    assert reject_item["fromStage"]["id"] == screening_stage["stageId"]
    assert reject_reason in reject_item["note"]
    
    db_status_check = subprocess.check_output([
        "docker", "exec", "hiron-postgres", "psql", "-U", "hiron_user", "-d", "hiron_dev", "-t", "-c",
        f"SELECT rejection_reason FROM job_candidates WHERE id = '{jc_id}';"
    ]).decode().strip()
    assert reject_reason in db_status_check
