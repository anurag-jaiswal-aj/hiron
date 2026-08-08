import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import { loginAs } from "./helpers/auth";

/**
 * Phase 7 Checkpoint 2 — Embedding Status E2E Tests
 *
 * Uses API route interception/mocking to avoid real OpenAI calls.
 * Covers: dashboard panel, candidate/job status badges, RBAC,
 * regeneration flow, polling timeout, API errors, and responsive layout.
 */

test.describe("Embedding Status Dashboard", () => {
  test("A. renders aggregate embedding metrics on the dashboard", async ({ page }) => {
    await page.route("**/api/v1/embeddings/status", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: {
            candidates: { total: 25, withEmbedding: 20, stale: 3, missing: 2, modelVersion: "text-embedding-3-small" },
            jobs: { total: 10, withEmbedding: 8, stale: 1, missing: 1, modelVersion: "text-embedding-3-small" },
          },
        },
      });
    });

    // Intercept individual status calls so they don't fail
    await page.route("**/api/v1/embeddings/candidates/**", async (route) => {
      await route.fulfill({ status: 200, json: { data: { status: "current", modelVersion: "text-embedding-3-small" } } });
    });
    await page.route("**/api/v1/embeddings/jobs/**", async (route) => {
      await route.fulfill({ status: 200, json: { data: { status: "current", modelVersion: "text-embedding-3-small" } } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Verify panel renders
    await expect(page.getByText("AI Embedding Status")).toBeVisible();
    await expect(page.getByText("text-embedding-3-small")).toBeVisible();
    await expect(page.getByText("Candidates Coverage")).toBeVisible();
    await expect(page.getByText("Jobs Coverage")).toBeVisible();
    // Verify metric data
    await expect(page.getByText("80%").first()).toBeVisible(); // 20/25
    await expect(page.getByText("20 / 25").first()).toBeVisible();
  });
});

test.describe("Candidate Detail Embedding Status", () => {
  let testCandidateId: string;
  const runId = `emb-${Date.now()}`;

  test.beforeAll(() => {
    try {
      execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev`, {
        input: `
        WITH t AS (SELECT id FROM tenants LIMIT 1)
        INSERT INTO candidates (id, tenant_id, full_name, email, skills, source)
        VALUES (gen_random_uuid(), (SELECT id FROM t), 'Emb Cand ${runId}', 'emb-cand-${runId}@example.com', '["Python"]', 'upload');
        `,
      });
      testCandidateId = execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev -t`, {
        input: `SELECT id FROM candidates WHERE email = 'emb-cand-${runId}@example.com';`,
      }).toString().trim();
    } catch (e) {
      console.error("Seeding failed", e);
      throw e;
    }
  });

  test.afterAll(() => {
    try {
      if (testCandidateId) {
        execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev`, {
          input: `DELETE FROM candidates WHERE id = '${testCandidateId}';`,
        });
      }
    } catch { /* cleanup best-effort */ }
  });

  test("B1. current status renders correctly", async ({ page }) => {
    await page.route(`**/api/v1/embeddings/candidates/${testCandidateId}`, async (route) => {
      await route.fulfill({ status: 200, json: { data: { status: "current", modelVersion: "text-embedding-3-small" } } });
    });
    await page.route("**/api/v1/resumes/**", async (route) => {
      await route.fulfill({ json: { data: [] } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${testCandidateId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Embedding Current")).toBeVisible();
    // "Generate" button should NOT be visible when status is current
    await expect(page.getByRole("button", { name: /Generate/ })).not.toBeVisible();
  });

  test("B2. stale status renders with Generate button", async ({ page }) => {
    await page.route(`**/api/v1/embeddings/candidates/${testCandidateId}`, async (route) => {
      await route.fulfill({ status: 200, json: { data: { status: "stale", modelVersion: "text-embedding-3-small" } } });
    });
    await page.route("**/api/v1/resumes/**", async (route) => {
      await route.fulfill({ json: { data: [] } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${testCandidateId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Embedding Stale")).toBeVisible();
    await expect(page.getByRole("button", { name: /Generate/ })).toBeVisible();
  });

  test("B3. regeneration POST triggers queued state and polling", async ({ page }) => {
    let statusCallCount = 0;
    await page.route(`**/api/v1/embeddings/candidates/${testCandidateId}`, async (route) => {
      statusCallCount++;
      // First 2 calls return stale, then current
      const status = statusCallCount <= 2 ? "stale" : "current";
      await route.fulfill({ status: 200, json: { data: { status, modelVersion: "text-embedding-3-small" } } });
    });
    await page.route(`**/api/v1/candidates/${testCandidateId}/embedding`, async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 202,
          json: { data: { candidateId: testCandidateId, taskId: "task-123", status: "QUEUED", modelVersion: "text-embedding-3-small" } },
        });
      } else {
        await route.continue();
      }
    });
    await page.route("**/api/v1/resumes/**", async (route) => {
      await route.fulfill({ json: { data: [] } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${testCandidateId}`);
    await page.waitForLoadState("networkidle");

    // Click Generate
    await page.getByRole("button", { name: /Generate/ }).click();

    // Queued state should appear
    await expect(page.getByText("Generating...")).toBeVisible();

    // Wait for polling to reach "current" (with 5s interval)
    await expect(page.getByText("Embedding Current")).toBeVisible({ timeout: 15000 });
  });

  test("D1. hiring_manager can see embedding status badge", async ({ page }) => {
    await page.route(`**/api/v1/embeddings/candidates/${testCandidateId}`, async (route) => {
      await route.fulfill({ status: 200, json: { data: { status: "stale", modelVersion: "text-embedding-3-small" } } });
    });
    await page.route("**/api/v1/resumes/**", async (route) => {
      await route.fulfill({ json: { data: [] } });
    });

    await loginAs(page, "manager@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${testCandidateId}`);
    await page.waitForLoadState("networkidle");

    // Should see status badge
    await expect(page.getByText("Embedding Stale")).toBeVisible();
    // Should NOT see Generate button (hiring_manager has no mutation RBAC)
    await expect(page.getByRole("button", { name: /Generate/ })).not.toBeVisible();
  });

  test("E. polling timeout — status never becomes current", async ({ page }) => {
    await page.route(`**/api/v1/embeddings/candidates/${testCandidateId}`, async (route) => {
      // Always return stale
      await route.fulfill({ status: 200, json: { data: { status: "stale", modelVersion: "text-embedding-3-small" } } });
    });
    await page.route(`**/api/v1/candidates/${testCandidateId}/embedding`, async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 202,
          json: { data: { candidateId: testCandidateId, taskId: "task-timeout", status: "QUEUED", modelVersion: "text-embedding-3-small" } },
        });
      } else {
        await route.continue();
      }
    });
    await page.route("**/api/v1/resumes/**", async (route) => {
      await route.fulfill({ json: { data: [] } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${testCandidateId}`);
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: /Generate/ }).click();
    await expect(page.getByText("Generating...")).toBeVisible();

    // After MAX_POLL_ATTEMPTS * 5s = 60s, polling should stop and button revert
    test.slow();
    await expect(page.getByText("Generating...")).not.toBeVisible({ timeout: 70000 });
    // Should revert to stale badge and Generate button
    await expect(page.getByText("Embedding Stale")).toBeVisible();
  });

  test("F. API error produces graceful state", async ({ page }) => {
    await page.route(`**/api/v1/embeddings/candidates/${testCandidateId}`, async (route) => {
      await route.fulfill({ status: 500, json: { error: { code: "INTERNAL_ERROR", message: "Server error" } } });
    });
    await page.route("**/api/v1/resumes/**", async (route) => {
      await route.fulfill({ json: { data: [] } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${testCandidateId}`);
    await page.waitForLoadState("networkidle");

    // Should show error badge, page should not crash
    await expect(page.getByText("Embedding Error")).toBeVisible();
    await expect(page.locator("h1")).toContainText(`Emb Cand ${runId}`);
  });
});

test.describe("Job Detail Embedding Status", () => {
  let testJobId: string;
  const runId = `emb-job-${Date.now()}`;

  test.beforeAll(() => {
    try {
      execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev`, {
        input: `
        WITH t AS (SELECT id FROM tenants LIMIT 1),
             u AS (SELECT id FROM users WHERE role = 'org_admin' LIMIT 1)
        INSERT INTO jobs (id, tenant_id, title, description, status, created_by)
        VALUES (gen_random_uuid(), (SELECT id FROM t), 'Emb Job ${runId}', 'Test description', 'open', (SELECT id FROM u));
        `,
      });
      testJobId = execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev -t`, {
        input: `SELECT id FROM jobs WHERE title = 'Emb Job ${runId}';`,
      }).toString().trim();
    } catch (e) {
      console.error("Seeding failed", e);
      throw e;
    }
  });

  test.afterAll(() => {
    try {
      if (testJobId) {
        execSync(`docker exec -i hiron-postgres psql -v ON_ERROR_STOP=1 -U hiron_user -d hiron_dev`, {
          input: `DELETE FROM jobs WHERE id = '${testJobId}';`,
        });
      }
    } catch { /* cleanup best-effort */ }
  });

  test("C1. current status renders on job detail", async ({ page }) => {
    await page.route(`**/api/v1/embeddings/jobs/${testJobId}`, async (route) => {
      await route.fulfill({ status: 200, json: { data: { status: "current", modelVersion: "text-embedding-3-small" } } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/jobs/${testJobId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Embedding Current")).toBeVisible();
  });

  test("C2. missing status renders with Generate button", async ({ page }) => {
    await page.route(`**/api/v1/embeddings/jobs/${testJobId}`, async (route) => {
      await route.fulfill({ status: 200, json: { data: { status: "missing", modelVersion: "text-embedding-3-small" } } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/jobs/${testJobId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("No Embedding")).toBeVisible();
    await expect(page.getByRole("button", { name: /Generate/ })).toBeVisible();
  });

  test("C3. job regeneration POST triggers queued state", async ({ page }) => {
    let statusCallCount = 0;
    await page.route(`**/api/v1/embeddings/jobs/${testJobId}`, async (route) => {
      statusCallCount++;
      const status = statusCallCount <= 2 ? "missing" : "current";
      await route.fulfill({ status: 200, json: { data: { status, modelVersion: "text-embedding-3-small" } } });
    });
    await page.route(`**/api/v1/jobs/${testJobId}/embedding`, async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 202,
          json: { data: { jobId: testJobId, taskId: "task-456", status: "QUEUED", modelVersion: "text-embedding-3-small" } },
        });
      } else {
        await route.continue();
      }
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/jobs/${testJobId}`);
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: /Generate/ }).click();
    await expect(page.getByText("Generating...")).toBeVisible();
    await expect(page.getByText("Embedding Current")).toBeVisible({ timeout: 15000 });
  });

  test("D2. hiring_manager can view job embedding status but cannot regenerate", async ({ page }) => {
    await page.route(`**/api/v1/embeddings/jobs/${testJobId}`, async (route) => {
      await route.fulfill({ status: 200, json: { data: { status: "stale", modelVersion: "text-embedding-3-small" } } });
    });

    await loginAs(page, "manager@acme.com", "SecurePassword123!");
    await page.goto(`/jobs/${testJobId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Embedding Stale")).toBeVisible();
    await expect(page.getByRole("button", { name: /Generate/ })).not.toBeVisible();
  });

  test("F2. job API error produces graceful state", async ({ page }) => {
    await page.route(`**/api/v1/embeddings/jobs/${testJobId}`, async (route) => {
      await route.fulfill({ status: 500, json: { error: { code: "INTERNAL_ERROR", message: "Server error" } } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/jobs/${testJobId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Embedding Error")).toBeVisible();
    await expect(page.getByRole("heading", { name: `Emb Job ${runId}` })).toBeVisible();
  });
});

test.describe("Responsive Embedding UI — 390px", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("G1. dashboard embedding panel has no horizontal overflow", async ({ page }) => {
    await page.route("**/api/v1/embeddings/status", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          data: {
            candidates: { total: 10, withEmbedding: 8, stale: 1, missing: 1, modelVersion: "text-embedding-3-small" },
            jobs: { total: 5, withEmbedding: 5, stale: 0, missing: 0, modelVersion: "text-embedding-3-small" },
          },
        },
      });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("AI Embedding Status")).toBeVisible();


    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2); // 2px tolerance
  });

  test("G2. candidate detail embedding badge renders at 390px without overflow", async ({ page }) => {
    const candId = "00000000-0000-0000-0000-000000000001";
    await page.route(`**/api/v1/candidates/${candId}`, async (route) => {
      await route.fulfill({
        status: 200,
        json: { data: { id: candId, fullName: "Test", email: null, skills: [], jobs: [], source: "manual", isArchived: false, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() } },
      });
    });
    await page.route(`**/api/v1/embeddings/candidates/${candId}`, async (route) => {
      await route.fulfill({ status: 200, json: { data: { status: "stale", modelVersion: "text-embedding-3-small" } } });
    });
    await page.route("**/api/v1/resumes/**", async (route) => {
      await route.fulfill({ json: { data: [] } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/candidates/${candId}`);
    await page.waitForLoadState("networkidle");

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2);
  });

  test("G3. job detail embedding badge renders at 390px without overflow", async ({ page }) => {
    const jobId = "00000000-0000-0000-0000-000000000002";
    await page.route(`**/api/v1/jobs/${jobId}`, async (route) => {
      await route.fulfill({
        status: 200,
        json: { data: { id: jobId, title: "Test Job", description: "Desc", status: "open", candidateCount: 0, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() } },
      });
    });
    await page.route(`**/api/v1/embeddings/jobs/${jobId}`, async (route) => {
      await route.fulfill({ status: 200, json: { data: { status: "missing", modelVersion: "text-embedding-3-small" } } });
    });

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto(`/jobs/${jobId}`);
    await page.waitForLoadState("networkidle");


    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2);
  });
});
