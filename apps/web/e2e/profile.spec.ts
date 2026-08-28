import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Profile Management", () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate as a user
    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");
  });

  test("Authenticated user can view and edit their profile", async ({ page }) => {
    // 1. Authenticated user can open /profile via Sidebar
    await page.click("text=Profile");
    await expect(page).toHaveURL(/.*\/profile/);
    await expect(page.locator("h1")).toHaveText("Profile");

    // 2. Existing profile data renders
    const fullNameInput = page.locator('input#fullName');
    const emailInput = page.locator('input#email');
    
    await expect(fullNameInput).toBeVisible();
    await expect(emailInput).toHaveValue("recruiter@acme.com");
    await expect(emailInput).toBeDisabled();

    // 3. Valid profile changes can be saved
    const runId = Date.now().toString().slice(-4);
    const newName = `Test Recruiter ${runId}`;
    
    await fullNameInput.fill(newName);
    
    const saveButton = page.locator('button[type="submit"]');
    await saveButton.click();

    // Success feedback
    await expect(page.locator("text=Profile updated successfully.")).toBeVisible();
    
    // AuthContext/Sidebar updates
    const sidebarName = page.locator(".sidebar").locator(`text=${newName}`);
    await expect(sidebarName).toBeVisible();
  });

  test("Invalid input is handled correctly", async ({ page }) => {
    await page.goto("/profile");
    
    // Clear input
    const fullNameInput = page.locator('input#fullName');
    await fullNameInput.fill("");
    
    // 4. Invalid input prevents save or shows error
    const saveButton = page.locator('button[type="submit"]');
    // Button is likely disabled if HTML5 required is used, or JS blocks it.
    // Let's assume standard HTML5 validation kicks in or we show an error.
    await saveButton.click({ force: true }); 
    
    // Assuming our JS handler blocks empty string and sets error
    await expect(page.locator("text=Full name is required.")).toBeVisible();
  });

  test("API failure produces appropriate UI feedback", async ({ page }) => {
    await page.goto("/profile");
    
    // Intercept API call to force a failure
    await page.route("**/api/v1/users/*", async (route) => {
      await route.fulfill({
        status: 500,
        json: {
          error: {
            message: "Simulated backend error for profile update",
          }
        }
      });
    });

    const fullNameInput = page.locator('input#fullName');
    await fullNameInput.fill("Trigger Error Name");
    
    const saveButton = page.locator('button[type="submit"]');
    await saveButton.click();

    // 5. API failure UI feedback
    await expect(page.locator("text=Simulated backend error for profile update")).toBeVisible();
  });
});

test.describe("Profile - Unauthenticated Access", () => {
  test("Unauthenticated users cannot access the profile page", async ({ page }) => {
    // 6. Unauthenticated users redirected
    await page.goto("/profile");
    
    // Should be redirected to login
    await expect(page).toHaveURL(/.*\/login/);
  });
});
