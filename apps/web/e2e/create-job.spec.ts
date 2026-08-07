import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Create Job Workflows", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
  });

  test("renders complete form and live preview elements", async ({ page }) => {
    await page.goto("/jobs/new");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Create New Job" })).toBeVisible();
    await expect(page.locator("#job-title-input")).toBeVisible();
    await expect(page.locator("#job-department-select")).toBeVisible();
    await expect(page.locator("#job-employment-select")).toBeVisible();
    await expect(page.locator("#job-location-input")).toBeVisible();
    await expect(page.locator("#job-exp-min-input")).toBeVisible();
    await expect(page.locator("#job-description-textarea")).toBeVisible();

    // Verify live preview header
    await expect(page.getByText("Live Preview", { exact: true })).toBeVisible();
  });

  test("validates experience range max >= min", async ({ page }) => {
    await page.goto("/jobs/new");
    await page.waitForLoadState("networkidle");

    await page.fill("#job-title-input", "Test Job Title");
    await page.fill("#job-description-textarea", "Valid description for testing.");
    await page.fill("#job-exp-min-input", "10");
    await page.fill("#job-exp-max-input", "5");

    await page.click('button[type="submit"]');

    await expect(
      page.getByText("Maximum experience years must be greater than or equal to minimum experience years.")
    ).toBeVisible();
  });

  test("updates live preview dynamically as user types", async ({ page }) => {
    await page.goto("/jobs/new");
    await page.waitForLoadState("networkidle");

    await page.fill("#job-title-input", "Lead AI Architect");
    await expect(page.getByRole("heading", { name: "Lead AI Architect" })).toBeVisible();

    await page.fill("#job-location-input", "Austin, TX");
    await expect(page.getByText("Austin, TX")).toBeVisible();
  });

  test("adds skill tags and creates job successfully through frontend", async ({ page }) => {
    const jobTitle = `Staff Backend Engineer ${Date.now()}`;

    await page.goto("/jobs/new");
    await page.waitForLoadState("networkidle");

    await page.fill("#job-title-input", jobTitle);
    await page.selectOption("#job-department-select", "Engineering");
    await page.selectOption("#job-employment-select", "full_time");
    await page.fill("#job-location-input", "Remote");
    await page.fill("#job-exp-min-input", "5");
    await page.fill("#job-exp-max-input", "10");
    await page.fill(
      "#job-description-textarea",
      "We are looking for a Staff Backend Engineer to design scalable distributed microservices."
    );

    // Add required skill
    const reqSkillInput = page.locator("#job-req-skills-input");
    await reqSkillInput.fill("Python");
    await reqSkillInput.press("Enter");
    await reqSkillInput.fill("FastAPI");
    await reqSkillInput.press("Enter");

    // Add preferred skill
    const prefSkillInput = page.locator("#job-pref-skills-input");
    await prefSkillInput.fill("Docker");
    await prefSkillInput.press("Enter");

    // Submit form
    await page.click('button[type="submit"]');

    // Verify redirect to /jobs
    await page.waitForURL(/\/jobs$/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/jobs$/);
    await page.waitForLoadState("networkidle");

    // Verify newly created job appears in Jobs List table
    await expect(page.getByText(jobTitle)).toBeVisible();
  });
});
