import { Page, expect } from "@playwright/test";
import { execSync } from "child_process";

let cachedTenantId: string | null = null;

async function getTenantId(): Promise<string> {
  if (cachedTenantId) return cachedTenantId;

  let output = "";
  try {
    output = execSync(
      'docker exec hiron-postgres psql -U hiron_user -d hiron_dev -t -c "SELECT id FROM tenants LIMIT 1;"',
    ).toString();

    const match = output.match(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/i);

    if (!match) {
      throw new Error(`Failed to extract tenant UUID from docker/psql output: ${output}`);
    }

    cachedTenantId = match[0];
    return cachedTenantId;
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
  const effectiveTenantId = tenantId || (await getTenantId());

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

  // Wait for redirect away from /login to dashboard /
  await page.waitForURL((url) => url.pathname !== "/login", { timeout: 10000 });
  await expect(page).not.toHaveURL(/\/login$/);

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
