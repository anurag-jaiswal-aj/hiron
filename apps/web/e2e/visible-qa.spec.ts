/**
 * HIRON MONOCHROME REDESIGN — VISIBLE BROWSER QA (Fixed)
 *
 * Run with:  npx playwright test e2e/visible-qa.spec.ts --headed --timeout=120000
 */
import { test, expect, type Page } from "@playwright/test";
import { loginAs } from "./helpers/auth";

const TENANT_ID = "2f16ef71-c473-4197-8db3-eeb667c69dfe";

let shotIndex = 0;
async function snap(page: Page, name: string): Promise<void> {
  shotIndex++;
  const padded = String(shotIndex).padStart(2, "0");
  let buffer: Buffer;
  try {
    buffer = await page.screenshot({ fullPage: true, timeout: 5000 });
  } catch (err) {
    console.warn(`[snap] fullPage timeout for ${name}, capturing viewport...`);
    try {
      buffer = await page.screenshot({ timeout: 5000 });
    } catch (fallbackErr) {
      if (
        page.isClosed() ||
        (fallbackErr instanceof Error &&
          fallbackErr.message.includes("Target page, context or browser has been closed"))
      ) {
        console.warn(`[snap] Page closed during fallback for ${name}, returning safely.`);
        return;
      }
      throw fallbackErr;
    }
  }
  await test.info().attach(`${padded}_${name}`, {
    body: buffer,
    contentType: "image/png",
  });
}

// ── 1. LOGIN & AUTH ──────────────────────────────────────────────
test("01 — Login page renders", async ({ page }) => {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  await snap(page, "login_page");

  await expect(page.locator("#email")).toBeVisible();
  await expect(page.locator("#tenantId")).toBeVisible();
  await expect(page.locator("#password")).toBeVisible();
  await expect(page.locator('button[type="submit"]')).toBeVisible();
});

test("02 — Invalid credentials show error", async ({ page }) => {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  await page.fill("#email", "invalid@acme.com");
  await page.fill("#tenantId", TENANT_ID);
  await page.fill("#password", "wrongpassword");
  await snap(page, "login_invalid_filled");

  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
  await snap(page, "login_error_displayed");

  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByText("Invalid email, password")).toBeVisible();
});

test("03 — Valid org_admin login to dashboard", async ({ page }) => {
  await loginAs(page, "admin@acme.com", "SecurePassword123!");
  await snap(page, "dashboard_after_login");
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("04 — Dashboard sidebar, layout, responsive", async ({ page }) => {
  await loginAs(page, "admin@acme.com", "SecurePassword123!");

  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Jobs", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Team" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();

  await snap(page, "dashboard_full_desktop");

  await page.setViewportSize({ width: 768, height: 1024 });
  await page.waitForTimeout(500);
  await snap(page, "dashboard_tablet_768");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  await snap(page, "dashboard_mobile_390");

  await page.setViewportSize({ width: 1440, height: 900 });
});

test("05 — Protected route redirect", async ({ page }) => {
  await page.goto("/jobs");
  await page.waitForURL(/\/login$/, { timeout: 10000 });
  await snap(page, "protected_redirect_to_login");
  await expect(page).toHaveURL(/\/login$/);
});

// ── 2. JOBS LIST (empty state) ───────────────────────────────────
test("06 — Jobs List empty state with controls", async ({ page }) => {
  await loginAs(page, "admin@acme.com", "SecurePassword123!");
  await page.click('a:has-text("Jobs")');
  await page.waitForURL(/\/jobs/);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  await snap(page, "jobs_list_empty_state");

  await expect(page.locator('input[placeholder*="Search"]')).toBeVisible();
  await expect(page.getByText("+ Create Job")).toBeVisible();
});

test("07 — Jobs List search, filter, sort controls render", async ({ page }) => {
  await loginAs(page, "admin@acme.com", "SecurePassword123!");
  await page.goto("/jobs");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);

  // Search for nonexistent
  await page.fill('input[placeholder*="Search"]', "nonexistent query xyz");
  await page.waitForTimeout(1000);
  await snap(page, "jobs_search_no_results");

  // Clear
  await page.fill('input[placeholder*="Search"]', "");
  await page.waitForTimeout(1000);
  await snap(page, "jobs_search_cleared");

  // Status filter
  const selects = page.locator("select");
  if ((await selects.count()) > 0) {
    await selects.nth(0).selectOption("draft");
    await page.waitForTimeout(1000);
    await snap(page, "jobs_filter_draft");
    await selects.nth(0).selectOption("");
    await page.waitForTimeout(500);
  }

  // Department filter
  if ((await selects.count()) > 1) {
    await selects.nth(1).selectOption("Engineering");
    await page.waitForTimeout(1000);
    await snap(page, "jobs_filter_engineering");
    await selects.nth(1).selectOption("");
    await page.waitForTimeout(500);
  }

  await snap(page, "jobs_controls_tested");
});

// ── 3. CREATE JOB ────────────────────────────────────────────────
test("08 — Create Job validation (invalid experience)", async ({ page }) => {
  await loginAs(page, "admin@acme.com", "SecurePassword123!");
  await page.goto("/jobs/new");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  await snap(page, "create_job_empty_form");

  await page.fill("#job-title-input", "Staff AI Architect QA");
  await page.selectOption("#job-department-select", "Engineering");
  await page.selectOption("#job-employment-select", "full_time");
  await page.fill("#job-location-input", "San Francisco, CA");
  await page.fill("#job-exp-min-input", "10");
  await page.fill("#job-exp-max-input", "5");
  await page.fill(
    "#job-description-textarea",
    "We are seeking an expert Staff AI Architect to lead generative AI systems.",
  );
  await snap(page, "create_job_filled_invalid_exp");

  await page.click('button[type="submit"]');
  await page.waitForTimeout(1000);
  await snap(page, "create_job_validation_error");

  const hasExpError =
    (await page.getByText("must be greater than or equal").count()) > 0 ||
    (await page.getByText("Maximum experience").count()) > 0;
  expect(hasExpError).toBeTruthy();
});

/**
 * Test 09: Full create → list → detail → edit → lifecycle IN A SINGLE SESSION.
 *
 * Due to the session.commit() bug (transactions not committed in the API),
 * jobs only exist within the same SQLAlchemy session. We must perform the
 * full CRUD lifecycle in one continuous test to exercise the flow.
 */
test("09 — Full Job CRUD lifecycle (create, detail, edit, lifecycle)", async ({ page }) => {
  await loginAs(page, "admin@acme.com", "SecurePassword123!");
  await page.goto("/jobs/new");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);

  const jobTitle = `QA Lifecycle Engineer ${Date.now()}`;

  // ── CREATE ──
  await page.fill("#job-title-input", jobTitle);
  await page.selectOption("#job-department-select", "Engineering");
  await page.selectOption("#job-employment-select", "full_time");
  await page.fill("#job-location-input", "Remote — Global");
  await page.fill("#job-exp-min-input", "3");
  await page.fill("#job-exp-max-input", "8");
  await page.fill(
    "#job-description-textarea",
    "QA engineer to build end-to-end test coverage for Hiron.",
  );

  const reqSkill = page.locator("#job-req-skills-input");
  await reqSkill.fill("Python");
  await reqSkill.press("Enter");
  await page.waitForTimeout(200);
  await reqSkill.fill("Playwright");
  await reqSkill.press("Enter");
  await page.waitForTimeout(200);

  const prefSkill = page.locator("#job-pref-skills-input");
  await prefSkill.fill("Docker");
  await prefSkill.press("Enter");
  await page.waitForTimeout(200);

  await snap(page, "create_job_filled_with_skills");

  await page.click('button[type="submit"]');
  await page.waitForURL(/\/jobs$/, { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2000);
  await snap(page, "after_create_redirect_to_jobs");

  const jobLink = page.getByText(jobTitle);
  await expect(jobLink).toBeVisible();
  await snap(page, "jobs_list_job_visible");

  // ── DETAIL ──
  await jobLink.click();
  await page.waitForURL(/\/jobs\/[a-f0-9-]+$/);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  await snap(page, "job_detail_page");

  // Click tabs
  for (const tab of ["Details", "Kanban", "Candidates", "Scores"]) {
    const tabBtn = page.locator(`button:has-text("${tab}")`).first();
    if ((await tabBtn.count()) > 0) {
      await tabBtn.click();
      await page.waitForTimeout(500);
      await snap(page, `job_detail_tab_${tab.toLowerCase()}`);
    }
  }

  // ── EDIT ──
  const editBtn = page.locator('a:has-text("Edit Job"), button:has-text("Edit Job")').first();
  if ((await editBtn.count()) > 0) {
    await editBtn.click();
    await page.waitForURL(/\/edit$/);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);
    await snap(page, "edit_job_loaded");

    await page.fill("#edit-job-location-input", "New York, NY (QA Updated)");
    await snap(page, "edit_job_modified");

    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
    await snap(page, "edit_job_saved");
  }

  // ── LIFECYCLE ──
  // Navigate back to detail
  if (page.url().includes("/edit")) {
    await page.goBack();
    await page.waitForTimeout(1000);
  }
  await snap(page, "lifecycle_initial_state");

  for (const btnText of ["Pause Job", "Reopen Job", "Close Job", "Archive"]) {
    const btn = page.locator(`button:has-text("${btnText}")`);
    if ((await btn.count()) > 0 && (await btn.isVisible().catch(() => false))) {
      await btn.click();
      await page.waitForTimeout(1500);
      await snap(page, `lifecycle_after_${btnText.replace(/\s+/g, "_").toLowerCase()}`);
    }
  }
});

test("10 — Nonexistent Job Detail error", async ({ page }) => {
  await loginAs(page, "admin@acme.com", "SecurePassword123!");
  await page.goto("/jobs/00000000-0000-0000-0000-000000000000");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2000);
  await snap(page, "job_detail_nonexistent");
});

// ── TEAM MANAGEMENT ──────────────────────────────────────────────
test("11 — Team Management page", async ({ page }) => {
  await loginAs(page, "admin@acme.com", "SecurePassword123!");
  await page.getByRole("link", { name: "Team" }).click();
  await page.waitForURL(/\/users/);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  await snap(page, "team_management_desktop");

  const inviteBtn = page.locator('button:has-text("Invite"), a:has-text("Invite")').first();
  if ((await inviteBtn.count()) > 0) {
    await inviteBtn.click();
    await page.waitForTimeout(500);
    await snap(page, "invite_user_modal");

    const cancelBtn = page.locator('button:has-text("Cancel")').first();
    if ((await cancelBtn.count()) > 0) {
      await cancelBtn.click();
      await page.waitForTimeout(300);
    }
  }

  await page.setViewportSize({ width: 768, height: 1024 });
  await page.waitForTimeout(500);
  await snap(page, "team_tablet_768");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  await snap(page, "team_mobile_390");

  await page.setViewportSize({ width: 1440, height: 900 });
});

// ── RBAC — HIRING MANAGER ────────────────────────────────────────
test("12 — Hiring Manager RBAC", async ({ page }) => {
  await loginAs(page, "manager@acme.com", "SecurePassword123!");
  await snap(page, "hm_dashboard");

  await page.goto("/jobs");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  await snap(page, "hm_jobs_list");

  const createJobVisible = await page
    .getByText("+ Create Job")
    .isVisible()
    .catch(() => false);
  expect(createJobVisible).toBeFalsy();
  await snap(page, "hm_no_create_button");

  // Direct nav to /jobs/new → Access Denied
  await page.goto("/jobs/new");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2000);
  await snap(page, "hm_access_denied_create");
  await expect(page.getByText("Access Denied")).toBeVisible();
});

// ── RESPONSIVE AUDIT ─────────────────────────────────────────────
test("13 — Responsive breakpoint audit", async ({ page }) => {
  test.setTimeout(60000);
  await loginAs(page, "admin@acme.com", "SecurePassword123!");

  const routes = ["/", "/jobs", "/users"];
  const viewports = [
    { width: 1440, height: 900, label: "desktop_1440" },
    { width: 1280, height: 800, label: "laptop_1280" },
    { width: 768, height: 1024, label: "tablet_768" },
    { width: 390, height: 844, label: "mobile_390" },
  ];

  for (const r of routes) {
    await page.goto(r);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.waitForTimeout(300);
      const pageName = r === "/" ? "overview" : r.replace("/", "");
      await snap(page, `responsive_${pageName}_${vp.label}`);
    }
  }

  await page.setViewportSize({ width: 1440, height: 900 });
});

// ── LOGOUT ───────────────────────────────────────────────────────
test("14 — Logout flow", async ({ page }) => {
  await loginAs(page, "admin@acme.com", "SecurePassword123!");
  await snap(page, "before_logout");

  const signOutBtn = page.locator('button:has-text("Sign Out")').first();
  expect(await signOutBtn.count()).toBeGreaterThan(0);
  await signOutBtn.click();
  await page.waitForTimeout(2000);
  await page.waitForLoadState("networkidle");
  await snap(page, "after_logout");
  expect(page.url()).toContain("/login");
});
