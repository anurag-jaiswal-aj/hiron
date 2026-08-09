import { test, expect } from "@playwright/test";

test.describe("Candidate Tags", () => {
  const candidateId = "cand-tag-123";

  /**
   * Helper: set up common API mocks shared across recruiter tests.
   */
  async function setupRecruiterMocks(page: import("@playwright/test").Page): Promise<void> {
    // Auth – recruiter role
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
      await route.fulfill({
        status: 200,
        json: { data: { accessToken: "test-token" } },
      });
    });

    // Candidate detail
    await page.route(`**/api/v1/candidates/${candidateId}`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          json: {
            data: {
              id: candidateId,
              fullName: "Tag Tester",
              email: "tag@example.com",
              skills: ["TypeScript"],
              jobs: [],
              source: "manual",
              isArchived: false,
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          },
        });
      } else {
        await route.fallback();
      }
    });

    // Resumes
    await page.route(`**/api/v1/resumes/candidate/${candidateId}`, async (route) => {
      await route.fulfill({ status: 200, json: { data: [] } });
    });

    // Jobs
    await page.route("**/api/v1/jobs", async (route) => {
      await route.fulfill({ status: 200, json: { data: [] } });
    });

    // Notes
    await page.route(`**/api/v1/candidates/${candidateId}/notes`, async (route) => {
      await route.fulfill({ status: 200, json: { data: [] } });
    });

    // Users (for notes @mentions)
    await page.route("**/api/v1/users?isActive=true&limit=100", async (route) => {
      await route.fulfill({
        status: 200,
        json: { data: [{ id: "user-1", fullName: "Test Recruiter" }] },
      });
    });
  }

  test.describe("Recruiter – Candidate Detail Tags Tab", () => {
    test.beforeEach(async ({ page }) => {
      await setupRecruiterMocks(page);
    });

    test("can navigate to Tags tab and view existing tags", async ({ page }) => {
      // Mock candidate tags with existing data
      await page.route(`**/api/v1/candidates/${candidateId}/tags`, async (route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({
            status: 200,
            json: {
              data: [
                {
                  id: "tag-1",
                  tagName: "strong-hire",
                  taggedBy: { id: "user-1", fullName: "Test Recruiter" },
                  createdAt: new Date().toISOString(),
                },
                {
                  id: "tag-2",
                  tagName: "backend",
                  taggedBy: { id: "user-1", fullName: "Test Recruiter" },
                  createdAt: new Date().toISOString(),
                },
              ],
            },
          });
        } else {
          await route.fallback();
        }
      });

      // Mock tenant tags
      await page.route("**/api/v1/tags", async (route) => {
        await route.fulfill({
          status: 200,
          json: { data: ["strong-hire", "backend", "frontend", "senior"] },
        });
      });

      // Catch-all for unhandled API calls
      await page.route("**/api/v1/**", async (route) => {
        await route.fallback();
      });

      await page.goto(`/candidates/${candidateId}`);

      // Switch to Tags tab
      await page.click("text=Tags");

      // Should see the existing tags
      await expect(page.locator("text=strong-hire").first()).toBeVisible();
      await expect(page.locator("text=backend").first()).toBeVisible();

      // Should see the tag count
      await expect(page.locator("text=Tags (2)")).toBeVisible();

      // Should see add-tag input since we are recruiter
      await expect(page.locator("text=Add Tag")).toBeVisible();
    });

    test("can add a new tag", async ({ page }) => {
      // Start with no tags
      let currentTags: Array<{
        id: string;
        tagName: string;
        taggedBy: { id: string; fullName: string };
        createdAt: string;
      }> = [];

      await page.route(`**/api/v1/candidates/${candidateId}/tags`, async (route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({
            status: 200,
            json: { data: currentTags },
          });
        } else if (route.request().method() === "POST") {
          const body = JSON.parse(route.request().postData() || "{}");
          const newTag = {
            id: "tag-new-1",
            tagName: body.tagName,
            taggedBy: { id: "user-1", fullName: "Test Recruiter" },
            createdAt: new Date().toISOString(),
          };
          currentTags = [...currentTags, newTag];
          await route.fulfill({ status: 201, json: { data: newTag } });
        } else {
          await route.fallback();
        }
      });

      await page.route("**/api/v1/tags", async (route) => {
        await route.fulfill({
          status: 200,
          json: { data: ["strong-hire", "backend"] },
        });
      });

      await page.route("**/api/v1/**", async (route) => {
        await route.fallback();
      });

      await page.goto(`/candidates/${candidateId}`);
      await page.click("text=Tags");

      // Should show empty state
      await expect(page.locator("text=No tags have been applied")).toBeVisible();

      // Type a new tag
      await page.fill('input[aria-label="Tag name input"]', "new-hire");

      // Click the Add button next to the tag input (not the header "Add to Job" button)
      await page.locator('button:text-is("Add")').click();

      // Tag should appear
      await expect(page.locator("text=new-hire")).toBeVisible();
      await expect(page.locator("text=Tags (1)")).toBeVisible();
    });

    test("autocomplete displays tenant tags", async ({ page }) => {
      await page.route(`**/api/v1/candidates/${candidateId}/tags`, async (route) => {
        await route.fulfill({ status: 200, json: { data: [] } });
      });

      await page.route("**/api/v1/tags", async (route) => {
        await route.fulfill({
          status: 200,
          json: { data: ["strong-hire", "backend", "frontend", "senior"] },
        });
      });

      await page.route("**/api/v1/**", async (route) => {
        await route.fallback();
      });

      await page.goto(`/candidates/${candidateId}`);
      await page.click("text=Tags");

      const input = page.locator('input[aria-label="Tag name input"]');
      await input.focus();
      await input.fill("back");

      // Should see "backend" suggestion in the dropdown
      await expect(page.locator('[role="option"]').filter({ hasText: "backend" })).toBeVisible();
    });

    test("can remove a tag", async ({ page }) => {
      await page.route(`**/api/v1/candidates/${candidateId}/tags`, async (route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({
            status: 200,
            json: {
              data: [
                {
                  id: "tag-1",
                  tagName: "to-remove",
                  taggedBy: { id: "user-1", fullName: "Test Recruiter" },
                  createdAt: new Date().toISOString(),
                },
              ],
            },
          });
        } else {
          await route.fallback();
        }
      });

      await page.route(`**/api/v1/candidates/${candidateId}/tags/tag-1`, async (route) => {
        if (route.request().method() === "DELETE") {
          await route.fulfill({ status: 204, body: "" });
        } else {
          await route.fallback();
        }
      });

      await page.route("**/api/v1/tags", async (route) => {
        await route.fulfill({ status: 200, json: { data: ["to-remove"] } });
      });

      await page.route("**/api/v1/**", async (route) => {
        await route.fallback();
      });

      await page.goto(`/candidates/${candidateId}`);
      await page.click("text=Tags");

      // Tag should be visible
      await expect(page.locator("text=to-remove")).toBeVisible();

      // Click remove button
      await page.click('button[aria-label="Remove tag to-remove"]');

      // Tag should disappear
      await expect(page.locator("text=to-remove")).not.toBeVisible();
      await expect(page.locator("text=Tags (0)")).toBeVisible();
    });
  });

  test.describe("Hiring Manager – Read-only Tags", () => {
    test("can view tags but cannot add or remove", async ({ page }) => {
      // Auth – hiring_manager role
      await page.route("**/api/v1/auth/me", async (route) => {
        await route.fulfill({
          status: 200,
          json: {
            data: {
              id: "user-hm",
              fullName: "Test HM",
              role: "hiring_manager",
              email: "hm@example.com",
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
        await route.fulfill({
          status: 200,
          json: { data: { accessToken: "test-token" } },
        });
      });

      await page.route(`**/api/v1/candidates/${candidateId}`, async (route) => {
        await route.fulfill({
          status: 200,
          json: {
            data: {
              id: candidateId,
              fullName: "Tag Tester",
              email: "tag@example.com",
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

      await page.route(`**/api/v1/resumes/candidate/${candidateId}`, async (route) => {
        await route.fulfill({ status: 200, json: { data: [] } });
      });

      await page.route("**/api/v1/jobs", async (route) => {
        await route.fulfill({ status: 200, json: { data: [] } });
      });

      await page.route(`**/api/v1/candidates/${candidateId}/notes`, async (route) => {
        await route.fulfill({ status: 200, json: { data: [] } });
      });

      await page.route(`**/api/v1/candidates/${candidateId}/tags`, async (route) => {
        await route.fulfill({
          status: 200,
          json: {
            data: [
              {
                id: "tag-1",
                tagName: "strong-hire",
                taggedBy: { id: "user-1", fullName: "Test Recruiter" },
                createdAt: new Date().toISOString(),
              },
            ],
          },
        });
      });

      await page.route("**/api/v1/tags", async (route) => {
        await route.fulfill({ status: 200, json: { data: ["strong-hire"] } });
      });

      await page.route("**/api/v1/**", async (route) => {
        await route.fallback();
      });

      await page.goto(`/candidates/${candidateId}`);
      await page.click("text=Tags");

      // Should see existing tags
      await expect(page.locator("text=strong-hire").first()).toBeVisible();

      // "Add Tag" heading and input should NOT be present
      await expect(page.locator("text=Add Tag")).not.toBeVisible();
      await expect(page.locator('input[aria-label="Tag name input"]')).not.toBeVisible();

      // Remove button should NOT be present
      await expect(page.locator('button[aria-label="Remove tag strong-hire"]')).not.toBeVisible();
    });
  });

  test.describe("Candidate List – Tag Filter", () => {
    test("tag filter sends correct query parameter and clears correctly", async ({ page }) => {
      // Auth
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
        await route.fulfill({
          status: 200,
          json: { data: { accessToken: "test-token" } },
        });
      });

      // Tenant tags for filter dropdown
      await page.route("**/api/v1/tags", async (route) => {
        await route.fulfill({
          status: 200,
          json: { data: ["strong-hire", "backend"] },
        });
      });

      // Track candidate list API requests
      const apiRequests: string[] = [];

      await page.route("**/api/v1/candidates?*", async (route) => {
        const url = route.request().url();
        apiRequests.push(url);

        const urlObj = new URL(url);
        const tagParam = urlObj.searchParams.get("tag");

        if (tagParam === "strong-hire") {
          // Return filtered result
          await route.fulfill({
            status: 200,
            json: {
              data: {
                data: [
                  {
                    id: "cand-filtered",
                    fullName: "Filtered Candidate",
                    email: "filtered@test.com",
                    currentTitle: "Engineer",
                    currentCompany: "TestCo",
                    location: "NYC",
                    totalExperienceYears: 5,
                    skills: ["TypeScript"],
                    source: "manual",
                    isArchived: false,
                    createdAt: new Date().toISOString(),
                  },
                ],
                pagination: { hasMore: false, nextCursor: null, totalCount: 1 },
              },
            },
          });
        } else {
          // Return unfiltered results
          await route.fulfill({
            status: 200,
            json: {
              data: {
                data: [
                  {
                    id: "cand-1",
                    fullName: "Alice Smith",
                    email: "alice@test.com",
                    currentTitle: "SWE",
                    currentCompany: "BigCo",
                    location: "SF",
                    totalExperienceYears: 8,
                    skills: ["Python"],
                    source: "upload",
                    isArchived: false,
                    createdAt: new Date().toISOString(),
                  },
                  {
                    id: "cand-2",
                    fullName: "Bob Johnson",
                    email: "bob@test.com",
                    currentTitle: "Lead",
                    currentCompany: "StartupCo",
                    location: "LA",
                    totalExperienceYears: 12,
                    skills: ["Go"],
                    source: "manual",
                    isArchived: false,
                    createdAt: new Date().toISOString(),
                  },
                ],
                pagination: { hasMore: false, nextCursor: null, totalCount: 2 },
              },
            },
          });
        }
      });

      await page.route("**/api/v1/**", async (route) => {
        await route.fallback();
      });

      await page.goto("/candidates");

      // Wait for initial load
      await expect(page.locator("text=Alice Smith")).toBeVisible();
      await expect(page.locator("text=Bob Johnson")).toBeVisible();

      // Select the "strong-hire" tag filter
      const tagSelect = page.locator("select").last();
      await tagSelect.selectOption("strong-hire");

      // Wait for the filtered results
      await expect(page.locator("text=Filtered Candidate")).toBeVisible();
      await expect(page.locator("text=Alice Smith")).not.toBeVisible();

      // Verify the tag parameter was sent
      const filteredRequests = apiRequests.filter((url) => url.includes("tag=strong-hire"));
      expect(filteredRequests.length).toBeGreaterThanOrEqual(1);

      // Clear the filter by selecting "All Tags"
      await tagSelect.selectOption("");

      // Wait for unfiltered results to return
      await expect(page.locator("text=Alice Smith")).toBeVisible();
      await expect(page.locator("text=Bob Johnson")).toBeVisible();
    });

    test("candidate list renders filtered results after tag selection", async ({ page }) => {
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
        await route.fulfill({
          status: 200,
          json: { data: { accessToken: "test-token" } },
        });
      });

      await page.route("**/api/v1/tags", async (route) => {
        await route.fulfill({
          status: 200,
          json: { data: ["backend"] },
        });
      });

      await page.route("**/api/v1/candidates?*", async (route) => {
        const url = route.request().url();
        const urlObj = new URL(url);
        const tagParam = urlObj.searchParams.get("tag");

        if (tagParam === "backend") {
          await route.fulfill({
            status: 200,
            json: {
              data: {
                data: [
                  {
                    id: "cand-be",
                    fullName: "Backend Dev",
                    email: "be@test.com",
                    currentTitle: "Backend Eng",
                    currentCompany: "DevCo",
                    location: "Remote",
                    totalExperienceYears: 6,
                    skills: ["Go", "PostgreSQL"],
                    source: "manual",
                    isArchived: false,
                    createdAt: new Date().toISOString(),
                  },
                ],
                pagination: { hasMore: false, nextCursor: null, totalCount: 1 },
              },
            },
          });
        } else {
          await route.fulfill({
            status: 200,
            json: {
              data: {
                data: [],
                pagination: { hasMore: false, nextCursor: null, totalCount: 0 },
              },
            },
          });
        }
      });

      await page.route("**/api/v1/**", async (route) => {
        await route.fallback();
      });

      await page.goto("/candidates");

      // Select the "backend" tag
      const tagSelect = page.locator("select").last();
      await tagSelect.selectOption("backend");

      // Should show filtered result
      await expect(page.locator("text=Backend Dev")).toBeVisible();
      await expect(page.locator("text=Showing 1 candidate(s) of 1")).toBeVisible();
    });
  });
});
