from locust import HttpUser, task, between
import random

class HironLoadTestUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Authenticate as the org_admin and fetch a job_id for pipeline requests."""
        import psycopg
        import os
        
        # Fetch the tenant ID for the loadtest-tenant
        db_url = os.getenv("DATABASE_URL", "postgresql://hiron_user:hiron_secure_password@localhost:5432/hiron_dev")
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM tenants WHERE slug = 'loadtest-tenant'")
                result = cur.fetchone()
                if result:
                    self.tenant_id = str(result[0])
                else:
                    print("Could not find loadtest-tenant in DB")
                    self.environment.runner.quit()
                    return

        # Authenticate using the load test admin credentials
        response = self.client.post("/api/v1/auth/login", json={
            "email": "admin@loadtest.hiron.ai",
            "password": "LoadTestPassword123!",
            "tenantId": self.tenant_id
        })
        
        if response.status_code == 200:
            token = response.json().get("data", {}).get("accessToken")
            self.client.headers.update({"Authorization": f"Bearer {token}"})
        else:
            print(f"Failed to authenticate: {response.text}")
            self.environment.runner.quit()
            return
            
        # Fetch jobs to get a job_id for pipeline requests
        jobs_response = self.client.get("/api/v1/jobs")
        if jobs_response.status_code == 200:
            jobs_data = jobs_response.json().get("data", {}).get("data", [])
            self.job_ids = [job["id"] for job in jobs_data]
        else:
            self.job_ids = []

    @task(5)
    def auth_me(self):
        """Test cached current-user read."""
        self.client.get("/api/v1/auth/me", name="/api/v1/auth/me")

    @task(3)
    def dashboard_summary(self):
        """Test heavy aggregate dashboard."""
        self.client.get("/api/v1/dashboard/summary", name="/api/v1/dashboard/summary")

    @task(4)
    def list_candidates(self):
        """Test cursor pagination."""
        self.client.get("/api/v1/candidates?limit=25", name="/api/v1/candidates")

    @task(4)
    def job_pipeline(self):
        """Test Kanban board data retrieval."""
        if self.job_ids:
            job_id = random.choice(self.job_ids)
            self.client.get(f"/api/v1/jobs/{job_id}/pipeline", name="/api/v1/jobs/[id]/pipeline")

    @task(2)
    def list_audit_logs(self):
        """Test cursor pagination for audit logs."""
        self.client.get("/api/v1/audit-logs", name="/api/v1/audit-logs")

    @task(2)
    def ai_usage_summary(self):
        """Test AI usage summary query."""
        self.client.get("/api/v1/ai-usage/summary", name="/api/v1/ai-usage/summary")
