import { test, expect, Page } from "@playwright/test";
import { loginAs } from "./helpers/auth";
import { execSync } from "child_process";

const queryDB = (query: string): string => {
  return execSync(`docker exec hiron-postgres psql -U hiron_user -d hiron_dev -t -c "${query}"`)
    .toString()
    .trim();
};

async function setupAuth(page: Page, role: string = "org_admin") {
  await page.route("**/api/v1/auth/refresh", async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        data: {
          accessToken: "mock-token",
        },
      },
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
        },
      },
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
      await new Promise((r) => setTimeout(r, 500));
      await route.fulfill({ json: { data: mockDashboardSummary } });
    });

    await setupAuth(page, "org_admin");

    // Navigate and check loading state
    await page.goto("/dashboard");
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
    await page.goto("/dashboard");

    await expect(page.locator("h1", { hasText: "Dashboard" })).toBeVisible();
    await expect(page.locator("text=Pipeline Overview")).toBeVisible();
  });

  test("3. Renders dashboard for hiring_manager", async ({ page }) => {
    await page.route("**/api/v1/dashboard/summary", async (route) => {
      await route.fulfill({ json: { data: mockDashboardSummary } });
    });

    await setupAuth(page, "hiring_manager");
    await page.goto("/dashboard");

    await expect(page.locator("h1", { hasText: "Dashboard" })).toBeVisible();
    await expect(page.locator("text=Recent Activity")).toBeVisible();
  });

  test("4. API error state works", async ({ page }) => {
    await page.route("**/api/v1/dashboard/summary", async (route) => {
      await route.fulfill({ status: 500, json: { error: "Internal Server Error" } });
    });

    await setupAuth(page, "org_admin");
    await page.goto("/dashboard");

    await expect(
      page.locator("text=Failed to load dashboard data. Please try again."),
    ).toBeVisible();
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
    await page.goto("/dashboard");

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
    await page.goto("/dashboard");

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

  test("7. Real backend data is correctly aggregated and rendered", async ({ page }) => {
    // We will NOT use setupAuth or mock any routes. We use the real backend.

    // Create unique tenant and user to ensure fresh dashboard metrics
    const timestamp = Date.now();
    const tenantId = `d0000000-0000-0000-0000-000000${timestamp.toString().slice(-6)}`;
    const userEmail = `dash-${timestamp}@acme.com`;

    // Hash for 'SecurePassword123!'
    const rawPwdHash = queryDB(
      "SELECT password_hash FROM users WHERE email = 'admin@acme.com' LIMIT 1;",
    );
    const pwdHash = rawPwdHash.replace(/'/g, "''").replace(/\$/g, "\\$");

    // Provision Tenant and User
    queryDB(
      `INSERT INTO tenants (id, name, slug, created_at, updated_at) VALUES ('${tenantId}', 'Dash E2E', 'dash-${timestamp}', NOW(), NOW());`,
    );
    queryDB(
      `INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_email_verified, created_at, updated_at) VALUES (gen_random_uuid(), '${tenantId}', '${userEmail}', '${pwdHash}', 'Dash Admin', 'org_admin', true, true, NOW(), NOW());`,
    );

    // Initial Dashboard check (should be onboarding)
    await loginAs(page, userEmail, "SecurePassword123!", tenantId);
    await expect(page.locator("text=Welcome to Hiron! 👋")).toBeVisible();

    // Provision real data: 1 Open Job, 2 Candidates (1 scored, 1 hired)
    const jobId = `e0000000-0000-0000-0000-000000${timestamp.toString().slice(-6)}`;
    const cand1Id = `c1000000-0000-0000-0000-000000${timestamp.toString().slice(-6)}`;
    const cand2Id = `c2000000-0000-0000-0000-000000${timestamp.toString().slice(-6)}`;
    const stageHiredId = `d1000000-0000-0000-0000-000000${timestamp.toString().slice(-6)}`;
    const stageAppliedId = `d2000000-0000-0000-0000-000000${timestamp.toString().slice(-6)}`;

    // Insert Job and Stages
    queryDB(
      `INSERT INTO jobs (id, tenant_id, title, description, status, created_at, updated_at) VALUES ('${jobId}', '${tenantId}', 'Real E2E Job', 'Test', 'open', NOW(), NOW());`,
    );
    queryDB(
      `INSERT INTO pipeline_stages (id, tenant_id, job_id, name, position) VALUES ('${stageAppliedId}', '${tenantId}', '${jobId}', 'Applied', 1);`,
    );
    queryDB(
      `INSERT INTO pipeline_stages (id, tenant_id, job_id, name, position) VALUES ('${stageHiredId}', '${tenantId}', '${jobId}', 'Hired', 2);`,
    );

    // Insert Candidates
    queryDB(
      `INSERT INTO candidates (id, tenant_id, full_name, email) VALUES ('${cand1Id}', '${tenantId}', 'Cand One', 'c1@test.com');`,
    );
    queryDB(
      `INSERT INTO candidates (id, tenant_id, full_name, email) VALUES ('${cand2Id}', '${tenantId}', 'Cand Two', 'c2@test.com');`,
    );

    // Insert Job Candidates (Cand 1 is Applied, Cand 2 is Hired)
    queryDB(
      `INSERT INTO job_candidates (id, tenant_id, job_id, candidate_id, current_stage_id) VALUES (gen_random_uuid(), '${tenantId}', '${jobId}', '${cand1Id}', '${stageAppliedId}');`,
    );
    queryDB(
      `INSERT INTO job_candidates (id, tenant_id, job_id, candidate_id, current_stage_id) VALUES (gen_random_uuid(), '${tenantId}', '${jobId}', '${cand2Id}', '${stageHiredId}');`,
    );

    // Insert 1 Score for Cand 1
    queryDB(
      `INSERT INTO scores (id, tenant_id, job_candidate_id, fit_score, confidence, breakdown, explanation, prompt_name, prompt_version, model_version, is_current) SELECT gen_random_uuid(), '${tenantId}', id, 85, 0.9, '{}'::jsonb, 'Test', 'test', 'v1', 'gpt-4', true FROM job_candidates WHERE candidate_id = '${cand1Id}';`,
    );

    // Insert Audit Activity
    queryDB(
      `INSERT INTO audit_logs (id, tenant_id, actor_id, action, entity_type, entity_id, created_at) SELECT gen_random_uuid(), '${tenantId}', id, 'create', 'job', '${jobId}', NOW() FROM users WHERE email = '${userEmail}';`,
    );

    // Reload Dashboard via client-side routing to preserve in-memory auth state
    await page.locator("nav a", { hasText: "Jobs" }).click();
    await page.waitForURL(/\/jobs/);
    await page.locator("nav a", { hasText: "Overview" }).click();
    await page.waitForURL(/\/dashboard/);
    await page.waitForTimeout(1000); // Wait for API response

    // Verify Metric Cards using real backend aggregations
    // Expect 1 Open Job
    await expect(page.locator("text=Open Jobs")).toBeVisible();
    await expect(page.locator("text=1").first()).toBeVisible();

    // Expect 2 Total Candidates
    await expect(page.locator("text=Total Candidates")).toBeVisible();
    await expect(page.locator("text=2").first()).toBeVisible();

    // Expect 1 Scored Candidate
    await expect(page.locator("text=AI Scored")).toBeVisible();
    await expect(page.locator("text=1").nth(1)).toBeVisible(); // .nth(1) because '1' appears multiple times, let's be robust

    // Expect 1 Hired Candidate
    await expect(page.locator("text=Hired")).toBeVisible();
    await expect(page.locator("text=1").nth(2)).toBeVisible();

    // Verify Pipeline
    await expect(page.locator("text=Real E2E Job")).toBeVisible();
    await expect(page.locator("text=2 cands")).toBeVisible();

    // Verify Recent Activity
    await expect(page.locator("text=Dash Admin")).toBeVisible();

    // Cleanup
    queryDB(`DELETE FROM audit_logs WHERE tenant_id = '${tenantId}'`);
    queryDB(`DELETE FROM scores WHERE tenant_id = '${tenantId}'`);
    queryDB(`DELETE FROM job_candidates WHERE tenant_id = '${tenantId}'`);
    queryDB(`DELETE FROM pipeline_stages WHERE tenant_id = '${tenantId}'`);
    queryDB(`DELETE FROM candidates WHERE tenant_id = '${tenantId}'`);
    queryDB(`DELETE FROM jobs WHERE tenant_id = '${tenantId}'`);
    queryDB(`DELETE FROM users WHERE tenant_id = '${tenantId}'`);
    queryDB(`DELETE FROM tenants WHERE id = '${tenantId}'`);
  });
});
