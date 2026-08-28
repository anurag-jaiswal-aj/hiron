import { Page, expect } from "@playwright/test";
import { execSync } from "child_process";

async function getTenantId(email: string): Promise<string> {
  // Try to use a known tenant if we can't reliably get the user's tenant
  let output = "";
  try {
    output = execSync(
      `docker exec hiron-postgres psql -U hiron_user -d hiron_dev -t -c "SELECT tenant_id FROM users WHERE email = '${email}' LIMIT 1;"`,
    ).toString();

    const match = output.match(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/i);

    if (!match) {
      // Fallback
      output = execSync(
        'docker exec hiron-postgres psql -U hiron_user -d hiron_dev -t -c "SELECT id FROM tenants WHERE slug = \'acme\' LIMIT 1;"',
      ).toString();
      const fallbackMatch = output.match(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/i);
      if (fallbackMatch) return fallbackMatch[0];
      throw new Error(`Failed to extract tenant UUID from docker/psql output: ${output}`);
    }

    return match[0];
  } catch (error) {
    console.error("Failed to fetch tenant ID from DB:", error);
    throw new Error(`Could not determine tenant ID. Original output was: ${output}`);
  }
}

export async function loginAs(
  page: Page,
  email: string = "admin@acme.com",
  password: string = "SecurePassword123!",
  tenantId?: string,
): Promise<string | null> {
  const effectiveTenantId = tenantId || (await getTenantId(email));

  await page.context().clearCookies();
  await page.goto("/login");
  try {
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  } catch {
    // Ignore if not on an active page
  }
  await page.goto("/login");
  page.on("console", (msg) => console.log("PAGE LOG:", msg.text()));
  page.on("pageerror", (err) => console.log("PAGE ERROR:", err.message));
  await page.waitForLoadState("domcontentloaded");

  // Wait for the login form to actually render (AuthContext loading resolved)
  await page.waitForSelector("#tenantId", { timeout: 10000 });

  await page.fill("#tenantId", effectiveTenantId);
  await page.fill("#email", email);
  await page.fill("#password", password);

  const responsePromise = page
    .waitForResponse(
      (response) => response.url().includes("/api/v1/auth/login") && response.status() === 200,
      { timeout: 10000 },
    )
    .catch(() => null);

  await page.click('button[type="submit"]');

  // Wait for redirect away from /login to dashboard and ensure it settles
  await page.waitForURL(/\/dashboard$/, { timeout: 10000 });
  await page.waitForLoadState("networkidle");
  // Wait for the Dashboard page component to mount so Next.js transition is fully finished
  await expect(page.locator("h1").first()).toContainText("Dashboard", { timeout: 10000 });
  await expect(page).toHaveURL(/\/dashboard$/);

  // Allow Next.js App Router internal history state to fully settle
  // WebKit in CI can take several seconds to process the RSC payload and apply history state
  await page.waitForTimeout(3000);

  let token: string | null = null;
  const response = await responsePromise;
  if (response) {
    try {
      const json = await response.json();
      token = json?.data?.accessToken || null;
    } catch (e) {
      // ignore parsing error
    }
  }

  return token;
}
