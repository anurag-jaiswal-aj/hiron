/* eslint-disable no-control-regex */
import { test, expect, type Page } from "@playwright/test";
import { loginAs } from "./helpers/auth";
import { execSync } from "child_process";
import { generateQStashSignature } from "./helpers/qstash";

async function manuallyTriggerQStashWebhook(page: Page, email: string): Promise<void> {
  // Query DB to get the user ID and tenant ID
  const dbOutput = execSync(
    `docker exec hiron-postgres psql -U hiron_user -d hiron_dev -t -c "SELECT id, tenant_id FROM users WHERE email = '${email}' LIMIT 1;"`,
  )
    .toString()
    .trim();
  const [userId, tenantId] = dbOutput.split("|").map((s) => s.trim());

  if (!userId || !tenantId) {
    throw new Error(`Failed to find user ${email} in DB to trigger webhook.`);
  }

  const body = JSON.stringify({
    user_id: userId,
    tenant_id: tenantId,
    email: email,
  });

  const secret = "sig_test_key_12345678901234567890";
  const url = "http://localhost:8000/api/v1/webhooks/qstash/users/invite";
  const signature = generateQStashSignature(body, secret, url);

  const res = await page.request.post(url, {
    headers: {
      "Upstash-Signature": signature,
      "Content-Type": "application/json",
    },
    data: body,
  });

  expect(res.status()).toBe(200);
}

// Disable parallel execution since we are creating and verifying users in the same tenant
// and extracting logs that might be noisy.
test.describe.configure({ mode: "serial" });

function extractInvitationToken(email: string): string {
  // Try up to 15 seconds to find the email intercept in docker logs
  for (let attempt = 0; attempt < 15; attempt++) {
    try {
      const logs = execSync("docker logs hiron-api --tail 1000 2>&1").toString();

      // Look for the specific email and extract its URL
      // We look for a block in structlog that contains to_email=... and invitation_url=...
      // Strip ANSI codes from the docker logs output
      const cleanLogs = logs.replace(
        /[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g,
        "",
      );
      const lines = cleanLogs.split("\n");
      for (let i = 0; i < lines.length; i++) {
        if (lines[i].includes("DEVELOPMENT EMAIL INTERCEPTED") && lines[i].includes(email)) {
          // Extract URL (it might have single quotes around it from structlog)
          const match = lines[i].match(/invitation_url='?([^ ']+)'?/);
          if (match && match[1]) {
            const urlString = match[1].replace(/['"]/g, "");
            const url = new URL(urlString);
            const token = url.searchParams.get("token");
            if (token) return token;
          }
        }
      }
    } catch (e) {
      console.error("Failed to read docker logs", e);
    }
    // Sleep 1 second before retrying
    execSync("sleep 1");
  }
  throw new Error(`Could not find invitation token in logs for ${email}`);
}

async function cleanupUser(email: string): Promise<void> {
  try {
    execSync(
      `docker exec hiron-postgres psql -U hiron_user -d hiron_dev -t -c "DELETE FROM users WHERE email = '${email}';"`,
    );
  } catch (e) {
    // Ignore cleanup errors
  }
}

test.describe("Full End-to-End Invitation Flow", () => {
  const timestamp = Date.now();
  const testEmail = `e2e-invite-${timestamp}@example.com`;
  const resendTestEmail = `e2e-resend-${timestamp}@example.com`;
  const newPassword = "E2EInvitePassword123!";

  test.afterAll(async () => {
    await cleanupUser(testEmail);
    await cleanupUser(resendTestEmail);
  });

  test("1. Full invitation lifecycle and replay protection", async ({ page }) => {
    // 1. Admin Login
    await loginAs(page, "admin@acme.com", "SecurePassword123!");

    // 2. Go to Users Management
    await page.goto("/users");
    await expect(page.getByRole("heading", { name: "Team Management" })).toBeVisible();

    // 3. Create Invitation
    await page.getByRole("button", { name: "+ Invite User" }).click();
    await page.getByLabel("Email Address *").fill(testEmail);
    await page.getByLabel("Full Name *").fill("E2E Test User");
    await page.getByLabel("Role *").selectOption("recruiter");
    await page.getByRole("button", { name: "Send Invitation" }).click();

    // Wait for the modal to close and the new user to appear in the list as pending
    await expect(page.getByRole("heading", { name: "Invite Team Member" })).not.toBeVisible();
    const newUserRow = page.locator("tr").filter({ hasText: testEmail });
    await expect(newUserRow.getByText("Pending", { exact: true })).toBeVisible();

    // TRIGGER QSTASH WEBHOOK (Test-only local mechanism)
    await manuallyTriggerQStashWebhook(page, testEmail);

    // 4. Capture Invitation URL via Docker logs (Mock Email Intercept)
    const token = extractInvitationToken(testEmail);
    expect(token).toBeTruthy();

    // 5. Open Accept Invite Page (ensure we are logged out first)
    await page.context().clearCookies();
    await page.goto(`/accept-invite?token=${token}`);

    await expect(page.getByRole("heading", { name: "HIRON" })).toBeVisible();
    await expect(page.getByText("Set your password to activate your Hiron account.")).toBeVisible();

    // 6. Accept Invitation
    await page.getByLabel("New Password *", { exact: true }).fill(newPassword);
    await page.getByLabel("Confirm New Password *").fill(newPassword);
    await page.getByRole("button", { name: "Accept Invitation" }).click();

    // 7. Verify Success State
    await expect(page.getByText("Invitation Accepted", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Proceed to Sign In" })).toBeVisible();

    // 8. Test Replay Attack
    // Try to accept the invitation again using the exact same token through the UI
    await page.goto(`/accept-invite?token=${token}`);
    await page.getByLabel("New Password *", { exact: true }).fill(newPassword);
    await page.getByLabel("Confirm New Password *").fill(newPassword);
    await page.getByRole("button", { name: "Accept Invitation" }).click();

    // Should fail with generic invalid message
    await expect(page.getByText("This invitation link is invalid or has expired.")).toBeVisible();

    // 9. Login as Invited User
    const userToken = await loginAs(page, testEmail, newPassword);
    expect(userToken).toBeTruthy();

    // Verify user reaches protected dashboard
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.locator("h1").first()).toContainText("Dashboard");

    // 10. Database Verification
    const dbCheckOutput = execSync(
      `docker exec hiron-postgres psql -U hiron_user -d hiron_dev -t -c "SELECT is_active, is_email_verified FROM users WHERE email = '${testEmail}';"`,
    );
    const [isActive, isVerified] = dbCheckOutput
      .toString()
      .split("|")
      .map((s) => s.trim());
    expect(isActive).toBe("t");
    expect(isVerified).toBe("t");

    // We should also check the invitation token is marked as used
    const dbTokenOutput = execSync(
      `docker exec hiron-postgres psql -U hiron_user -d hiron_dev -t -c "SELECT used_at FROM user_invitation_tokens JOIN users ON user_invitation_tokens.user_id = users.id WHERE users.email = '${testEmail}';"`,
    );
    const usedAt = dbTokenOutput.toString().trim();
    expect(usedAt).not.toBe("");
  });

  test("2. Resend invitation revokes old token", async ({ page }) => {
    // 1. Admin Login
    await loginAs(page, "admin@acme.com", "SecurePassword123!");

    // 2. Go to Users Management
    await page.goto("/users");

    // 3. Create initial invitation
    await page.getByRole("button", { name: "+ Invite User" }).click();
    await page.getByLabel("Email Address *").fill(resendTestEmail);
    await page.getByLabel("Full Name *").fill("Resend Test User");
    await page.getByRole("button", { name: "Send Invitation" }).click();
    await expect(page.getByRole("heading", { name: "Invite Team Member" })).not.toBeVisible();

    await manuallyTriggerQStashWebhook(page, resendTestEmail);

    // 4. Capture first token
    const firstToken = extractInvitationToken(resendTestEmail);

    // 5. Resend Invitation
    const userRow = page.locator("tr").filter({ hasText: resendTestEmail });
    await userRow.getByRole("button", { name: "Resend Invite" }).click();
    await expect(
      page.getByText(`Invitation resent successfully to ${resendTestEmail}.`),
    ).toBeVisible();

    // TRIGGER QSTASH WEBHOOK (Test-only local mechanism)
    await manuallyTriggerQStashWebhook(page, resendTestEmail);

    // 6. Wait a moment so docker logs have time to get the second email
    // Sleep briefly to ensure new log entry
    execSync("sleep 2");

    // Capture second token
    // Our extract function fetches tail 1000, which might grab the first one if we aren't careful.
    // Let's modify our logic inline to fetch the LAST token sent.
    let secondToken = "";
    const logs = execSync("docker logs hiron-api --tail 1000 2>&1").toString();
    const cleanLogs = logs.replace(
      /[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g,
      "",
    );
    const lines = cleanLogs.split("\n");
    // Iterate backwards to get the most recent email log
    for (let i = lines.length - 1; i >= 0; i--) {
      if (
        lines[i].includes("DEVELOPMENT EMAIL INTERCEPTED") &&
        lines[i].includes(resendTestEmail)
      ) {
        const match = lines[i].match(/invitation_url='?([^ ']+)'?/);
        if (match && match[1]) {
          const urlString = match[1].replace(/['"]/g, "");
          const url = new URL(urlString);
          const t = url.searchParams.get("token");
          if (t && t !== firstToken) {
            secondToken = t;
            break;
          }
        }
      }
    }

    expect(secondToken).toBeTruthy();
    expect(secondToken).not.toEqual(firstToken);

    // 7. Try first token (should fail because it was revoked)
    await page.context().clearCookies();
    await page.goto(`/accept-invite?token=${firstToken}`);
    await page.getByLabel("New Password *", { exact: true }).fill(newPassword);
    await page.getByLabel("Confirm New Password *").fill(newPassword);
    await page.getByRole("button", { name: "Accept Invitation" }).click();
    await expect(page.getByText("This invitation link is invalid or has expired.")).toBeVisible();

    // 8. Try second token (should succeed)
    await page.goto(`/accept-invite?token=${secondToken}`);
    await page.getByLabel("New Password *", { exact: true }).fill(newPassword);
    await page.getByLabel("Confirm New Password *").fill(newPassword);
    await page.getByRole("button", { name: "Accept Invitation" }).click();
    await expect(page.getByText("Invitation Accepted", { exact: true })).toBeVisible();
  });

  test("3. Invalid token handling", async ({ page }) => {
    await page.goto("/accept-invite?token=some_completely_invalid_token_value_here");
    await page.getByLabel("New Password *", { exact: true }).fill("SecurePassword123!");
    await page.getByLabel("Confirm New Password *").fill("SecurePassword123!");
    await page.getByRole("button", { name: "Accept Invitation" }).click();
    await expect(page.getByText("This invitation link is invalid or has expired.")).toBeVisible();
  });
});
