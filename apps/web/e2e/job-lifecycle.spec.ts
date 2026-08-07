import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Job Lifecycle Workflows", () => {
  test("executes open, pause, close, and archive transitions correctly on Job Detail page", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");

    const title = `Lifecycle Job ${Date.now()}`;

    // 1. Create a job (defaults to draft status)
    await page.goto("/jobs/new");
    await page.waitForLoadState("networkidle");
    await page.fill("#job-title-input", title);
    await page.fill("#job-description-textarea", "Job created for testing lifecycle transitions.");
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs$/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    // Open detail page
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");
    await page.fill('input[placeholder="Search jobs by title..."]', title);
    await page.waitForTimeout(400);
    await page.click(`a:has-text("${title}")`);

    await page.waitForURL(/\/jobs\/[a-f0-9-]+$/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    // Verify initial Draft badge and Open Job button
    await expect(page.getByText("Draft", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Open Job" })).toBeVisible();

    // 2. Open Job
    await page.click('button:has-text("Open Job")');
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Open", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Pause Job" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Close Job" })).toBeVisible();

    // 3. Pause Job
    await page.click('button:has-text("Pause Job")');
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Paused", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Reopen Job" })).toBeVisible();

    // 4. Close Job
    await page.click('button:has-text("Close Job")');
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Closed", { exact: true })).toBeVisible();

    // 5. Test Archive Confirmation Modal & Archiving
    await page.click('button:has-text("Archive")');
    await expect(page.getByRole("heading", { name: "Archive Job Description?" })).toBeVisible();

    // Cancel modal first
    await page.click('button:has-text("Cancel")');
    await expect(page.getByRole("heading", { name: "Archive Job Description?" })).not.toBeVisible();

    // Open modal again and confirm
    await page.click('button:has-text("Archive")');
    await page.click('button:has-text("Archive Job")');

    // Should redirect to /jobs
    await page.waitForURL(/\/jobs$/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    // Verify archived job is excluded from active jobs list
    await page.fill('input[placeholder="Search jobs by title..."]', title);
    await page.waitForTimeout(400);
    await expect(page.getByText(title)).not.toBeVisible();
  });

  test("hiring_manager sees read-only detail view without lifecycle controls", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");

    const title = `HM ReadOnly Job ${Date.now()}`;
    await page.goto("/jobs/new");
    await page.fill("#job-title-input", title);
    await page.fill("#job-description-textarea", "Description for read only test.");
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs$/, { timeout: 10000 });
    await page.fill('input[placeholder="Search jobs by title..."]', title);
    await page.waitForTimeout(400);
    await page.click(`a:has-text("${title}")`);
    await page.waitForURL(/\/jobs\/[a-zA-Z0-9-]+$/);
    await expect(page.getByRole("heading", { name: title })).toBeVisible();

    const jobUrl = page.url();

    // Log out first
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.click('button:has-text("Sign Out"), a:has-text("Sign Out")');
    await page.waitForURL(/\/login/);
    
    // Log in as Hiring Manager
    await loginAs(page, "manager@acme.com", "SecurePassword123!");
    await page.goto(jobUrl);
    await page.waitForLoadState("networkidle");


    await expect(page.getByRole("heading", { name: title })).toBeVisible();
    await expect(page.getByRole("link", { name: "Edit Job" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Open Job" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Archive" })).not.toBeVisible();
  });
});
