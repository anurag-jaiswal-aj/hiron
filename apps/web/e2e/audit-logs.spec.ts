import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Audit Logs Page", () => {
  test("redirects unauthorized roles (hiring_manager)", async ({ page }) => {
    await loginAs(page, "manager@acme.com");
    await page.goto("/audit-logs");

    // Should be redirected to /
    await page.waitForURL((url) => url.pathname !== "/audit-logs", { timeout: 10000 });
    expect(page.url()).not.toContain("/audit-logs");
  });

  test("allows org_admin to access audit logs and verifies UI elements", async ({ page }) => {
    await loginAs(page, "admin@acme.com");
    await page.goto("/audit-logs");

    // Check page title
    await expect(page.getByRole("heading", { name: "Audit Logs" })).toBeVisible();

    // Wait for table or empty state to load
    const tableLocator = page.locator("table");
    const emptyStateLocator = page.getByText("No audit history");
    await expect(tableLocator.or(emptyStateLocator).first()).toBeVisible({ timeout: 15000 });

    // Check if table has rows
    const rows = page.locator("tbody tr");
    const count = await rows.count();

    if (count > 0 && !(await rows.first().locator("text=No audit logs found").isVisible())) {
      // Test filtering
      await page.locator("select#audit-filter-action").selectOption("created");
      // Table should update
      await page.waitForTimeout(1000); // Wait for debounce and fetch

      // Test detail modal
      const viewChangesBtn = page.getByRole("button", { name: "View Changes" }).first();
      if (await viewChangesBtn.isVisible()) {
        await viewChangesBtn.click();
        await expect(page.getByRole("dialog")).toBeVisible();
        await expect(page.getByText("Audit Event Details:")).toBeVisible();
        await page.getByRole("button", { name: "Close" }).click();
        await expect(page.getByRole("dialog")).toBeHidden();
      }

      // Test empty state
      await page.locator("select#audit-filter-action").selectOption("login_failed"); // Assuming none
      await page.locator("input#audit-filter-entity-id").fill("not-a-uuid");
      await page.waitForTimeout(1000);
      await expect(page.getByText("No matches found")).toBeVisible();

      // Reset filters
      await page.getByRole("button", { name: "Clear Filters" }).click();
      await page.waitForTimeout(1000);
      await expect(page.getByText("No matches found")).toBeHidden();

      // Test pagination (Load More) if visible
      const loadMoreBtn = page.getByRole("button", { name: "Load More" });
      if (await loadMoreBtn.isVisible()) {
        const initialRowCount = await rows.count();
        const responsePromise = page.waitForResponse(
          (r) => r.url().includes("/api/v1/audit-logs") && r.status() === 200,
        );
        await loadMoreBtn.click();
        await responsePromise;
        await expect(page.getByText("Loading more logs...")).toBeHidden();

        // Verify the additional logs are actually loaded
        await expect(async () => {
          expect(await rows.count()).toBeGreaterThan(initialRowCount);
        }).toPass({ timeout: 5000 });
      }
    } else {
      // Empty state
      await expect(page.getByText("No audit history")).toBeVisible();
    }
  });

  test("allows recruiter to access audit logs", async ({ page }) => {
    await loginAs(page, "recruiter@acme.com");
    await page.goto("/audit-logs");

    await expect(page.getByRole("heading", { name: "Audit Logs" })).toBeVisible();
    await expect(page.getByText("(Viewing only your own actions)")).toBeVisible();
  });
});
