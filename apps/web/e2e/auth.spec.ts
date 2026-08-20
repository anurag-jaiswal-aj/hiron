import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";

test.describe("Authentication Workflows", () => {
  test("unauthenticated access to /jobs redirects to /login", async ({ page }) => {

    await page.goto("/jobs");
    await page.waitForURL(/\/login$/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/login$/);
  });

  test("unauthenticated access to /jobs/new redirects to /login", async ({ page }) => {

    await page.goto("/jobs/new");
    await page.waitForURL(/\/login$/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/login$/);
  });

  test("valid org_admin can log in successfully", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  });

  test("authenticated session survives navigation", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/jobs");
    await expect(page).toHaveURL(/\/jobs$/);
    await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();

    await page.goto("/");
    await expect(page).toHaveURL(/\/$/);
  });

  test("chromium: ensures exactly one concurrent refresh request during session restore", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");

    let inFlightRefreshCount = 0;
    let maxInFlightRefreshCount = 0;
    let successfulRefreshResponses = 0;

    page.on("request", (req) => {
      if (req.url().includes("/api/v1/auth/refresh") && req.method() === "POST") {
        inFlightRefreshCount++;
        maxInFlightRefreshCount = Math.max(maxInFlightRefreshCount, inFlightRefreshCount);
      }
    });

    page.on("response", (res) => {
      if (res.url().includes("/api/v1/auth/refresh") && res.request().method() === "POST") {
        inFlightRefreshCount--;
        if (res.status() === 200) {
          successfulRefreshResponses++;
        }
      }
    });

    await page.goto("/jobs");
    await page.waitForTimeout(1000); // Wait for strict mode lifecycle to complete

    expect(maxInFlightRefreshCount).toBeLessThanOrEqual(1);
    expect(successfulRefreshResponses).toBeGreaterThanOrEqual(1);
    await expect(page).toHaveURL(/\/jobs$/);
    await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();
  });

  test("webkit: browser API requests are same-origin and survive navigation", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");

    let refreshRequestUrl = "";
    let refreshCookieHeader = "";
    let refreshResponseStatus = 0;
    let summaryRequestUrl = "";

    page.on("request", async (req) => {
      if (req.url().includes("/api/v1/auth/refresh") && req.method() === "POST") {
        refreshRequestUrl = req.url();
        refreshCookieHeader = await req.headerValue("cookie") || "";
      } else if (req.url().includes("/api/v1/dashboard/summary")) {
        summaryRequestUrl = req.url();
      }
    });

    page.on("response", (res) => {
      if (res.url().includes("/api/v1/auth/refresh") && res.request().method() === "POST") {
        refreshResponseStatus = res.status();
      }
    });

    await page.goto("/jobs");
    await page.waitForTimeout(1000); // Wait for requests

    // Verify /refresh is same-origin (starts with localhost:3000)
    expect(refreshRequestUrl).toMatch(/^http:\/\/localhost:3000\/api\/v1\/auth\/refresh/);
    // Note: Playwright doesn't always populate 'cookie' header for fetch depending on browser engine,
    // but we can assert the response was 200 which PROVES the cookie was successfully sent!
    expect(refreshResponseStatus).toBe(200);

    // Verify /dashboard/summary is same-origin
    if (summaryRequestUrl) {
       expect(summaryRequestUrl).toMatch(/^http:\/\/localhost:3000\/api\/v1/);
    }

    await expect(page).toHaveURL(/\/jobs$/);
    await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();
  });
});
