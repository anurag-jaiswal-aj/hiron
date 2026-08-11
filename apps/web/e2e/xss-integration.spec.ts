import { test, expect } from "@playwright/test";

test.describe("XSS Integration in CandidateNotesTab", () => {
  test("dangerouslySetInnerHTML is sanitized in the actual rendered component", async ({ page }) => {
    page.on("console", msg => console.log("BROWSER CONSOLE:", msg.text()));
    page.on("pageerror", err => console.log("BROWSER ERROR:", err.message));

    // 1. Mock authentication so the app thinks we are logged in
    await page.route("**/api/v1/auth/refresh", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: {
            accessToken: "fake-token",
            tokenType: "Bearer",
            expiresIn: 3600
          }
        },
      });
    });

    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: {
            id: "user-1",
            email: "test@example.com",
            fullName: "Test Admin",
            role: "org_admin",
          },
        },
      });
    });

    // 2. Mock Candidate Details
    await page.route("**/api/v1/candidates/cand-123", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: {
            id: "cand-123",
            firstName: "John",
            lastName: "Doe",
            email: "john@example.com",
            stages: []
          },
        },
      });
    });

    // 3. Mock Candidate Notes with Malicious Payloads
    const maliciousNote = {
      id: "note-1",
      content: "Hello <script>alert(1)</script><img src=x onerror=alert(2)><svg onload=alert(3)><a href=\"javascript:alert(4)\">click</a> <b>safe</b>",
      authorId: "user-1",
      isPrivate: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      author: {
        id: "user-1",
        email: "test@example.com",
        fullName: "Test Admin",
        role: "org_admin"
      }
    };

    await page.route("**/api/v1/candidates/cand-123/notes*", async (route) => {
      await route.fulfill({
        status: 200,
        json: { data: [maliciousNote] },
      });
    });

    // We also mock the dashboard summary just in case the app fetches it concurrently or preloads
    await page.route("**/api/v1/dashboard/summary*", async (route) => {
      await route.fulfill({ status: 200, json: { data: {} } });
    });

    // We also mock candidates list
    await page.route("**/api/v1/candidates*", async (route) => {
      await route.fulfill({ status: 200, json: { data: [], total: 0, page: 1, pageSize: 10 } });
    });

    // 4. Navigate to the candidate page
    await page.goto("/candidates/cand-123");

    // Ensure we are not redirected to login
    await expect(page).not.toHaveURL(/\/login/);

    // 5. Switch to Notes tab
    await page.getByRole("button", { name: "Notes" }).click();

    // Wait for the note to render
    const noteContainer = page.locator('.tiptap-content');
    await expect(noteContainer).toBeVisible({ timeout: 10000 });

    // 6. Inspect the actual rendered DOM
    const htmlContent = await noteContainer.innerHTML();

    // Verify scripts are removed
    expect(htmlContent).not.toContain("<script>");
    expect(htmlContent).not.toContain("onerror");
    expect(htmlContent).not.toContain("onload");

    // Verify javascript: protocol is sanitized
    // (DOMPurify usually replaces it with 'about:blank' or removes it entirely)
    expect(htmlContent).not.toContain("javascript:alert(4)");

    // Verify safe HTML remains
    expect(htmlContent).toContain("<b>safe</b>");
  });
});
