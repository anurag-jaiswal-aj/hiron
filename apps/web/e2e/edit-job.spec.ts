import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Edit Job Workflows", () => {
  test("pre-populates existing data and updates job successfully via PATCH API", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");

    const originalTitle = `Original Engineer ${Date.now()}`;
    const updatedTitle = `Updated Staff Engineer ${Date.now()}`;

    // 1. Create a job to edit
    await page.goto("/jobs/new");
    await page.waitForLoadState("networkidle");

    await page.fill("#job-title-input", originalTitle);
    await page.selectOption("#job-department-select", "Engineering");
    await page.fill("#job-location-input", "Chicago, IL");
    await page.fill("#job-description-textarea", "Original description text.");

    const reqSkillInput = page.locator("#job-req-skills-input");
    await reqSkillInput.fill("Node.js");
    await reqSkillInput.press("Enter");

    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs$/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    // 2. Click title to open detail page
    await page.click(`a:has-text("${originalTitle}")`);
    await page.waitForURL(/\/jobs\/[a-f0-9-]+$/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    // 3. Click Edit Job button
    await page.click('a:has-text("Edit Job")');
    await page.waitForURL(/\/jobs\/[a-f0-9-]+\/edit$/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    // 4. Verify existing fields pre-populated
    await expect(page.locator("#edit-job-title-input")).toHaveValue(originalTitle);
    await expect(page.locator("#edit-job-location-input")).toHaveValue("Chicago, IL");
    await expect(page.getByText("Node.js", { exact: true })).toBeVisible();

    // 5. Modify fields
    await page.fill("#edit-job-title-input", updatedTitle);
    await page.fill("#edit-job-location-input", "Remote / Boston, MA");
    await page.fill("#edit-job-desc-textarea", "Updated description after editing.");

    const editReqSkillInput = page.locator("#edit-job-req-skills-input");
    await editReqSkillInput.fill("TypeScript");
    await editReqSkillInput.press("Enter");

    // 6. Save changes
    await page.click('button[type="submit"]');

    // 7. Verify navigation back to detail page and persisted updates
    await page.waitForURL(/\/jobs\/[a-f0-9-]+$/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: updatedTitle })).toBeVisible();
    await expect(page.getByText("Remote / Boston, MA")).toBeVisible();
    await expect(page.getByText("Updated description after editing.")).toBeVisible();
    await expect(page.getByText("TypeScript")).toBeVisible();
  });

  test("validates experience range max >= min on edit form", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");

    // Navigate to create page to make temporary job
    const title = `Exp Validation Job ${Date.now()}`;
    await page.goto("/jobs/new");
    await page.waitForLoadState("networkidle");
    await page.fill("#job-title-input", title);
    await page.fill("#job-description-textarea", "Desc");
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs$/, { timeout: 10000 });
    await page.click(`a:has-text("${title}")`);
    await page.waitForURL(/\/jobs\/[a-f0-9-]+$/, { timeout: 10000 });
    await page.click('a:has-text("Edit Job")');

    // Enter invalid min/max exp
    await page.fill("#edit-job-exp-min-input", "15");
    await page.fill("#edit-job-exp-max-input", "5");

    await page.click('button[type="submit"]');

    await expect(
      page.getByText("Maximum experience years must be greater than or equal to minimum experience years.")
    ).toBeVisible();
  });

  test("recruiter can access edit job page", async ({ page }) => {
    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");

    // Navigate to create job to make temporary job
    const title = `Recruiter Job ${Date.now()}`;
    await page.goto("/jobs/new");
    await page.fill("#job-title-input", title);
    await page.fill("#job-description-textarea", "Recruiter job description.");
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs$/, { timeout: 10000 });
    await page.click(`a:has-text("${title}")`);
    await page.click('a:has-text("Edit Job")');

    await expect(page.getByRole("heading", { name: "Edit Job Description" })).toBeVisible();
  });

  test("hiring_manager cannot access edit job page and receives Access Denied", async ({ page }) => {
    await loginAs(page, "manager@acme.com", "SecurePassword123!");

    // Direct navigation attempt
    await page.goto("/jobs/00000000-0000-0000-0000-000000000000/edit");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Access Denied" })).toBeVisible();
    await expect(
      page.getByText("Only Organization Admins and Recruiters can edit job descriptions.")
    ).toBeVisible();
  });

  test("handles nonexistent job ID gracefully with error state", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");

    await page.goto("/jobs/00000000-0000-0000-0000-000000000000/edit");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Job Not Found" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Return to Jobs List" })).toBeVisible();
  });
});
