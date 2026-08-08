import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Semantic Search Foundation", () => {
  // Use sequential mode because tests might interfere if running in parallel on the same user
  test.describe.configure({ mode: 'serial' });
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

  test("should execute a semantic search and render result cards", async ({ page }) => {
    // Checkpoint 3 testing: Search execution and result rendering
    await loginAs(page, "recruiter@acme.com");
    await page.goto("/search");

    // Mock search API
    await page.route("**/api/v1/search/candidates", async (route) => {
      console.log("MOCKED SEARCH API HIT!");
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        json: {
          data: [
            {
              candidate: {
                id: "c1",
                fullName: "Jane Smith",
                currentTitle: "Sr. SWE",
                skills: ["React"],
                totalExperienceYears: 8
              },
              relevanceScore: 0.94,
              highlights: ["React expert"]
            }
          ],
          pagination: { hasMore: false, totalCount: 1 }
        }
      });
    });

    page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));

    const searchInput = page.getByPlaceholder("Try: 'Senior backend engineers with fintech experience who know Python'");
    await searchInput.fill("React developers");
    await page.getByRole("button", { name: "Search" }).click();

    // Verify results load
    await expect(page.getByText("results • Searched in")).toBeVisible({ timeout: 15000 });

    // Result cards should have % match badge
    await expect(page.getByText("%Match").first()).toBeVisible();
    await expect(page.getByText("Why they matched").first()).toBeVisible();
  });

  test("should open save search modal and save successfully", async ({ page }) => {
    // Checkpoint 3 testing: Save Search
    await loginAs(page, "recruiter@acme.com");
    await page.goto("/search");

    // Execute search to show "Save this search" button
    const searchInput = page.getByPlaceholder("Try: 'Senior backend engineers with fintech experience who know Python'");
    await searchInput.fill("Data Scientists");

    // Mock search API to return empty results just to show the button
    await page.route("**/api/v1/search/candidates", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: [
            {
              candidate: { id: "c1", fullName: "Jane Smith", currentTitle: "Data Scientist", skills: ["Python"], totalExperienceYears: 5 },
              relevanceScore: 0.85,
              highlights: ["Python"]
            }
          ],
          pagination: { hasMore: false, totalCount: 1 }
        }
      });
    });

    await page.getByRole("button", { name: "Search" }).click();

    // Wait for results
    await expect(page.getByText("results • Searched in")).toBeVisible({ timeout: 15000 });

    // Click Save this search
    await page.getByRole("button", { name: "Save this search" }).click();
    await expect(page.getByRole("heading", { name: "Save Search" })).toBeVisible();

    // Fill modal and save
    await page.getByLabel("Search Name").fill("Test E2E Data Scientists Search");

    // Set up request interception to mock success if backend is flaky or no DB connected
    await page.route("**/api/v1/saved-searches", async (route) => {
      await route.fulfill({ status: 201, json: { data: { id: "test-id" } } });
    });

    await page.getByRole("button", { name: "Save Search", exact: true }).click();

    // Verify success state
    await expect(page.getByText("Search saved successfully!")).toBeVisible();
  });
});
