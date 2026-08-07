import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("RBAC Permissions", () => {
  test("org_admin can access /jobs/new and create job", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/jobs/new");
    await expect(page.getByRole("heading", { name: "Create New Job" })).toBeVisible();
  });

  test("recruiter can access /jobs/new and create job", async ({ page }) => {
    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");
    await page.goto("/jobs/new");
    await expect(page.getByRole("heading", { name: "Create New Job" })).toBeVisible();
  });

  test("hiring_manager cannot see Create Job CTA on /jobs", async ({ page }) => {
    await loginAs(page, "manager@acme.com", "SecurePassword123!");
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("link", { name: "+ Create Job" })).not.toBeVisible();
    await expect(page.getByRole("link", { name: "+ Create your first job" })).not.toBeVisible();
  });

  test("direct navigation by hiring_manager to /jobs/new displays Access Denied", async ({ page }) => {
    await loginAs(page, "manager@acme.com", "SecurePassword123!");
    await page.goto("/jobs/new");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Access Denied" })).toBeVisible();
    await expect(
      page.getByText("Only Organization Admins and Recruiters can create new job descriptions.")
    ).toBeVisible();
  });
});
