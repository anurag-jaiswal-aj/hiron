import { test, expect, Page } from "@playwright/test";

async function setupAuth(page: Page, role: string = "org_admin") {
  await page.route("**/api/v1/auth/refresh", async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: {
          accessToken: "mock-token",
        }
      }
    });
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: {
          id: "test-user-id",
          tenantId: "test-tenant-id",
          email: `${role}@acme.com`,
          role: role,
        }
      }
    });
  });
}

test.describe("Dashboard & Analytics (Phase 12)", () => {
  const mockDashboardSummary = {
    metrics: {
      openJobsCount: 12,
      totalCandidatesCount: 1250,
      scoredCandidatesCount: 847,
      shortlistedCandidatesCount: 105,
      hiredCandidatesCount: 23,
    },
    pipelineOverview: [
      {
        jobId: "job-1",
        jobTitle: "Sr. Backend Eng",
        status: "open",
        totalCandidates: 47,
        stages: [
          { stageId: "s1", stageName: "Applied", position: 1, candidateCount: 20 },
          { stageId: "s2", stageName: "Phone Screen", position: 2, candidateCount: 15 },
          { stageId: "s3", stageName: "Interview", position: 3, candidateCount: 12 },
        ],
      },
    ],
    scoreDistribution: {
      highFitCount: 400,
      mediumFitCount: 300,
      lowFitCount: 147,
      totalScored: 847,
      averageFitScore: 72.5,
    },
    recentActivity: [
      {
        id: "act-1",
        activityType: "job_created",
        description: "created a new job",
        actorName: "Jane Doe",
        timestamp: new Date().toISOString(),
      },
    ],
  };

  test("1. Renders loading state and then dashboard for org_admin", async ({ page }) => {
    await page.route("**/api/v1/dashboard/summary", async (route) => {
      // delay to ensure loading state is visible
      await new Promise(r => setTimeout(r, 500));
      await route.fulfill({ json: { data: mockDashboardSummary } });
    });

    await setupAuth(page, "org_admin");
    
    // Navigate and check loading state
    await page.goto("/");
    await expect(page.locator("text=Loading dashboard metrics...")).toBeVisible();

    // Check header
    await expect(page.locator("h1", { hasText: "Dashboard" })).toBeVisible();
    await expect(page.locator("text=Recruiting intelligence overview")).toBeVisible();

    // Check metric cards
    await expect(page.locator("text=Open Jobs")).toBeVisible();
    await expect(page.locator("text=12").first()).toBeVisible();
    await expect(page.locator("text=Total Candidates")).toBeVisible();
    await expect(page.locator("text=1250")).toBeVisible();
    await expect(page.locator("text=AI Scored")).toBeVisible();
    await expect(page.locator("text=847")).toBeVisible();
    await expect(page.locator("text=Hired")).toBeVisible();
    await expect(page.locator("text=23")).toBeVisible();

    // Check pipeline overview
    await expect(page.locator("h2", { hasText: "Pipeline Overview" })).toBeVisible();
    await expect(page.locator("text=Sr. Backend Eng")).toBeVisible();
    await expect(page.locator("text=47 cands")).toBeVisible();

    // Check score distribution chart
    await expect(page.locator("h3", { hasText: "AI Score Distribution" })).toBeVisible();
    await expect(page.locator("text=Average Score:")).toBeVisible();
    await expect(page.locator("text=72.5")).toBeVisible();

    // Check recent activity
    await expect(page.locator("h2", { hasText: "Recent Activity" })).toBeVisible();
    await expect(page.locator("text=Jane Doe")).toBeVisible();
    await expect(page.locator("text=created a new job")).toBeVisible();
  });

  test("2. Renders dashboard for recruiter", async ({ page }) => {
    await page.route("**/api/v1/dashboard/summary", async (route) => {
      await route.fulfill({ json: { data: mockDashboardSummary } });
    });

    await setupAuth(page, "recruiter");
    await page.goto("/");
    
    await expect(page.locator("h1", { hasText: "Dashboard" })).toBeVisible();
    await expect(page.locator("text=Pipeline Overview")).toBeVisible();
  });

  test("3. Renders dashboard for hiring_manager", async ({ page }) => {
    await page.route("**/api/v1/dashboard/summary", async (route) => {
      await route.fulfill({ json: { data: mockDashboardSummary } });
    });

    await setupAuth(page, "hiring_manager");
    await page.goto("/");
    
    await expect(page.locator("h1", { hasText: "Dashboard" })).toBeVisible();
    await expect(page.locator("text=Recent Activity")).toBeVisible();
  });

  test("4. API error state works", async ({ page }) => {
    await page.route("**/api/v1/dashboard/summary", async (route) => {
      await route.fulfill({ status: 500, json: { error: "Internal Server Error" } });
    });

    await setupAuth(page, "org_admin");
    await page.goto("/");
    
    await expect(page.locator("text=Failed to load dashboard data. Please try again.")).toBeVisible();
  });

  test("5. Empty/new-tenant onboarding state works", async ({ page }) => {
    const emptySummary = {
      ...mockDashboardSummary,
      metrics: {
        openJobsCount: 0,
        totalCandidatesCount: 0,
        scoredCandidatesCount: 0,
        shortlistedCandidatesCount: 0,
        hiredCandidatesCount: 0,
      },
    };

    await page.route("**/api/v1/dashboard/summary", async (route) => {
      await route.fulfill({ json: { data: emptySummary } });
    });

    await setupAuth(page, "org_admin");
    await page.goto("/");
    
    await expect(page.locator("text=Welcome to Hiron! 👋")).toBeVisible();
    await expect(page.locator("text=Create your first job")).toBeVisible();
    await expect(page.locator("text=Upload resumes")).toBeVisible();
    await expect(page.locator("text=Let AI score candidates")).toBeVisible();
    await expect(page.locator("button:has-text('Create First Job')")).toBeVisible();
  });

  test("6. Responsive layout does not horizontally overflow", async ({ page }) => {
    await page.route("**/api/v1/dashboard/summary", async (route) => {
      await route.fulfill({ json: { data: mockDashboardSummary } });
    });

    await setupAuth(page, "org_admin");
    await page.goto("/");

    // Desktop
    let width = await page.evaluate(() => document.documentElement.scrollWidth);
    let viewWidth = await page.evaluate(() => window.innerWidth);
    expect(width).toBeLessThanOrEqual(viewWidth);

    // Tablet
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500); // allow resize reflow
    width = await page.evaluate(() => document.documentElement.scrollWidth);
    viewWidth = await page.evaluate(() => window.innerWidth);
    expect(width).toBeLessThanOrEqual(viewWidth);

    // Mobile
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(500); // allow resize reflow
    width = await page.evaluate(() => document.documentElement.scrollWidth);
    viewWidth = await page.evaluate(() => window.innerWidth);
    expect(width).toBeLessThanOrEqual(viewWidth);
  });
});
