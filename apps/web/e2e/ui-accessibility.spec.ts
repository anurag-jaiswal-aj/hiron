import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { loginAs } from "./helpers/auth";

/**
 * Axe-core Accessibility Audit — WCAG 2.2 AA
 *
 * Covers the 14 implemented application screens.
 * 3 screens from the UI/UX Design Specification are not implemented:
 *   - Forgot Password (no route)
 *   - Tenant Settings (no route)
 *   - Profile (no route)
 *
 * Each test:
 * 1. Navigates to the screen
 * 2. Waits for meaningful UI content to render
 * 3. Runs axe-core with WCAG 2.2 AA tags
 * 4. Asserts zero critical and zero serious violations
 * 5. Logs violations for diagnostic purposes
 */

interface AxeViolation {
  id: string;
  impact?: string;
  description: string;
  helpUrl: string;
  nodes: Array<{ target: string[]; html: string }>;
}

function logViolations(violations: AxeViolation[], screenName: string): void {
  if (violations.length > 0) {
    console.log(`\n[Axe] ${screenName}: ${violations.length} violation(s) found`);
    for (const v of violations) {
      console.log(`  [${v.impact}] ${v.id}: ${v.description}`);
      console.log(`    Help: ${v.helpUrl}`);
      for (const node of v.nodes) {
        console.log(`    Target: ${node.target.join(", ")}`);
        console.log(`    HTML: ${node.html.substring(0, 200)}`);
      }
    }
  }
}

async function runAxeAudit(
  page: import("@playwright/test").Page,
  screenName: string
): Promise<void> {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();

  logViolations(results.violations, screenName);

  const critical = results.violations.filter((v) => v.impact === "critical");
  const serious = results.violations.filter((v) => v.impact === "serious");

  expect(
    critical,
    `${screenName}: Found ${critical.length} critical accessibility violation(s):\n${critical.map((v) => `  - ${v.id}: ${v.description}`).join("\n")}`
  ).toHaveLength(0);

  expect(
    serious,
    `${screenName}: Found ${serious.length} serious accessibility violation(s):\n${serious.map((v) => `  - ${v.id}: ${v.description}`).join("\n")}`
  ).toHaveLength(0);
}

// ─── Unauthenticated Screen ─────────────────────────────────────────

test.describe("Accessibility: Login", () => {
  test("Login page has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/login");
    await page.waitForSelector("#email", { state: "visible" });
    await runAxeAudit(page, "Login");
  });
});

// ─── Authenticated Screens ──────────────────────────────────────────

test.describe("Accessibility: Authenticated Screens", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test("Dashboard has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await runAxeAudit(page, "Dashboard");
  });

  test("Jobs List has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");
    await runAxeAudit(page, "Jobs List");
  });

  test("Create Job has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/jobs/new");
    await page.waitForSelector("#job-title-input", { state: "visible" });
    await runAxeAudit(page, "Create Job");
  });

  test("Job Detail has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForTimeout(1000);
    const firstJobLink = page.locator("a[href^='/jobs/']").first();
    if (await firstJobLink.count() > 0) {
      await firstJobLink.click();
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);
      await runAxeAudit(page, "Job Detail");
    } else {
      test.skip(true, "No jobs available to test Job Detail screen");
    }
  });

  test("Edit Job has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForTimeout(1000);
    const firstJobLink = page.locator("a[href^='/jobs/']").first();
    if (await firstJobLink.count() > 0) {
      const href = await firstJobLink.getAttribute("href");
      if (href) {
        await page.goto(`${href}/edit`);
        await page.waitForLoadState("networkidle");
        await page.waitForTimeout(1000);
        await runAxeAudit(page, "Edit Job");
      }
    } else {
      test.skip(true, "No jobs available to test Edit Job screen");
    }
  });

  test("Candidates List has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/candidates");
    await page.waitForLoadState("networkidle");
    await runAxeAudit(page, "Candidates List");
  });

  test("Candidate Detail has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/candidates");
    await page.waitForTimeout(1000);
    const firstRow = page.locator("tbody tr").first();
    if (await firstRow.count() > 0) {
      await firstRow.click();
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);
      await runAxeAudit(page, "Candidate Detail");
    } else {
      test.skip(true, "No candidates available to test Candidate Detail screen");
    }
  });

  test("Create Candidate has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/candidates/new");
    await page.waitForLoadState("networkidle");
    await runAxeAudit(page, "Create Candidate");
  });

  test("Resume Upload has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/candidates/upload");
    await page.waitForLoadState("networkidle");
    await runAxeAudit(page, "Resume Upload");
  });

  test("Semantic Search has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/search");
    await page.waitForLoadState("networkidle");
    await runAxeAudit(page, "Semantic Search");
  });

  test("User Management has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/users");
    await page.waitForLoadState("networkidle");
    await runAxeAudit(page, "User Management");
  });

  test("Audit Logs has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/audit-logs");
    await page.waitForLoadState("networkidle");
    await runAxeAudit(page, "Audit Logs");
  });

  test("AI Usage Analytics has no critical or serious WCAG 2.2 AA violations", async ({ page }) => {
    await page.goto("/ai-usage");
    await page.waitForLoadState("networkidle");
    await runAxeAudit(page, "AI Usage Analytics");
  });
});
