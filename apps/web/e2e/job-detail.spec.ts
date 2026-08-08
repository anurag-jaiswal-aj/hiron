import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Job Detail Workflows", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
  });

  test("navigates from Jobs List to Job Detail and renders details and tabs", async ({ page }) => {
    const jobTitle = `Principal AI Engineer ${Date.now()}`;

    // Create a job first to get a real Job Detail page
    await page.goto("/jobs/new");
    await page.waitForLoadState("networkidle");

    await page.fill("#job-title-input", jobTitle);
    await page.selectOption("#job-department-select", "Engineering");
    await page.fill("#job-location-input", "San Francisco, CA");
    await page.fill("#job-description-textarea", "Detailed description for Principal AI Engineer position.");

    const reqSkillInput = page.locator("#job-req-skills-input");
    await reqSkillInput.fill("PyTorch");
    await reqSkillInput.press("Enter");

    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs$/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    // Click newly created job title link in table
    const jobLink = page.getByRole("link", { name: jobTitle });
    await expect(jobLink).toBeVisible();
    await jobLink.click();

    // Verify navigation to /jobs/[id]
    await page.waitForURL(/\/jobs\/[a-f0-9-]+$/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    // Verify Job Header & Metadata
    await expect(page.getByRole("heading", { name: jobTitle })).toBeVisible();
    await expect(page.getByText("San Francisco, CA")).toBeVisible();
    await expect(page.getByText("Detailed description for Principal AI Engineer position.")).toBeVisible();
    await expect(page.getByText("PyTorch")).toBeVisible();

    // Verify Tabs Bar
    await expect(page.getByRole("button", { name: "Details" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Kanban" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Candidates" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Scores" })).toBeVisible();

    // Test Tab Switching to Kanban
    await page.click('button:has-text("Kanban")');
    await expect(page.getByRole("heading", { name: "Pipeline Kanban Board" })).toBeVisible();

    // Test Tab Switching to Candidates
    await page.click('button:has-text("Candidates")');
    await expect(page.getByRole("heading", { name: "Candidate Pool" })).toBeVisible();

    // Mock the pipeline API to return at least one candidate so the Scores tab renders the list instead of EmptyState
    await page.route(`**/api/v1/jobs/*/pipeline`, async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: [
            {
              stageId: "applied",
              stageName: "Applied",
              position: 0,
              candidateCount: 1,
              candidates: [
                {
                  candidateId: "cand-1",
                  jobCandidateId: "jc-1",
                  fullName: "Jane Smith",
                  currentTitle: "Backend Developer",
                  fitScore: 92,
                  confidence: 0.85,
                  isShortlisted: false,
                  appliedAt: new Date().toISOString()
                }
              ]
            }
          ]
        }
      });
    });

    // Test Tab Switching to Scores
    await page.click('button:has-text("Scores")');
    await expect(page.getByRole("heading", { name: "Candidate AI Fit Scores" })).toBeVisible();
  });

  test("handles nonexistent job ID gracefully with error state", async ({ page }) => {
    await page.goto("/jobs/00000000-0000-0000-0000-000000000000");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Job Not Found" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Return to Jobs List" })).toBeVisible();
  });
});
