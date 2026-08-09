import { test, expect } from "@playwright/test";

test.describe("Candidate Notes", () => {
  const candidateId = "cand-123";

  test.beforeEach(async ({ page }) => {
    page.on("console", (msg) => console.log("BROWSER LOG:", msg.type(), msg.text()));
    
    // Mock user context
    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: {
            id: "user-1",
            fullName: "Test Recruiter",
            role: "recruiter",
            email: "recruiter@example.com",
            tenantId: "tenant-1",
            isActive: true,
            isEmailVerified: true,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          },
        },
      });
    });

    await page.route("**/api/v1/auth/refresh", async (route) => {
      console.log("MOCK REACHED: /auth/refresh", route.request().method());
      await route.fulfill({
        status: 200,
        json: {
          data: { accessToken: "test-token" },
        },
      });
    });

    // Mock candidate detail
    await page.route(`**/api/v1/candidates/${candidateId}`, async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: {
            id: candidateId,
            fullName: "Jane Doe",
            email: "jane@example.com",
            skills: [],
            jobs: [],
            source: "manual",
            isArchived: false,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          },
        },
      });
    });

    // Mock resumes
    await page.route(`**/api/v1/resumes/candidate/${candidateId}`, async (route) => {
      await route.fulfill({
        status: 200,
        json: { data: [] },
      });
    });

    // Mock jobs
    await page.route(`**/api/v1/jobs`, async (route) => {
      await route.fulfill({
        status: 200,
        json: { data: [] },
      });
    });

    // Mock initial notes list (empty)
    await page.route(`**/api/v1/candidates/${candidateId}/notes`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          json: {
            data: [],
          },
        });
      } else if (route.request().method() === "POST") {
        const body = JSON.parse(route.request().postData() || "{}");
        await route.fulfill({
          status: 201,
          json: {
            data: {
              id: "note-1",
              candidateId,
              author: { id: "user-1", fullName: "Test Recruiter" },
              content: body.content,
              isPrivate: body.isPrivate,
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          },
        });
      } else {
        await route.fulfill({ status: 200, body: "" });
      }
    });

    // Mock tags list
    await page.route(`**/api/v1/candidates/${candidateId}/tags`, async (route) => {
      await route.fulfill({
        status: 200,
        json: { data: [] },
      });
    });

    // Mock users list for mentions
    await page.route(`**/api/v1/users?isActive=true&limit=100`, async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: [
            { id: "user-1", fullName: "Test Recruiter" },
            { id: "user-2", fullName: "Alice Admin" },
          ],
        },
      });
    });
    await page.route("**/api/v1/**", async (route) => {
      if (!route.request().url().includes("/notes") && 
          !route.request().url().includes("/candidates") && 
          !route.request().url().includes("/auth") &&
          !route.request().url().includes("/tags") &&
          !route.request().url().includes("/users") &&
          !route.request().url().includes("/jobs") &&
          !route.request().url().includes("/resumes")) {
        console.error("Unhandled API request:", route.request().method(), route.request().url());
        await route.abort();
      } else {
        console.log("Falling back for:", route.request().method(), route.request().url());
        await route.fallback();
      }
    });

    await page.goto(`/candidates/${candidateId}`);
  });

  test("can navigate to notes tab, view empty state, and create a note", async ({ page }) => {
    // Switch to notes tab
    await page.click("text=Notes");

    // Should see empty state
    await expect(page.locator("text=No notes on this candidate")).toBeVisible();

    // Click to add note
    await page.click("text=Add a note... (use @ to mention)");

    // Editor should appear
    await expect(page.locator(".ProseMirror")).toBeVisible();

    // Type content
    await page.locator(".ProseMirror").click();
    await page.keyboard.type("This is a great candidate!");

    // Mock the GET request to return the new note after creation
    await page.route(`**/api/v1/candidates/${candidateId}/notes`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          json: {
            data: [
              {
                id: "note-1",
                candidateId,
                author: { id: "user-1", fullName: "Test Recruiter" },
                content: "<p>This is a great candidate!</p>",
                isPrivate: false,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
              }
            ],
          },
        });
      } else {
        await route.fallback();
      }
    });

    // Save note
    await page.click("text=Save Note");

    // Note should appear in the feed
    await expect(page.locator("text=This is a great candidate!")).toBeVisible();
    await expect(page.locator("text=Test Recruiter").first()).toBeVisible();
  });

  test("can mention users", async ({ page }) => {
    await page.click("text=Notes");
    await page.click("text=Add a note... (use @ to mention)");

    const editor = page.locator(".ProseMirror");
    await editor.fill("Hey @Ali");

    // The mention dropdown should appear
    await expect(page.locator("text=Alice Admin")).toBeVisible();
    await page.keyboard.press("Enter");

    // Mention should be inserted
    await expect(editor).toContainText("Alice Admin");
  });
});
