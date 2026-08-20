import asyncio
import json
from pathlib import Path

import httpx

API_BASE = "https://hiron-api.vercel.app/api/v1"


async def login(client: httpx.AsyncClient, email: str, password: str, tenant_id: str):
    resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"email": email, "password": password, "tenant_id": tenant_id},
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return data["accessToken"], data["user"]


async def main():
    with Path(".phase13_prod_data.json").open("r") as f:  # noqa: ASYNC230
        data = json.load(f)

    tenant_a_id = data["tenant_a_id"]
    tenant_b_id = data["tenant_b_id"]
    run_id = data["run_id"]
    password = data["password"]

    print("==================================================")
    print(f"PHASE 13 PROD API VALIDATION (RUN ID: {run_id})")
    print("==================================================")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. AUTHENTICATE
        print("\n1. AUTHENTICATING...")
        token_a_admin, _user_a_admin = await login(
            client, data["admin_a_email"], password, tenant_a_id
        )
        token_a_rec, _user_a_rec = await login(client, data["rec_a_email"], password, tenant_a_id)
        token_b_admin, _user_b_admin = await login(
            client, data["admin_b_email"], password, tenant_b_id
        )
        print("   ✅ Authentication successful")

        def headers(token):
            return {"Authorization": f"Bearer {token}"}

        # 2. MUTATIONS (Tenant A Admin)
        print("\n2. PERFORMING SYNTHETIC MUTATIONS...")
        # Create Job
        job_data = {
            "title": f"Val Job {run_id}",
            "department": "Engineering",
            "location": "Remote",
            "status": "open",
            "description": "Validation testing",
        }
        resp = await client.post(f"{API_BASE}/jobs", json=job_data, headers=headers(token_a_admin))
        resp.raise_for_status()
        job = resp.json()["data"]
        job_id = job["id"]
        print(f"   ✅ Created Job: {job_id}")

        # Update Job (to test before/after)
        resp = await client.patch(
            f"{API_BASE}/jobs/{job_id}",
            json={"department": "Product", "description": "Updated validation testing"},
            headers=headers(token_a_admin),
        )
        resp.raise_for_status()
        print(f"   ✅ Updated Job: {job_id}")

        # Create Candidate
        cand_data = {"full_name": f"Val Cand {run_id}", "email": f"val-cand-{run_id}@example.com"}
        resp = await client.post(
            f"{API_BASE}/candidates", json=cand_data, headers=headers(token_a_admin)
        )
        resp.raise_for_status()
        cand_id = resp.json()["data"]["id"]
        print(f"   ✅ Created Candidate: {cand_id}")

        # Link Candidate to Job
        # Usually pipeline stages are created automatically for a new job. Let's get the stages.
        resp = await client.get(f"{API_BASE}/jobs/{job_id}", headers=headers(token_a_admin))
        stages = resp.json()["data"].get("pipeline_stages", [])
        if stages:
            stage_id = stages[0]["id"]
            resp = await client.post(
                f"{API_BASE}/candidates/{cand_id}/jobs",
                json={"job_id": job_id, "stage_id": stage_id},
                headers=headers(token_a_admin),
            )
            if resp.status_code == 200:
                print("   ✅ Linked Candidate to Job")

        # Create Note (by Recruiter!)
        note_data = {"content": f"Test note by recruiter {run_id}"}
        resp = await client.post(
            f"{API_BASE}/candidates/{cand_id}/notes", json=note_data, headers=headers(token_a_rec)
        )
        if resp.status_code == 200:
            print("   ✅ Created Note (by recruiter)")

        # 3. AUTHORIZATION & TENANT ISOLATION
        print("\n3. TESTING AUTHORIZATION & ISOLATION...")

        # Admin A sees everything
        resp = await client.get(f"{API_BASE}/audit-logs", headers=headers(token_a_admin))
        resp.raise_for_status()
        logs_a_admin = resp.json()["data"]
        assert len(logs_a_admin) > 0, "Admin A sees no logs!"  # noqa: S101 - assertions intentionally enforce validation invariants
        print("   ✅ Admin A can view Tenant A audit logs")

        # Recruiter A sees only own actions
        resp = await client.get(f"{API_BASE}/audit-logs", headers=headers(token_a_rec))
        resp.raise_for_status()
        logs_a_rec = resp.json()["data"]
        # They should see the note creation
        assert all((log.get("actor") or {}).get("id") == data["rec_a_id"] for log in logs_a_rec), (  # noqa: S101 - assertions intentionally enforce validation invariants
            "Recruiter sees other actions!"
        )
        print("   ✅ Recruiter A only sees own actions")

        # Admin B sees nothing from A
        resp = await client.get(f"{API_BASE}/audit-logs", headers=headers(token_b_admin))
        resp.raise_for_status()
        logs_b = resp.json()["data"]
        assert len(logs_b) == 0, "Admin B sees Tenant A logs!"  # noqa: S101 - assertions intentionally enforce validation invariants
        print("   ✅ Admin B isolated from Tenant A logs")

        # 4. FILTERS & PAGINATION
        print("\n4. TESTING FILTERS...")
        # valid filter zero results
        resp = await client.get(
            f"{API_BASE}/audit-logs?entityType=score", headers=headers(token_a_admin)
        )
        assert len(resp.json()["data"]) == 0  # noqa: S101 - assertions intentionally enforce validation invariants
        print("   ✅ Valid filter with zero results verified")

        # invalid UUID format
        resp = await client.get(
            f"{API_BASE}/audit-logs?actorId=not-a-uuid", headers=headers(token_a_admin)
        )
        assert resp.status_code in [400, 422], "Invalid UUID did not return 4xx"  # noqa: S101 - assertions intentionally enforce validation invariants
        print("   ✅ Invalid UUID rejected correctly")

        # 5. BEFORE / AFTER VERIFICATION
        print("\n5. VERIFYING BEFORE / AFTER PAYLOADS...")
        job_update_log = next(
            (log_entry for log_entry in logs_a_admin if log_entry["action"] == "job_updated"), None
        )
        assert job_update_log is not None, "Could not find job update log"  # noqa: S101 - assertions intentionally enforce validation invariants
        changes = job_update_log.get("changes", {})
        assert "before" in changes, "Missing before in changes"  # noqa: S101 - assertions intentionally enforce validation invariants
        assert "after" in changes, "Missing after in changes"  # noqa: S101 - assertions intentionally enforce validation invariants
        assert changes["before"].get("department") == "Engineering"  # noqa: S101 - assertions intentionally enforce validation invariants
        assert changes["after"].get("department") == "Product"  # noqa: S101 - assertions intentionally enforce validation invariants
        print("   ✅ before/after transition recorded correctly")

        # 6. IMMUTABILITY
        print("\n6. TESTING IMMUTABILITY...")
        log_id = logs_a_admin[0]["id"]
        r1 = await client.delete(f"{API_BASE}/audit-logs/{log_id}", headers=headers(token_a_admin))
        r2 = await client.put(
            f"{API_BASE}/audit-logs/{log_id}",
            json={"action": "hacked"},
            headers=headers(token_a_admin),
        )
        assert r1.status_code in [403, 404, 405], f"DELETE allowed! Status: {r1.status_code}"  # noqa: S101 - assertions intentionally enforce validation invariants
        assert r2.status_code in [403, 404, 405], f"PUT allowed! Status: {r2.status_code}"  # noqa: S101 - assertions intentionally enforce validation invariants
        print("   ✅ API immutability verified (404/405/403 returned)")

        # Save data for DB verification script
        data["job_id"] = job_id
        data["cand_id"] = cand_id
        with Path(".phase13_prod_data.json").open("w") as f:  # noqa: ASYNC230
            json.dump(data, f, indent=2)

    print("\nAPI VALIDATION COMPLETE.")


if __name__ == "__main__":
    asyncio.run(main())
