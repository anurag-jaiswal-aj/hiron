import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Tenant Settings Management", () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate as org_admin
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
  });

  test("org_admin can access Settings and update organization name", async ({ page }) => {
    // 1. org_admin can access Settings
    await page.click("text=Settings");
    await expect(page).toHaveURL(/.*\/settings/);
    await expect(page.locator("h1")).toHaveText("Workspace Settings");

    // 2. Settings displays the current organization name
    const orgNameInput = page.locator("input#orgName");
    const workspaceUrlInput = page.locator("input#workspaceUrl");
    const planInput = page.locator("input#plan");

    await expect(orgNameInput).toBeVisible();
    await expect(workspaceUrlInput).toBeDisabled();
    await expect(planInput).toBeDisabled();

    // 3. org_admin can update organization name
    const runId = Date.now().toString().slice(-4);
    const newName = `Acme Corp ${runId}`;

    await orgNameInput.fill(newName);

    const saveButton = page.locator('button[type="submit"]');
    await saveButton.click();

    // 4. Updated organization name is reflected in the UI
    await expect(page.locator("text=Workspace settings updated successfully.")).toBeVisible();
    await expect(orgNameInput).toHaveValue(newName);

    // 5. Restore original name to avoid polluting shared DB fixtures
    await orgNameInput.fill("Acme Corp");
    await saveButton.click();
    await expect(page.locator("text=Workspace settings updated successfully.")).toBeVisible();
    await expect(orgNameInput).toHaveValue("Acme Corp");
  });

  test("Empty organization name produces validation feedback", async ({ page }) => {
    await page.goto("/settings");

    // 5. Empty organization name produces validation feedback
    const orgNameInput = page.locator("input#orgName");
    await orgNameInput.fill("");

    const saveButton = page.locator('button[type="submit"]');
    await saveButton.click({ force: true });

    await expect(page.locator("text=Organization name is required.")).toBeVisible();
  });

  test("API failure produces appropriate UI feedback", async ({ page }) => {
    await page.goto("/settings");

    // 8. API failure produces appropriate UI feedback
    await page.route("**/api/v1/tenants/*", async (route) => {
      if (route.request().method() === "PATCH") {
        await route.fulfill({
          status: 500,
          json: {
            error: {
              message: "Simulated backend error for settings update",
            },
          },
        });
      } else {
        await route.continue();
      }
    });

    const orgNameInput = page.locator("input#orgName");
    await orgNameInput.fill("Trigger Error Name");

    const saveButton = page.locator('button[type="submit"]');
    await saveButton.click();

    await expect(page.locator("text=Simulated backend error for settings update")).toBeVisible();
  });
});

test.describe("Settings - Non-Admin Access", () => {
  test("non-org_admin cannot access Settings and does not see the link", async ({ page }) => {
    // Authenticate as a regular recruiter
    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");

    // 7. Settings link is not available to non-org_admin users
    const settingsLink = page.locator(".sidebar").locator("text=Settings");
    await expect(settingsLink).not.toBeVisible();

    // 6. Non-org_admin cannot access Settings route
    await page.goto("/settings");
    await expect(page.locator("text=Access Denied")).toBeVisible();
    await expect(
      page.locator("text=You do not have permission to view workspace settings."),
    ).toBeVisible();
  });
});
