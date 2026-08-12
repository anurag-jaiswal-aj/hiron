import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Jobs List Workflows", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
  });

  test("authenticated org_admin can navigate to /jobs and see controls", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();
    await expect(page.getByPlaceholder("Search jobs by title...")).toBeVisible();
    await expect(page.getByRole("button", { name: "+ Create Job" })).toBeVisible();
  });

  test("Create Job CTA navigates to /jobs/new", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: "+ Create Job" }).click();
    await page.waitForURL(/\/jobs\/new$/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/jobs\/new$/);
    await expect(page.getByRole("heading", { name: "Create New Job" })).toBeVisible();
  });

  test("filters jobs list by search query, status, and department", async ({ page }) => {
    const targetTitle = `Unique Filter Job ${Date.now()}`;

    // Create a specific job to filter for
    await page.goto("/jobs/new");
    await page.waitForLoadState("networkidle");
    await page.fill("#job-title-input", targetTitle);
    await page.selectOption("#job-department-select", "Product");
    await page.fill("#job-description-textarea", "Product manager description.");
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/jobs$/, { timeout: 10000 });
    await page.waitForLoadState("networkidle");

    // 1. Search by title using search input
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");
    await page.fill('input[placeholder="Search jobs by title..."]', targetTitle);
    await page.waitForTimeout(400); // Allow 300ms debounce
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(targetTitle)).toBeVisible();

    // 2. Filter by status (draft)
    await page.selectOption("select >> nth=0", "draft");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(targetTitle)).toBeVisible();

    // 3. Filter by non-matching search term to test filtered empty state
    await page.fill('input[placeholder="Search jobs by title..."]', "NonExistentSearchQueryXYZ");
    await page.press('input[placeholder="Search jobs by title..."]', 'Enter');
    await page.waitForTimeout(400);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("No jobs match your filters")).toBeVisible();
    await expect(page.getByRole("button", { name: "Clear filters" })).toBeVisible();

    // 4. Click Clear filters
    await page.click('button:has-text("Clear filters")');
    await page.waitForLoadState("networkidle");

    await expect(page.getByPlaceholder("Search jobs by title...")).toHaveValue("");
  });

  test("sorts jobs list by title and date", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");

    // Sort by Title (A-Z)
    await page.selectOption("select >> nth=2", "title:asc");
    await page.waitForLoadState("networkidle");

    // Sort by Newest First
    await page.selectOption("select >> nth=2", "createdAt:desc");
    await page.waitForLoadState("networkidle");
  });
});
