import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import { loginAs } from "./helpers/auth";

test.describe("Candidate Creation Workflows", () => {
  const runId = Date.now();
  const testEmail = `newcand${runId}@example.com`;
  
  test.afterAll(() => {
    // Cleanup
    try {
      execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev`, {
        input: `DELETE FROM candidates WHERE email = '${testEmail}';`
      });
    } catch (e) {
      const err = e as { stdout?: { toString: () => string }; stderr?: { toString: () => string } };
      console.error("Cleanup failed:", err?.stdout?.toString(), err?.stderr?.toString());
    }
  });

  test("authorized user can navigate to creation UI and create a candidate successfully", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    
    // Navigate from Candidates List
    await page.goto("/candidates");
    await page.getByRole("button", { name: "+ Add Candidate" }).click();
    await page.waitForURL("**/candidates/new");
    
    // Verify required field validation
    // The button is disabled if fullName is empty, so we expect it to be disabled.
    await expect(page.getByRole("button", { name: "Create Candidate" })).toBeDisabled();

    // Fill form
    await page.fill('input#fullName', `New Candidate ${runId}`);
    await page.fill('input#email', testEmail);
    await page.fill('input#phone', "555-0101");
    await page.fill('input#location', "New York");
    await page.fill('input#linkedinUrl', "https://linkedin.com/in/newcand");
    await page.fill('input#currentTitle', "Backend Engineer");
    await page.fill('input#currentCompany', "Startup Inc");
    await page.fill('input#totalExperience', "3");
    
    // Add Skills
    await page.getByPlaceholder("Type a skill and press Enter...").fill("Python");
    await page.keyboard.press("Enter");
    await page.getByPlaceholder("+ Add skill").fill("Django");
    await page.keyboard.press("Enter");

    await page.fill('textarea#summary', "A great backend engineer");

    // Submit
    await page.getByRole("button", { name: "Create Candidate" }).click();

    // Verify data rendered on detail page
    await expect(page.locator("h1")).toContainText(`New Candidate ${runId}`);
    await expect(page.getByText("Backend Engineer @ Startup Inc")).toBeVisible();
    await expect(page.getByText(testEmail)).toBeVisible();
    await expect(page.getByText("3 years")).toBeVisible();
    await expect(page.getByText("Python")).toBeVisible();
    await expect(page.getByText("Django")).toBeVisible();
  });

  test("duplicate email conflict handling works", async ({ page }) => {
    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");
    await page.goto("/candidates/new");

    // We use the same email we just created
    await page.fill('input#fullName', `Duplicate Candidate ${runId}`);
    await page.fill('input#email', testEmail);
    await page.getByRole("button", { name: "Create Candidate" }).click();

    // Verify error state
    await expect(page.getByText("A candidate with this email already exists in your organization.")).toBeVisible();
  });

  test("hiring_manager is denied access to candidate creation", async ({ page }) => {
    await loginAs(page, "manager@acme.com", "SecurePassword123!");
    await page.goto("/candidates/new");
    
    await expect(page.getByText("Access Denied")).toBeVisible();
    await expect(page.getByText("You do not have permission to create candidates.")).toBeVisible();
  });
});
