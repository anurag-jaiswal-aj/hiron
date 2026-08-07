import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import { loginAs } from "./helpers/auth";

test.describe("Candidate Detail Workflows", () => {
  let testCandidateId: string;
  let testJobId: string;
  const runId = Date.now();

  test.beforeAll(() => {
    // Deterministic test data setup
    try {
      execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev`, {
        input: `
        WITH t AS (SELECT id FROM tenants LIMIT 1),
             u AS (SELECT id FROM users WHERE role = 'org_admin' LIMIT 1),
             inserted_job AS (
               INSERT INTO jobs (id, tenant_id, title, description, department, employment_type, status, created_by)
               VALUES (gen_random_uuid(), (SELECT id FROM t), 'Test Job ${runId}', 'Test description', 'Engineering', 'full_time', 'open', (SELECT id FROM u))
               RETURNING id
             ),
             inserted_cand AS (
               INSERT INTO candidates (id, tenant_id, full_name, email, current_title, current_company, location, total_experience_years, skills, source)
               VALUES (gen_random_uuid(), (SELECT id FROM t), 'Detail Candidate ${runId}', 'detail${runId}@example.com', 'QA Engineer', 'Test Corp', 'Remote', 5, '["Testing", "Playwright"]', 'upload')
               RETURNING id
             ),
             inserted_stage AS (
               INSERT INTO pipeline_stages (id, tenant_id, job_id, name, position, stage_type)
               VALUES (gen_random_uuid(), (SELECT id FROM t), (SELECT id FROM inserted_job), 'Applied', 1, 'active')
               RETURNING id
             )
        INSERT INTO job_candidates (id, tenant_id, job_id, candidate_id, current_stage_id)
        VALUES (gen_random_uuid(), (SELECT id FROM t), (SELECT id FROM inserted_job), (SELECT id FROM inserted_cand), (SELECT id FROM inserted_stage));
        `
      });

      // Retrieve the generated candidate ID
      const result = execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev -t`, {
        input: `SELECT id FROM candidates WHERE full_name = 'Detail Candidate ${runId}';`
      }).toString().trim();
      
      const jobResult = execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev -t`, {
        input: `SELECT id FROM jobs WHERE title = 'Test Job ${runId}';`
      }).toString().trim();
      
      testCandidateId = result;
      testJobId = jobResult;
    } catch (e) {
      const err = e as { stdout?: { toString: () => string }; stderr?: { toString: () => string } };
      console.error("Failed to seed deterministic detail candidate:", err?.stdout?.toString(), err?.stderr?.toString());
      throw err;
    }
  });

  test.afterAll(() => {
    // Cleanup
    try {
      if (testCandidateId) {
        execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev`, {
          input: `DELETE FROM candidates WHERE id = '${testCandidateId}';`
        });
      }
      if (testJobId) {
         execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev`, {
          input: `DELETE FROM jobs WHERE id = '${testJobId}';`
        });
      }
    } catch (e) {
      const err = e as { stdout?: { toString: () => string }; stderr?: { toString: () => string } };
      console.error("Cleanup failed:", err?.stdout?.toString(), err?.stderr?.toString());
    }
  });

  test("navigates from Candidates List to Candidate Detail and renders profile and jobs", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/candidates");
    
    // Find candidate in list
    // Search for the candidate to ensure they are on the first page
    await page.fill('input[placeholder="Search candidates..."]', `Detail Candidate ${runId}`);
    await page.waitForTimeout(500); // Wait for debounce
    await page.waitForLoadState("networkidle");

    // Click on row to navigate
    await page.getByText(`Detail Candidate ${runId}`).click();
    await page.waitForURL(`**/candidates/${testCandidateId}`);

    // Verify information rendering
    await expect(page.locator("h1")).toContainText(`Detail Candidate ${runId}`);
    await expect(page.getByText("QA Engineer @ Test Corp")).toBeVisible();
    await expect(page.getByText(`detail${runId}@example.com`)).toBeVisible();
    await expect(page.getByText("5 years")).toBeVisible();
    await expect(page.getByText("Testing")).toBeVisible();
    await expect(page.getByText("Playwright")).toBeVisible();

    // Job Associations rendering
    await expect(page.getByText(`Test Job ${runId}`)).toBeVisible();
    await expect(page.getByText("→ Applied")).toBeVisible();
    
    // Controls should be visible for admin
    await expect(page.getByRole("button", { name: "Edit Profile" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Archive" })).toBeVisible();
  });

  test("handles nonexistent candidate ID gracefully with error state", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/candidates/00000000-0000-0000-0000-000000000000");

    await expect(page.getByText("Candidate Not Found")).toBeVisible();
    await expect(page.getByText("The requested candidate was not found")).toBeVisible();
    
    // Test return button
    await page.click('button:has-text("Return to Candidates List")');
    await page.waitForURL("**/candidates");
  });

  test("authorized user can add candidate to a new job", async ({ page }) => {
    // We need a second job for testing the Add to Job flow
    const secondJobRunId = runId + 1;
    let secondJobId = "";
    try {
      execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev`, {
        input: `
        WITH t AS (SELECT id FROM tenants LIMIT 1),
             u AS (SELECT id FROM users WHERE role = 'org_admin' LIMIT 1),
             inserted_job AS (
               INSERT INTO jobs (id, tenant_id, title, description, department, employment_type, status, created_by)
               VALUES (gen_random_uuid(), (SELECT id FROM t), 'Second Test Job ${secondJobRunId}', 'Test', 'Engineering', 'full_time', 'open', (SELECT id FROM u))
               RETURNING id
             )
        INSERT INTO pipeline_stages (id, tenant_id, job_id, name, position, stage_type)
        VALUES (gen_random_uuid(), (SELECT id FROM t), (SELECT id FROM inserted_job), 'New Stage', 1, 'active');
        `
      });
      secondJobId = execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev -t`, {
        input: `SELECT id FROM jobs WHERE title = 'Second Test Job ${secondJobRunId}';`
      }).toString().trim();
    } catch (e) {
      console.error("Failed to seed second test job");
    }

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${testCandidateId}`);
    
    // Open Add to Job Modal
    await page.getByRole("button", { name: "Add to Job" }).click();
    await expect(page.getByText(`Select a job to add Detail Candidate ${runId} to its pipeline.`)).toBeVisible();
    
    // Select the second job
    await page.locator("select").selectOption({ label: `Second Test Job ${secondJobRunId}` });
    await page.getByRole("button", { name: "Add Candidate" }).click();
    
    // Verify modal closes and candidate detail page updates
    await expect(page.getByRole("button", { name: "Add Candidate" })).not.toBeVisible();
    await expect(page.getByText(`Second Test Job ${secondJobRunId}`)).toBeVisible();
    await expect(page.getByText("→ New Stage")).toBeVisible();
    
    // Test duplicate conflict handling
    await page.getByRole("button", { name: "Add to Job" }).click();
    // Verify the second job is NOT in the select options (it's filtered out)
    await expect(page.locator("select")).not.toContainText(`Second Test Job ${secondJobRunId}`);
    
    await page.getByRole("button", { name: "Cancel" }).click();

    // Cleanup the second job
    if (secondJobId) {
      execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev`, {
        input: `DELETE FROM jobs WHERE id = '${secondJobId}';`
      });
    }
  });

  test("hiring_manager sees read-only detail view without mutation controls", async ({ page }) => {
    await loginAs(page, "manager@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${testCandidateId}`);
    
    await expect(page.locator("h1")).toContainText(`Detail Candidate ${runId}`);
    
    // Should NOT see Edit / Archive / Add to Job
    await expect(page.getByRole("button", { name: "Edit Profile" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Archive" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Add to Job" })).not.toBeVisible();
  });
});
