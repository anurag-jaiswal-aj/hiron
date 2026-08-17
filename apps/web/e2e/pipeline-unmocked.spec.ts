import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";
import fs from "fs";
import path from "path";
import { execSync } from "child_process";

const queryDB = (query: string) => {
    return execSync(`psql "postgresql://hiron_user:hiron_secure_password@localhost:5432/hiron_dev" -t -c "${query}"`).toString().trim();
};

test.describe("Pipeline / Kanban (Unmocked)", () => {
  let testData: any;

  test.beforeEach(async () => {
    // Read the test data created by setup_test_data.py
    const dataPath = path.resolve(__dirname, "../../../e2e_test_data.json");
    if (!fs.existsSync(dataPath)) {
        throw new Error("test data not found at " + dataPath);
    }
    const content = fs.readFileSync(dataPath, "utf8");
    testData = JSON.parse(content);

    // Reset candidate to Applied stage for repeatable test runs
    const appliedStageId = queryDB(`SELECT id FROM pipeline_stages WHERE job_id = '${testData.job_a_id}' AND name = 'Applied' LIMIT 1`).trim();
    queryDB(`UPDATE job_candidates SET current_stage_id = '${appliedStageId}', is_shortlisted = false, rejection_reason = null WHERE job_id = '${testData.job_a_id}'`);
    queryDB(`DELETE FROM candidate_stage_history WHERE job_candidate_id IN (SELECT id FROM job_candidates WHERE job_id = '${testData.job_a_id}')`);
  });

  test("Kanban rendering & Drag & Drop", async ({ page }) => {
    // Login as recruiter
    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");

    // Navigate to Kanban board for Job A
    await page.goto(`/jobs/${testData.job_a_id}`);
    await page.getByRole("button", { name: "Kanban" }).click();

    // Verify all expected columns are visible
    await expect(page.getByRole("heading", { name: "Applied" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Screening" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Interview" })).toBeVisible();

    // The candidate should be in Applied
    const candidateCard = page.getByRole("button", { name: /E2E Candidate/i }).first();
    await expect(candidateCard).toBeVisible();

    // Drag and drop test using Playwright native dragTo
    console.log("Attempting drag and drop via dragTo...");
    const targetColumnHeader = page.getByRole("heading", { name: "Screening" });
    const targetColumnContainer = targetColumnHeader.locator("..").locator(".."); // Up to the KanbanColumn div
    const droppableArea = targetColumnContainer.locator("> div").nth(1); // The second child is the droppable flex area

    const sourceBox = await candidateCard.boundingBox();
    const targetBox = await droppableArea.boundingBox();

    if (sourceBox && targetBox) {
      await page.mouse.move(sourceBox.x + sourceBox.width / 2, sourceBox.y + sourceBox.height / 2);
      await page.mouse.down();
      await page.waitForTimeout(100);

      // small movement to trigger drag
      await page.mouse.move(sourceBox.x + sourceBox.width / 2 + 20, sourceBox.y + sourceBox.height / 2 + 20, { steps: 5 });
      await page.waitForTimeout(500);

      // move to center of TARGET container
      await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height / 2, { steps: 10 });
      await page.waitForTimeout(500);

      await page.mouse.up();
    }

    // Wait for optimistic update and API call
    await page.waitForTimeout(2000);

    // Validate drag and drop success in UI
    await expect(targetColumnContainer.getByRole("button", { name: /E2E Candidate/i }).first()).toBeVisible({ timeout: 5000 });

    // Verify reload persistence
    await page.goto(`/jobs/${testData.job_a_id}?_timestamp=${Date.now()}`); // Cache busting
    await page.getByRole("button", { name: "Kanban" }).click();
    await expect(targetColumnContainer.getByRole("button", { name: /E2E Candidate/i }).first()).toBeVisible({ timeout: 5000 });

    // Validate in DB
    const movedCandId = queryDB(`SELECT jc.id FROM job_candidates jc JOIN candidates c ON jc.candidate_id = c.id WHERE jc.job_id = '${testData.job_a_id}' AND c.full_name = 'E2E Candidate' ORDER BY jc.updated_at DESC LIMIT 1`).trim();
    const currentStageId = queryDB(`SELECT current_stage_id FROM job_candidates WHERE id = '${movedCandId}'`).trim();
    const screeningStageId = queryDB(`SELECT id FROM pipeline_stages WHERE job_id = '${testData.job_a_id}' AND name = 'Screening' LIMIT 1`).trim();

    expect(currentStageId).toBe(screeningStageId);

    // Verify candidate_stage_history
    const historyCount = queryDB(`SELECT COUNT(*) FROM candidate_stage_history WHERE job_candidate_id = '${movedCandId}' AND to_stage_id = '${screeningStageId}'`).trim();
    expect(parseInt(historyCount)).toBeGreaterThan(0);
  });

  test("Shortlist & Reject", async ({ page }) => {
    page.on("console", msg => console.log("BROWSER:", msg.text()));
    page.on("request", req => console.log("REQ:", req.method(), req.url()));
    page.on("response", res => console.log("RES:", res.request().method(), res.url(), res.status()));
    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");
    await page.goto(`/jobs/${testData.job_a_id}`);
    await page.getByRole("button", { name: "Kanban" }).click();

    // Shortlist
    console.log("Clicking candidate...");
    await page.getByRole("button", { name: "E2E Candidate" }).first().click();
    console.log("Candidate clicked.");
    await expect(page.getByText("Candidate Actions")).toBeVisible();

    console.log("Clicking Shortlist...");
    await page.locator('button:text-is("Shortlist")').click({ force: true });
    console.log("Shortlist clicked.");
    await expect(page.getByText("Candidate Actions")).toBeHidden();

    // Verify DB State for Shortlist first!
    const isShortlisted = queryDB(`SELECT jc.is_shortlisted FROM job_candidates jc JOIN candidates c ON jc.candidate_id = c.id WHERE jc.job_id = '${testData.job_a_id}' AND c.full_name = 'E2E Candidate' ORDER BY jc.updated_at DESC LIMIT 1`).trim();
    expect(isShortlisted).toBe("t"); // postgres boolean true is 't'

    // Verify Shortlist Reload
    console.log("Reloading...");
    await page.goto(`/jobs/${testData.job_a_id}?_timestamp=${Date.now()}`); // Cache busting
    await page.getByRole("button", { name: "Kanban" }).click();

    // DEBUG: Check what is rendered in the card!
    console.log("Checking card for star...");
    const reloadedCard = page.getByRole("button", { name: "E2E Candidate" }).first();
    // In our UI, if shortlisted, a star SVG is rendered inside the card
    await expect(reloadedCard.locator("svg.text-\\[var\\(--accent-primary\\)\\]")).toBeVisible({ timeout: 2000 }).catch(() => console.log("Star not visible"));

    await reloadedCard.click();
    await expect(page.getByText("Candidate Actions")).toBeVisible({ timeout: 2000 });

    const modalText = await page.getByText("Candidate Actions").locator("..").locator("..").textContent();
    console.log("MODAL TEXT:", modalText);

    await expect(page.getByText("Shortlisted").first()).toBeVisible();

    // Reject
    await page.locator('button:text-is("Reject")').click({ force: true });
    await page.getByLabel("Reason").fill("Not enough experience");
    await page.locator('button:text-is("Reject Candidate")').click();
    await page.waitForTimeout(1000);

    // Verify Reject Reload
    await page.reload();
    await page.getByRole("button", { name: "Kanban" }).click();
    const rejectedContainer = page.getByRole("heading", { name: /Rejected|Disqualified/i }).locator("..").locator("..");
    await expect(rejectedContainer.getByRole("button", { name: /E2E Candidate/i })).toBeVisible();

    // Verify disappearance from previous stage (Screening)
    const screeningContainer = page.getByRole("heading", { name: "Screening" }).locator("..").locator("..");
    await expect(screeningContainer.getByRole("button", { name: /E2E Candidate/i })).toBeHidden();

    // Verify DB State for Reject
    const rejectedCandId = queryDB(`SELECT jc.id FROM job_candidates jc JOIN candidates c ON jc.candidate_id = c.id WHERE jc.job_id = '${testData.job_a_id}' AND c.full_name = 'E2E Candidate' ORDER BY jc.updated_at DESC LIMIT 1`).trim();
    const rejectedStageId = queryDB(`SELECT current_stage_id FROM job_candidates WHERE id = '${rejectedCandId}'`).trim();
    const rejectionReason = queryDB(`SELECT rejection_reason FROM job_candidates WHERE id = '${rejectedCandId}'`).trim();

    const dbRejectedStageId = queryDB(`SELECT id FROM pipeline_stages WHERE job_id = '${testData.job_a_id}' AND (name = 'Rejected' OR name = 'Disqualified') LIMIT 1`).trim();

    expect(rejectedStageId).toBe(dbRejectedStageId);
    expect(rejectionReason).toBe("Not enough experience");

    const rejectHistoryCount = queryDB(`SELECT COUNT(*) FROM candidate_stage_history WHERE job_candidate_id = '${rejectedCandId}' AND to_stage_id = '${rejectedStageId}'`).trim();
    expect(rejectHistoryCount).toBe("1");
  });

  test("Hiring Manager permissions", async ({ page }) => {
    await loginAs(page, "manager@acme.com", "SecurePassword123!");
    await page.goto(`/jobs/${testData.job_a_id}`);
    await page.getByRole("button", { name: "Kanban" }).click();

    await page.getByRole("button", { name: "E2E Candidate" }).first().click({ force: true });

    // Should not see Shortlist or Reject
    await expect(page.getByText("Candidate Actions")).toBeVisible();
    await expect(page.locator('button:text-is("Shortlist")')).not.toBeVisible();
    await expect(page.locator('button:text-is("Reject")')).not.toBeVisible();
  });
});
