import { Page, expect } from "@playwright/test";
import { execSync } from "child_process";

let cachedTenantId: string | null = null;

async function getTenantId(): Promise<string> {
  if (cachedTenantId) return cachedTenantId;

  try {
    const output = execSync(
      'docker exec hiron-postgres psql -U hiron_user -d hiron_dev -t -c "SELECT id FROM tenants LIMIT 1;"'
    ).toString();
    cachedTenantId = output.trim();
    if (cachedTenantId) {
        return cachedTenantId;
    }
  } catch (error) {
    console.error("Failed to fetch tenant ID from DB:", error);
  }

  throw new Error("Could not determine tenant ID");
}

export async function loginAs(
  page: Page,
  email: string = "admin@acme.com",
  password: string = "SecurePassword123!",
  tenantId?: string
): Promise<string | null> {
  const effectiveTenantId = tenantId || (await getTenantId());



  await page.goto("/login");
  await page.waitForLoadState("domcontentloaded");

  // Wait for the login form to actually render (AuthContext loading resolved)
  await page.waitForSelector("#tenantId", { timeout: 10000 });

  await page.fill("#tenantId", effectiveTenantId);
  await page.fill("#email", email);
  await page.fill("#password", password);

  const responsePromise = page.waitForResponse(response => response.url().includes('/api/v1/auth/login') && response.status() === 200, { timeout: 10000 }).catch(() => null);
  
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
