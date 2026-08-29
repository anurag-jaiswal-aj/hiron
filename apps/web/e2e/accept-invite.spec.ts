import { test, expect } from "@playwright/test";

test.describe("Public Accept Invitation Flow", () => {
  const MOCK_TOKEN = "test-invitation-token-12345678901234567890";

  test("missing token displays invalid invitation state", async ({ page }) => {
    await page.goto("/accept-invite");
    await expect(page.getByText("Invalid Invitation", { exact: true })).toBeVisible();
    await expect(page.getByText("This invitation link is invalid or incomplete.")).toBeVisible();
    await expect(page.getByRole("link", { name: "Back to Login" })).toBeVisible();
    await expect(page.locator("form")).not.toBeVisible();
  });

  test("valid token renders password form", async ({ page }) => {
    await page.goto(`/accept-invite?token=${MOCK_TOKEN}`);
    await expect(page.getByRole("heading", { name: "HIRON" })).toBeVisible();
    await expect(page.getByText("Set your password to activate your Hiron account.")).toBeVisible();

    // Check fields exist
    await expect(page.getByLabel("New Password *", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Confirm New Password *")).toBeVisible();
    await expect(page.getByRole("button", { name: "Accept Invitation" })).toBeVisible();

    // Verify token is not rendered visibly
    const pageText = await page.innerText("body");
    expect(pageText).not.toContain(MOCK_TOKEN);
  });

  test("empty password is rejected by HTML5 validation", async ({ page }) => {
    await page.goto(`/accept-invite?token=${MOCK_TOKEN}`);
    await page.getByRole("button", { name: "Accept Invitation" }).click();

    // The browser prevents submission because of `required`
    // Wait a short bit to ensure no API calls are made.
    let apiCalled = false;
    await page.route("**/api/v1/users/invite/accept", () => {
      apiCalled = true;
    });

    await page.waitForTimeout(500);
    expect(apiCalled).toBe(false);
  });

  test("short password is rejected by custom validation", async ({ page }) => {
    await page.goto(`/accept-invite?token=${MOCK_TOKEN}`);
    await page.getByLabel("New Password *", { exact: true }).fill("short");
    await page.getByLabel("Confirm New Password *").fill("short");

    await page.getByRole("button", { name: "Accept Invitation" }).click();
    await expect(page.getByText("Password must be at least 8 characters long.")).toBeVisible();
  });

  test("mismatched passwords are rejected by custom validation", async ({ page }) => {
    await page.goto(`/accept-invite?token=${MOCK_TOKEN}`);
    await page.getByLabel("New Password *", { exact: true }).fill("SecurePassword123!");
    await page.getByLabel("Confirm New Password *").fill("SecurePassword1234");

    await page.getByRole("button", { name: "Accept Invitation" }).click();
    await expect(page.getByText("Passwords do not match.")).toBeVisible();
  });

  test("valid password submission calls API and shows success state", async ({ page }) => {
    let apiRequestPayload: Record<string, string> | null = null;

    await page.route("**/api/v1/users/invite/accept", async (route) => {
      apiRequestPayload = route.request().postDataJSON();
      // Simulate network delay to check button state
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        json: { data: { status: "invitation_accepted" } },
      });
    });

    await page.goto(`/accept-invite?token=${MOCK_TOKEN}`);

    // Fill out form
    await page.getByLabel("New Password *", { exact: true }).fill("SecurePassword123!");
    await page.getByLabel("Confirm New Password *").fill("SecurePassword123!");

    const submitBtn = page.getByRole("button", { name: "Accept Invitation" });
    await submitBtn.click();

    // Check loading state (duplicate submission prevention)
    await expect(page.getByRole("button", { name: "Accepting Invitation..." })).toBeVisible();
    await expect(page.getByRole("button", { name: "Accepting Invitation..." })).toBeDisabled();

    // Wait for success message
    await expect(page.getByText("Invitation Accepted", { exact: true })).toBeVisible();
    await expect(
      page.getByText("Your account is ready. You can now sign in with your new password."),
    ).toBeVisible();

    const loginLink = page.getByRole("link", { name: "Proceed to Sign In" });
    await expect(loginLink).toBeVisible();
    await expect(loginLink).toHaveAttribute("href", "/login");

    // Verify API payload contract
    expect(apiRequestPayload).not.toBeNull();
    expect(apiRequestPayload.token).toBe(MOCK_TOKEN);
    expect(apiRequestPayload.password).toBe("SecurePassword123!");
    expect(apiRequestPayload.confirm_password).toBeUndefined();
    expect(apiRequestPayload.confirmPassword).toBeUndefined();

    // Verify token is never written to localStorage or sessionStorage
    const localStorageToken = await page.evaluate(() => localStorage.getItem("token"));
    expect(localStorageToken).toBeNull();

    const sessionStorageToken = await page.evaluate(() => sessionStorage.getItem("token"));
    expect(sessionStorageToken).toBeNull();
  });

  test("400 response displays generic invalid invitation message", async ({ page }) => {
    await page.route("**/api/v1/users/invite/accept", async (route) => {
      await route.fulfill({
        status: 400,
        json: { error: { code: "INVALID_TOKEN", message: "Specific internal error string" } },
      });
    });

    await page.goto(`/accept-invite?token=${MOCK_TOKEN}`);
    await page.getByLabel("New Password *", { exact: true }).fill("SecurePassword123!");
    await page.getByLabel("Confirm New Password *").fill("SecurePassword123!");
    await page.getByRole("button", { name: "Accept Invitation" }).click();

    await expect(
      page.getByText(
        "This invitation link is invalid or has expired. Please ask your administrator to send you a new invitation.",
      ),
    ).toBeVisible();

    // Ensure raw token is not in the error message
    const pageText = await page.innerText("body");
    expect(pageText).not.toContain(MOCK_TOKEN);
  });

  test("429 response displays rate limit message", async ({ page }) => {
    await page.route("**/api/v1/users/invite/accept", async (route) => {
      await route.fulfill({
        status: 429,
        json: { error: { code: "RATE_LIMIT_EXCEEDED", message: "Too many requests" } },
      });
    });

    await page.goto(`/accept-invite?token=${MOCK_TOKEN}`);
    await page.getByLabel("New Password *", { exact: true }).fill("SecurePassword123!");
    await page.getByLabel("Confirm New Password *").fill("SecurePassword123!");
    await page.getByRole("button", { name: "Accept Invitation" }).click();

    await expect(
      page.getByText("Too many attempts. Please wait a few minutes and try again."),
    ).toBeVisible();
  });

  test("500 response displays generic error", async ({ page }) => {
    await page.route("**/api/v1/users/invite/accept", async (route) => {
      await route.fulfill({
        status: 500,
        json: { error: { code: "INTERNAL_ERROR", message: "Database connection failed" } },
      });
    });

    await page.goto(`/accept-invite?token=${MOCK_TOKEN}`);
    await page.getByLabel("New Password *", { exact: true }).fill("SecurePassword123!");
    await page.getByLabel("Confirm New Password *").fill("SecurePassword123!");
    await page.getByRole("button", { name: "Accept Invitation" }).click();

    await expect(page.getByText("Something went wrong. Please try again later.")).toBeVisible();
  });
});
