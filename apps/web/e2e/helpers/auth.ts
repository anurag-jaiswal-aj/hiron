import { Page, expect } from "@playwright/test";
import { execSync } from "child_process";

let cachedTenantId: string | null = null;

async function getTenantId(page: Page): Promise<string> {
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
): Promise<void> {
  const effectiveTenantId = tenantId || (await getTenantId(page));

  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  await page.fill("#tenantId", effectiveTenantId);
  await page.fill("#email", email);
  await page.fill("#password", password);

  await page.click('button[type="submit"]');

  // Wait for redirect away from /login to dashboard /
  await page.waitForURL((url) => url.pathname !== "/login", { timeout: 10000 });
  await expect(page).not.toHaveURL(/\/login$/);
}
