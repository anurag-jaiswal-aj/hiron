import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Semantic Search Foundation", () => {
  test("should render semantic search UI correctly for recruiter", async ({ page }) => {
    // Checkpoint 2 testing: Foundation UI presence
    await loginAs(page, "recruiter@acme.com");
    await page.goto("/search");

    // Verify page headers
    await expect(page.getByText("Semantic Search")).toBeVisible();
    await expect(page.getByText("Find candidates using natural language")).toBeVisible();

    // Verify search input
    const searchInput = page.getByPlaceholder("Try: 'Senior backend engineers with fintech experience who know Python'");
    await expect(searchInput).toBeVisible();

    // Type in search
    await searchInput.fill("React developers");
    await expect(searchInput).toHaveValue("React developers");

    // Verify filter actions (dummy interaction for CP2)
    await expect(page.getByText("No active filters")).toBeVisible();
    await page.getByRole("button", { name: "+ Add Filter" }).click();
    await expect(page.getByText("Exp:")).toBeVisible();
    await expect(page.getByText("5+ yrs")).toBeVisible();
  });

  test("should reject hiring managers from accessing search", async ({ page }) => {
    await loginAs(page, "manager@acme.com");
    
    const response = await page.goto("/search");
    
    // ProtectedRoute redirects unauthorized roles to Dashboard
    await page.waitForURL("**/");
    expect(page.url()).toContain("/");
  });
});
