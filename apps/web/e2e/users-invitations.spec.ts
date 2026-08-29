import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Users Admin Page - Invitations", () => {
  test.beforeEach(async ({ page }) => {
    // Intercept the users list API to mock the response
    await page.route("**/api/v1/users*", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          json: {
            data: [
              {
                id: "user-verified-1",
                tenantId: "tenant-1",
                email: "verified@acme.com",
                fullName: "Verified User",
                role: "recruiter",
                isActive: true,
                isEmailVerified: true,
                createdAt: "2026-08-01T00:00:00Z",
              },
              {
                id: "user-pending-1",
                tenantId: "tenant-1",
                email: "pending@acme.com",
                fullName: "Pending User",
                role: "hiring_manager",
                isActive: true,
                isEmailVerified: false,
                createdAt: "2026-08-02T00:00:00Z",
              },
              {
                id: "user-inactive-1",
                tenantId: "tenant-1",
                email: "inactive@acme.com",
                fullName: "Inactive User",
                role: "recruiter",
                isActive: false,
                isEmailVerified: false,
                createdAt: "2026-08-03T00:00:00Z",
              },
            ],
          },
        });
      } else {
        await route.fallback();
      }
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/users");
    await page.waitForLoadState("networkidle");
  });

  test("displays Pending badge for unverified active users", async ({ page }) => {
    // The Pending user row
    const pendingRow = page.locator("tr").filter({ hasText: "pending@acme.com" });
    await expect(pendingRow.getByText("Pending", { exact: true })).toBeVisible();

    // The Verified user row
    const verifiedRow = page.locator("tr").filter({ hasText: "verified@acme.com" });
    await expect(verifiedRow.getByText("Active")).toBeVisible();
    await expect(verifiedRow.getByText("Pending", { exact: true })).not.toBeVisible();
  });

  test("shows Resend Invite button only for unverified active users", async ({ page }) => {
    // The Pending user row
    const pendingRow = page.locator("tr").filter({ hasText: "pending@acme.com" });
    await expect(pendingRow.getByRole("button", { name: "Resend Invite" })).toBeVisible();

    // The Verified user row
    const verifiedRow = page.locator("tr").filter({ hasText: "verified@acme.com" });
    await expect(verifiedRow.getByRole("button", { name: "Resend Invite" })).not.toBeVisible();

    // The Inactive user row
    const inactiveRow = page.locator("tr").filter({ hasText: "inactive@acme.com" });
    await expect(inactiveRow.getByRole("button", { name: "Resend Invite" })).not.toBeVisible();
  });

  test("clicking Resend Invite calls API and shows success notification", async ({ page }) => {
    let resendApiCalled = false;
    await page.route("**/api/v1/users/user-pending-1/invite/resend", async (route) => {
      resendApiCalled = true;
      await route.fulfill({
        status: 200,
        json: { data: { status: "invitation_queued" } },
      });
    });

    const pendingRow = page.locator("tr").filter({ hasText: "pending@acme.com" });
    const resendBtn = pendingRow.getByRole("button", { name: "Resend Invite" });

    await resendBtn.click();

    // Wait for success toast
    await expect(
      page.getByText("Invitation resent successfully to pending@acme.com."),
    ).toBeVisible();
    expect(resendApiCalled).toBe(true);
  });

  test("handles resend failure with a safe error message", async ({ page }) => {
    await page.route("**/api/v1/users/user-pending-1/invite/resend", async (route) => {
      await route.fulfill({
        status: 429,
        json: {
          error: { code: "RATE_LIMIT_EXCEEDED", message: "Rate limit exceeded. Try again later." },
        },
      });
    });

    const pendingRow = page.locator("tr").filter({ hasText: "pending@acme.com" });
    const resendBtn = pendingRow.getByRole("button", { name: "Resend Invite" });

    await resendBtn.click();

    // Wait for error toast
    await expect(page.getByText("Rate limit exceeded. Try again later.")).toBeVisible();
  });

  test("can invite a new user successfully", async ({ page }) => {
    await page.route("**/api/v1/users/invite", async (route) => {
      await route.fulfill({
        status: 201,
        json: {
          data: { id: "new-user-1", email: "new@acme.com", fullName: "New", role: "recruiter" },
        },
      });
    });

    await page.getByRole("button", { name: "+ Invite User" }).click();

    // Expect modal to be open
    await expect(page.getByRole("heading", { name: "Invite Team Member" })).toBeVisible();

    await page.getByLabel("Email Address *").fill("new@acme.com");
    await page.getByLabel("Full Name *").fill("New Person");
    // Role defaults to recruiter, which is fine

    await page.getByRole("button", { name: "Send Invitation" }).click();

    // Modal closes, fetchUsers is called again
    await expect(page.getByRole("heading", { name: "Invite Team Member" })).not.toBeVisible();
  });
});
