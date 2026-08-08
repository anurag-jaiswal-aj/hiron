import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Phase 8 Checkpoint 1: Basic AI Scoring UI", () => {
  const jobId = "00000000-0000-0000-0000-000000000001";
  const candidateId = "11111111-1111-1111-1111-111111111111";

  const setupMocks = async (page: any, hasScore: boolean, role: string = "recruiter") => {
    // Mock user session
    await page.route("**/api/v1/auth/me", async (route: any) => {
      await route.fulfill({
        status: 200,
        json: { data: { id: "user-1", email: `${role}@acme.com`, role: role, tenantId: "tenant-1" } },
      });
    });

    // Mock candidate detail
    await page.route(`**/api/v1/candidates/${candidateId}`, async (route: any) => {
      await route.fulfill({
        status: 200,
        json: {
          data: {
            id: candidateId,
            fullName: "Alice Scorer",
            jobs: [{ jobId: jobId, jobTitle: "Senior Developer", currentStage: "Applied", isShortlisted: false }],
            createdAt: new Date().toISOString(),
          },
        },
      });
    });

    // Mock resumes
    await page.route(`**/api/v1/resumes/candidate/${candidateId}`, async (route: any) => {
      await route.fulfill({
        status: 200,
        json: { data: [] },
      });
    });

    // Mock embedding status
    await page.route(`**/api/v1/embeddings/candidates/${candidateId}`, async (route: any) => {
      await route.fulfill({
        status: 200,
        json: { data: { status: "current", modelVersion: "v1" } },
      });
    });

    // Mock GET score
    await page.route(`**/api/v1/jobs/${jobId}/candidates/${candidateId}/score`, async (route: any) => {
      if (route.request().method() === "GET") {
        if (hasScore) {
          await route.fulfill({
            status: 200,
            json: {
              data: { id: "score-1", fitScore: 85, confidence: 0.9, breakdown: {}, explanation: "Good fit", skillsMatched: [], skillsMissing: [], warnings: [], promptVersion: "1", modelVersion: "1", isCurrent: true, createdAt: new Date().toISOString() },
            },
          });
        } else {
          await route.fulfill({
            status: 404,
            json: { error: { code: "NOT_FOUND", message: "Score not found" } },
          });
        }
      } else {
        await route.fallback();
      }
    });
  };

  test("1. Candidate with no score: Score Now visible and works", async ({ page }) => {
    await setupMocks(page, false, "recruiter");

    await page.route(`**/api/v1/jobs/${jobId}/candidates/${candidateId}/score`, async (route: any) => {
      if (route.request().method() === "POST") {
        await new Promise((r) => setTimeout(r, 500)); // Simulating latency
        await route.fulfill({
          status: 200,
          json: {
            data: { id: "score-1", fitScore: 92, confidence: 0.9, breakdown: {}, explanation: "Great fit", skillsMatched: [], skillsMissing: [], warnings: [], promptVersion: "1", modelVersion: "1", isCurrent: true, createdAt: new Date().toISOString() },
          },
        });
      } else {
         await route.fallback();
      }
    });

    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${candidateId}`);
    
    await page.getByRole("button", { name: "Scores" }).click();
    
    // Check "Score Now" is visible and "Not Scored" badge
    await expect(page.getByText("Not Scored")).toBeVisible();
    const scoreNowBtn = page.getByRole("button", { name: "Score Now" });
    await expect(scoreNowBtn).toBeVisible();

    // Click Score Now
    await scoreNowBtn.click();
    
    // Should show Loading state
    await expect(page.getByRole("button", { name: "Scoring..." })).toBeVisible();
    await expect(page.getByText("Not Scored")).toBeVisible();
    
    // After delay, should show score
    await expect(page.getByText("92/100")).toBeVisible();
    await expect(page.getByRole("button", { name: "Re-score" })).toBeVisible();
  });

  test("2. Existing score: current fit score renders", async ({ page }) => {
    await setupMocks(page, true, "recruiter");

    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${candidateId}`);
    await page.getByRole("button", { name: "Scores" }).click();

    await expect(page.getByText("85/100")).toBeVisible();
    await expect(page.getByRole("button", { name: "Re-score" })).toBeVisible();
  });

  test("3. Hiring manager: score visible, Score Now NOT visible", async ({ page }) => {
    await setupMocks(page, true, "manager");

    await loginAs(page, "manager@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${candidateId}`);
    await page.getByRole("button", { name: "Scores" }).click();

    await expect(page.getByText("85/100")).toBeVisible();
    await expect(page.getByRole("button", { name: "Re-score" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Score Now" })).not.toBeVisible();
  });

  test("4. Duplicate submission protection: prevents multiple POST requests", async ({ page }) => {
    await setupMocks(page, false, "recruiter");

    let postRequestCount = 0;
    let finishRequest: () => void;
    const requestPromise = new Promise<void>((resolve) => {
      finishRequest = resolve;
    });

    await page.route(`**/api/v1/jobs/${jobId}/candidates/${candidateId}/score`, async (route: any) => {
      if (route.request().method() === "POST") {
        postRequestCount++;
        await requestPromise; // Hang until we let it finish
        await route.fulfill({
          status: 200,
          json: {
            data: { id: "score-1", fitScore: 92, confidence: 0.9, breakdown: {}, explanation: "Great fit", skillsMatched: [], skillsMissing: [], warnings: [], promptVersion: "1", modelVersion: "1", isCurrent: true, createdAt: new Date().toISOString() },
          },
        });
      } else {
         await route.fallback();
      }
    });

    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${candidateId}`);
    
    await page.getByRole("button", { name: "Scores" }).click();
    
    // Click Score Now
    const scoreNowBtn = page.getByRole("button", { name: "Score Now" });
    await scoreNowBtn.click();
    
    // Should show Loading state
    const scoringBtn = page.getByRole("button", { name: "Scoring..." });
    await expect(scoringBtn).toBeVisible();

    // Attempt to double-click the button even though it says Scoring...
    // Playwright won't let you click a disabled button normally, so we force click it
    await scoringBtn.click({ force: true });
    await scoringBtn.click({ force: true });
    
    // Resolve the request
    finishRequest!();
    
    // After delay, should show score
    await expect(page.getByText("92/100")).toBeVisible();
    
    // Verify only one POST request was sent
    expect(postRequestCount).toBe(1);
  });

  test("5. API failure: scoring error surfaced", async ({ page }) => {
    await setupMocks(page, false, "recruiter");

    await page.route(`**/api/v1/jobs/${jobId}/candidates/${candidateId}/score`, async (route: any) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 500,
          json: { error: { message: "AI Scoring Failed" } },
        });
      } else {
         await route.fallback();
      }
    });

    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${candidateId}`);
    
    await page.getByRole("button", { name: "Scores" }).click();
    
    await page.getByRole("button", { name: "Score Now" }).click();
    
    await expect(page.getByText("Error: AI Scoring Failed")).toBeVisible();
  });
});

test.describe("Responsive Scoring UI — 390px", () => {
  test.use({ viewport: { width: 390, height: 844 } });
  
  test("6. No horizontal overflow", async ({ page }) => {
    const jobId = "00000000-0000-0000-0000-000000000001";
    const candidateId = "11111111-1111-1111-1111-111111111111";
    
    await page.route("**/api/v1/auth/me", async (route: any) => {
      await route.fulfill({ status: 200, json: { data: { id: "user-1", email: "admin@acme.com", role: "org_admin", tenantId: "tenant-1" } } });
    });

    await page.route(`**/api/v1/candidates/${candidateId}`, async (route: any) => {
      await route.fulfill({
        status: 200,
        json: {
          data: {
            id: candidateId,
            fullName: "Alice Scorer",
            jobs: [{ jobId: jobId, jobTitle: "Senior Developer", currentStage: "Applied", isShortlisted: false }],
            createdAt: new Date().toISOString(),
          },
        },
      });
    });

    await page.route(`**/api/v1/jobs/${jobId}/candidates/${candidateId}/score`, async (route: any) => {
        await route.fulfill({
          status: 200,
          json: {
            data: { id: "score-1", fitScore: 85, confidence: 0.9, breakdown: {}, explanation: "Good fit", skillsMatched: [], skillsMissing: [], warnings: [], promptVersion: "1", modelVersion: "1", isCurrent: true, createdAt: new Date().toISOString() },
          },
        });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${candidateId}`);
    await page.getByRole("button", { name: "Scores" }).click();

    // Check no horizontal scrollbar
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2); // 2px tolerance
  });
});
