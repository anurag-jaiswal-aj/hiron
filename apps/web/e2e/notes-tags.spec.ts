import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";
import { execSync } from "child_process";

const queryDB = (query: string): string => {
  return execSync(`docker exec hiron-postgres psql -U hiron_user -d hiron_dev -t -c "${query}"`)
    .toString()
    .trim();
};

test.describe("Phase 11 Notes & Tags (Validation Corrections)", () => {
  let testData: Record<string, string>;

  test.beforeEach(async () => {
    const timestamp = Date.now() + Math.floor(Math.random() * 100000);

    // Tenant A setup
    const testCandidateId = `a0000000-0000-0000-0000-000000${timestamp.toString().slice(-6)}`;
    const testJobId = `b0000000-0000-0000-0000-000000${timestamp.toString().slice(-6)}`;

    // Tenant B setup
    const tenantBId = `e0000000-0000-0000-0000-000000${timestamp.toString().slice(-6)}`;
    const candidateBId = `c0000000-0000-0000-0000-000000${timestamp.toString().slice(-6)}`;

    const tenantIdStr = queryDB("SELECT id FROM tenants WHERE slug = 'acme' LIMIT 1;");
    const tenantAId = tenantIdStr.match(/[a-f0-9-]{36}/)![0];

    const rawPwdHash = queryDB(
      `SELECT password_hash FROM users WHERE email = 'admin@acme.com' LIMIT 1;`,
    );
    const pwdHash = rawPwdHash.replace(/\$/g, "\\$");

    // Create Tenant A Users
    const userAEmail = `user-a-${timestamp}@acme.com`;
    queryDB(
      `INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_email_verified, created_at, updated_at) VALUES (gen_random_uuid(), '${tenantAId}', '${userAEmail}', '${pwdHash}', 'User A', 'recruiter', true, true, NOW(), NOW());`,
    );
    const userBEmail = `user-b-${timestamp}@acme.com`;
    queryDB(
      `INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_email_verified, created_at, updated_at) VALUES (gen_random_uuid(), '${tenantAId}', '${userBEmail}', '${pwdHash}', 'User B', 'recruiter', true, true, NOW(), NOW());`,
    );

    // Create Tenant A Data
    queryDB(
      `INSERT INTO jobs (id, tenant_id, title, description, department, location, employment_type, status, created_at, updated_at) VALUES ('${testJobId}', '${tenantAId}', 'E2E Job', 'Test', 'Engineering', 'Remote', 'full_time', 'open', NOW(), NOW());`,
    );
    queryDB(
      `INSERT INTO candidates (id, tenant_id, email, full_name, created_at, updated_at) VALUES ('${testCandidateId}', '${tenantAId}', 'candidate-${timestamp}@example.com', 'Candidate A', NOW(), NOW());`,
    );

    // Create Tenant B
    queryDB(
      `INSERT INTO tenants (id, name, slug, created_at, updated_at) VALUES ('${tenantBId}', 'Tenant B E2E', 'tenant-b-${timestamp}', NOW(), NOW());`,
    );
    const userTenantBEmail = `admin-b-${timestamp}@tenantb.com`;
    queryDB(
      `INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_email_verified, created_at, updated_at) VALUES (gen_random_uuid(), '${tenantBId}', '${userTenantBEmail}', '${pwdHash}', 'Admin B', 'org_admin', true, true, NOW(), NOW());`,
    );
    queryDB(
      `INSERT INTO candidates (id, tenant_id, email, full_name, created_at, updated_at) VALUES ('${candidateBId}', '${tenantBId}', 'candidate-b-${timestamp}@tenantb.com', 'Candidate B', NOW(), NOW());`,
    );

    testData = {
      testJobId,
      tenantA_id: tenantAId,
      org_admin_email: "admin@acme.com",
      user_a_email: userAEmail,
      user_b_email: userBEmail,
      candidate_a_id: testCandidateId,
      tenantB_id: tenantBId,
      user_tenantB_email: userTenantBEmail,
      candidate_b_id: candidateBId,
      password: "SecurePassword123!",
    };
  });

  test.afterEach(async () => {
    if (testData) {
      // Cleanup Tenant A Test Data
      queryDB(`DELETE FROM candidate_tags WHERE candidate_id = '${testData.candidate_a_id}'`);
      queryDB(`DELETE FROM candidate_notes WHERE candidate_id = '${testData.candidate_a_id}'`);
      queryDB(`DELETE FROM candidates WHERE id = '${testData.candidate_a_id}'`);
      queryDB(`DELETE FROM jobs WHERE id = '${testData.testJobId}'`);
      queryDB(`DELETE FROM users WHERE email = '${testData.user_a_email}'`);
      queryDB(`DELETE FROM users WHERE email = '${testData.user_b_email}'`);

      // Cleanup Tenant B Test Data
      queryDB(`DELETE FROM candidate_tags WHERE candidate_id = '${testData.candidate_b_id}'`);
      queryDB(`DELETE FROM candidate_notes WHERE candidate_id = '${testData.candidate_b_id}'`);
      queryDB(`DELETE FROM candidates WHERE id = '${testData.candidate_b_id}'`);
      queryDB(`DELETE FROM users WHERE email = '${testData.user_tenantB_email}'`);
      queryDB(`DELETE FROM tenants WHERE id = '${testData.tenantB_id}'`);
    }
  });

  test("Private Note Privacy: Author Read, Co-worker Deny, Admin Deny, Admin Delete", async ({
    browser,
  }) => {
    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();
    await loginAs(pageA, testData.user_a_email, testData.password, testData.tenantA_id);

    // User A creates private note
    await pageA.goto(`/candidates/${testData.candidate_a_id}`);
    await pageA.getByRole("button", { name: "Notes" }).click();
    await pageA.getByText("Add a note... (use @ to mention)").click();
    await pageA.locator(".ProseMirror").click();
    await pageA.keyboard.type("My secret private note content");

    await pageA.getByLabel("Private Note (only visible to org admins)").click();

    const createRes = pageA.waitForResponse(
      (r) => r.url().includes("/notes") && r.status() === 201,
    );
    await pageA.getByRole("button", { name: "Save Note" }).click();
    await createRes;

    // User A can read their private note
    await expect(pageA.getByText("My secret private note content")).toBeVisible();
    await contextA.close();

    // User B attempts to read private note
    const contextB = await browser.newContext();
    const pageB = await contextB.newPage();
    await loginAs(pageB, testData.user_b_email, testData.password, testData.tenantA_id);
    await pageB.goto(`/candidates/${testData.candidate_a_id}`);
    await pageB.getByRole("button", { name: "Notes" }).click();
    await pageB.waitForLoadState("networkidle");
    // Wait slightly to ensure notes are loaded
    await pageB.waitForTimeout(500);
    // Verify it is NOT visible to User B
    await expect(pageB.getByText("My secret private note content")).not.toBeVisible();
    await contextB.close();

    // Org Admin attempts to read private note
    const contextAdmin = await browser.newContext();
    const pageAdmin = await contextAdmin.newPage();
    const adminToken = await loginAs(
      pageAdmin,
      testData.org_admin_email,
      testData.password,
      testData.tenantA_id,
    );
    await pageAdmin.goto(`/candidates/${testData.candidate_a_id}`);
    await pageAdmin.getByRole("button", { name: "Notes" }).click();
    await pageAdmin.waitForLoadState("networkidle");
    await pageAdmin.waitForTimeout(500);
    // Org Admin MUST NOT see it merely because they are an admin!
    await expect(pageAdmin.getByText("My secret private note content")).not.toBeVisible();

    // Verify Admin can still delete the note by issuing API DELETE Request
    const noteId = queryDB(
      `SELECT id FROM candidate_notes WHERE candidate_id = '${testData.candidate_a_id}' AND is_private = true LIMIT 1;`,
    );
    const deleteReq = await pageAdmin.request.delete(
      `/api/v1/candidates/${testData.candidate_a_id}/notes/${noteId}`,
      {
        headers: { Authorization: `Bearer ${adminToken}` },
      },
    );
    expect(deleteReq.status()).toBe(204);

    // Verify soft deletion persistence
    const archivedCount = queryDB(
      `SELECT COUNT(*) FROM candidate_notes WHERE id = '${noteId}' AND is_archived = true;`,
    );
    expect(archivedCount).toBe("1");
    await contextAdmin.close();
  });

  test("Note Editing Lifecycle", async ({ page }) => {
    await loginAs(page, testData.user_a_email, testData.password, testData.tenantA_id);
    await page.goto(`/candidates/${testData.candidate_a_id}`);
    await page.getByRole("button", { name: "Notes" }).click();
    await page.getByText("Add a note... (use @ to mention)").click();

    // Create public note
    await page.locator(".ProseMirror").click();
    await page.keyboard.type("Initial public note content");

    await Promise.all([
      page.waitForResponse((r) => r.url().includes("/notes") && r.status() === 201),
      page.getByRole("button", { name: "Save Note" }).click(),
    ]);

    // Wait for the editor to disappear to ensure the note is actually saved and rendered
    await expect(page.locator(".ProseMirror")).toHaveCount(0);

    await expect(page.getByText("Initial public note content")).toBeVisible();

    // Edit Note
    await page.getByRole("button", { name: "Edit", exact: true }).click();

    // Clear and re-type
    const editEditor = page.locator(".ProseMirror").first();
    await editEditor.click();
    await page.keyboard.press("Meta+a");
    await page.keyboard.press("Backspace");
    await page.keyboard.type("Updated public note content");

    await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes("/notes") && r.request().method() === "PATCH" && r.status() === 200,
      ),
      page.getByRole("button", { name: "Save Note" }).click(),
    ]);

    // Verify UI reflects update
    await expect(page.getByText("Updated public note content")).toBeVisible();
    await expect(page.getByText("Initial public note content")).not.toBeVisible();

    // Verify DB
    const dbContentCount = queryDB(
      `SELECT COUNT(*) FROM candidate_notes WHERE candidate_id = '${testData.candidate_a_id}' AND content ILIKE '%Updated public note content%';`,
    );
    expect(dbContentCount).toBe("1");
  });

  test("Tenant Isolation via API Boundaries", async ({ page }) => {
    // We login as Tenant B Admin
    const token = await loginAs(
      page,
      testData.user_tenantB_email,
      testData.password,
      testData.tenantB_id,
    );

    // Attempt to GET Tenant A Candidate's notes
    const listRes = await page.request.get(`/api/v1/candidates/${testData.candidate_a_id}/notes`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(listRes.status()).toBe(404);

    // Attempt to GET Tenant A Candidate's tags
    const tagsRes = await page.request.get(`/api/v1/candidates/${testData.candidate_a_id}/tags`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(tagsRes.status()).toBe(404);

    // Attempt to CREATE note on Tenant A candidate
    const createRes = await page.request.post(
      `/api/v1/candidates/${testData.candidate_a_id}/notes`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: { content: "Cross-tenant intrusion", isPrivate: false },
      },
    );
    expect(createRes.status()).toBe(404);
  });

  test("Tags: Normalization, Duplicate 409, and Filtering", async ({ page }) => {
    const token = await loginAs(
      page,
      testData.user_a_email,
      testData.password,
      testData.tenantA_id,
    );
    await page.goto(`/candidates/${testData.candidate_a_id}`);
    await page.getByRole("button", { name: "Tags" }).click();

    // Create Tag X with varying case
    const tagInput = page.locator('input[aria-label="Tag name input"]');
    await tagInput.fill(" ReAcT ");
    await Promise.all([
      page.waitForResponse((r) => r.url().includes("/tags") && r.status() === 201),
      page.locator('button:text-is("Add")').click(),
    ]);

    // Verify Normalization in UI and DB
    await expect(page.getByText("react").first()).toBeVisible();
    const tagCount = queryDB(
      `SELECT COUNT(*) FROM candidate_tags WHERE candidate_id = '${testData.candidate_a_id}' AND tag_name = 'react';`,
    );
    expect(tagCount).toBe("1");

    // Client-side UI error
    await tagInput.fill("React");
    await page.locator('button:text-is("Add")').click();
    await expect(page.getByText("This tag is already applied to this candidate.")).toBeVisible();

    // Duplicate Tag HTTP 409 Assertion via API
    const dupResponse = await page.request.post(
      `/api/v1/candidates/${testData.candidate_a_id}/tags`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: { tagName: "React" },
      },
    );
    expect(dupResponse.status()).toBe(409); // Required explicitly

    // Assert exactly 1 normalized tag remains
    const totalTagCount = queryDB(
      `SELECT COUNT(*) FROM candidate_tags WHERE candidate_id = '${testData.candidate_a_id}';`,
    );
    expect(totalTagCount).toBe("1");

    // Tag Filtering UI
    await page.goto("/candidates");
    await page.waitForLoadState("networkidle");

    // Wait for the candidates list to populate
    await expect(page.getByText("Candidate A").first()).toBeVisible();

    // Apply tag filter
    const tagFilterSelect = page.locator("select").nth(3);
    await tagFilterSelect.selectOption({ label: "react" });

    // Assert Candidate A appears
    await expect(page.getByText("Candidate A").first()).toBeVisible();
  });
});
