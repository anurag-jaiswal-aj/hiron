import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Authentication Workflows", () => {
  test("unauthenticated access to /jobs redirects to /login", async ({ page }) => {

    await page.goto("/jobs");
    await page.waitForURL(/\/login$/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/login$/);
  });

  test("unauthenticated access to /jobs/new redirects to /login", async ({ page }) => {

    await page.goto("/jobs/new");
    await page.waitForURL(/\/login$/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/login$/);
  });

  test("valid org_admin can log in successfully", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  });

  test("authenticated session survives navigation", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/jobs");
    await expect(page).toHaveURL(/\/jobs$/);
    await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();

    await page.goto("/");
    await expect(page).toHaveURL(/\/$/);
  });
});
