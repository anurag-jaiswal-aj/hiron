import { expect, test } from "@playwright/test";
test.describe("Password Reset Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Ensure we are logged out
    await page.context().clearCookies();
    await page.goto("/login");
    try {
      await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
      });
    } catch {
      // Ignore
    }
  });

  test.describe("Forgot Password Route", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto("/forgot-password");
      await page.waitForLoadState("networkidle");
    });

    test("Logged-out user can open /forgot-password", async ({ page }) => {
      await expect(page.locator("h1")).toContainText("HIRON");
      await expect(page.getByText("Forgot Password")).toBeVisible();
      await expect(page.locator('input[type="email"]')).toBeVisible();
      await expect(page.locator('input[type="text"]')).toBeVisible();
    });

    test("Empty email validation works", async ({ page }) => {
      // Missing email, only tenant
      await page.fill("#tenantId", "00000000-0000-0000-0000-000000000000");
      await page.click('button[type="submit"]');

      // The browser's native HTML5 validation will trigger.
      // But if we bypass it, our React state validation should catch it.
      // To test HTML5 validation we just ensure the form hasn't submitted and no success state is shown
      await expect(page.getByText("Check your email")).toBeHidden();
    });

    test("Valid request shows generic confirmation", async ({ page }) => {
      // We'll mock the API so we don't trigger the real worker or rate limiting in this test
      await page.route("**/api/v1/auth/forgot-password", async (route) => {
        await route.fulfill({
          status: 202,
          json: {
            data: {
              message: "If an account exists for that email, a password reset link has been sent.",
            },
          },
        });
      });

      await page.fill("#email", "admin@acme.com");
      await page.fill("#tenantId", "00000000-0000-0000-0000-000000000000");
      await page.click('button[type="submit"]');

      await expect(page.getByText("Check your email")).toBeVisible();
      await expect(
        page.getByText(
          "If an account exists for that email, we've sent you a password reset link.",
        ),
      ).toBeVisible();
    });

    test("Existing vs nonexistent email produces the same public success behavior", async ({
      page,
    }) => {
      // For a non-existent email, the backend will return the same 202 response
      await page.route("**/api/v1/auth/forgot-password", async (route) => {
        await route.fulfill({
          status: 202,
          json: {
            data: {
              message: "If an account exists for that email, a password reset link has been sent.",
            },
          },
        });
      });

      await page.fill("#email", "doesnotexist@acme.com");
      await page.fill("#tenantId", "00000000-0000-0000-0000-000000000000");
      await page.click('button[type="submit"]');

      await expect(page.getByText("Check your email")).toBeVisible();
    });

    test("API failure displays a safe generic error", async ({ page }) => {
      await page.route("**/api/v1/auth/forgot-password", async (route) => {
        await route.fulfill({
          status: 500,
          json: { error: { code: "SERVER_ERROR", message: "Internal server error" } },
        });
      });

      await page.fill("#email", "admin@acme.com");
      await page.fill("#tenantId", "00000000-0000-0000-0000-000000000000");
      await page.click('button[type="submit"]');

      await expect(page.locator('div[role="alert"]:not(#__next-route-announcer__)')).toContainText(
        "Internal server error",
      );
      await expect(page.getByText("Check your email")).toBeHidden();
    });

    test("User can navigate back to login", async ({ page }) => {
      await page.click('text="Back to Sign In"');
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe("Reset Password Route", () => {
    test("Missing token is handled safely", async ({ page }) => {
      await page.goto("/reset-password");
      await page.waitForLoadState("networkidle");

      await expect(page.getByText("Invalid Link")).toBeVisible();
      await expect(
        page.getByText("This password reset link is invalid or has expired."),
      ).toBeVisible();
      await expect(page.locator('input[type="password"]')).toBeHidden();
    });

    test("Password mismatch validation works", async ({ page }) => {
      await page.goto("/reset-password?token=some_fake_token_value");
      await page.waitForLoadState("networkidle");

      await page.fill("#password", "SecurePassword123!");
      await page.fill("#confirmPassword", "DifferentPassword123!");
      await page.click('button[type="submit"]');

      await expect(page.locator('div[role="alert"]:not(#__next-route-announcer__)')).toContainText(
        "Passwords do not match.",
      );
    });

    test("Weak/invalid password validation works according to backend rules", async ({ page }) => {
      await page.goto("/reset-password?token=some_fake_token_value");
      await page.waitForLoadState("networkidle");

      await page.fill("#password", "short");
      await page.fill("#confirmPassword", "short");
      await page.click('button[type="submit"]');

      await expect(page.locator('div[role="alert"]:not(#__next-route-announcer__)')).toContainText(
        "Password must be at least 8 characters long.",
      );
    });

    test("Successful reset shows success state", async ({ page }) => {
      // 1. Use a mocked token since we mock the API response below for strict frontend isolation
      const validToken = "mock_valid_token_string";

      // 2. Navigate to the page with this token
      await page.goto(`/reset-password?token=${validToken}`);
      await page.waitForLoadState("networkidle");

      // 3. Submit a new password
      const newPassword = "NewSecurePassword123!";
      await page.fill("#password", newPassword);
      await page.fill("#confirmPassword", newPassword);

      await page.route("**/api/v1/auth/reset-password", async (route) => {
        await route.fulfill({ status: 200, json: { data: { message: "Success" } } });
      });
      const responsePromise = page.waitForResponse("**/api/v1/auth/reset-password");
      await page.click('button[type="submit"]');

      const response = await responsePromise;
      expect(response.status()).toBe(200);

      // 4. Verify success state UI
      await expect(page.getByText("Password Reset Complete")).toBeVisible();
      await expect(page.getByText("Your password has been successfully reset")).toBeVisible();

      // 5. Verify navigation to login
      await page.click('text="Proceed to Sign In"');
      await expect(page).toHaveURL(/\/login/);
    });

    test("Invalid/expired token shows safe error", async ({ page }) => {
      await page.goto("/reset-password?token=invalid_token_value_that_fails_in_db");
      await page.waitForLoadState("networkidle");

      await page.route("**/api/v1/auth/reset-password", async (route) => {
        await route.fulfill({
          status: 400,
          json: { error: { message: "Invalid or expired token" } },
        });
      });
      await page.fill("#password", "NewSecurePassword123!");
      await page.fill("#confirmPassword", "NewSecurePassword123!");
      await page.click('button[type="submit"]');

      await expect(page.locator('div[role="alert"]:not(#__next-route-announcer__)')).toContainText(
        "This password reset link is invalid or has expired.",
      );
    });

    test("API failure does not expose internal details", async ({ page }) => {
      // Mock the backend responding with an unexpected 500 error
      await page.route("**/api/v1/auth/reset-password", async (route) => {
        await route.fulfill({
          status: 500,
          json: {
            error: { code: "SERVER_ERROR", message: "Database connection failed internally" },
          },
        });
      });

      await page.goto("/reset-password?token=some_token");
      await page.waitForLoadState("networkidle");

      await page.fill("#password", "NewSecurePassword123!");
      await page.fill("#confirmPassword", "NewSecurePassword123!");
      await page.click('button[type="submit"]');

      // The UI should fallback to a safe generic message, not the internal message
      await expect(page.locator('div[role="alert"]:not(#__next-route-announcer__)')).toContainText(
        "An error occurred while resetting your password. Please try again.",
      );
    });
  });
});
