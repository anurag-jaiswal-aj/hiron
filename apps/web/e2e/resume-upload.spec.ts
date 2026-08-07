import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";
import path from "path";
import fs from "fs";

test.describe("Resume Upload UI", () => {
  const dummyPdfPath = path.join(__dirname, "dummy.pdf");
  const dummyDocxPath = path.join(__dirname, "dummy.docx");
  const dummyTxtPath = path.join(__dirname, "dummy.txt");
  const dummyJpgPath = path.join(__dirname, "dummy.jpg");
  const dummyLargePdfPath = path.join(__dirname, "dummy-large.pdf");

  test.beforeAll(() => {
    fs.writeFileSync(dummyPdfPath, "%PDF-1.4 sample");
    fs.writeFileSync(dummyDocxPath, "PK\\x03\\x04 sample docx");
    fs.writeFileSync(dummyTxtPath, "Sample text resume");
    fs.writeFileSync(dummyJpgPath, "not a valid resume");
    // Create an 11MB file
    const largeBuffer = Buffer.alloc(11 * 1024 * 1024, "a");
    fs.writeFileSync(dummyLargePdfPath, largeBuffer);
  });

  test.afterAll(() => {
    [dummyPdfPath, dummyDocxPath, dummyTxtPath, dummyJpgPath, dummyLargePdfPath].forEach((file) => {
      if (fs.existsSync(file)) fs.unlinkSync(file);
    });
  });

  test("org_admin can reach the Resume Upload UI", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/candidates/upload");
    await expect(page.locator("h1", { hasText: "Upload Resumes" })).toBeVisible();
  });

  test("recruiter can reach the Resume Upload UI", async ({ page }) => {
    await loginAs(page, "recruiter@acme.com", "SecurePassword123!");
    await page.goto("/candidates/upload");
    await expect(page.locator("h1", { hasText: "Upload Resumes" })).toBeVisible();
  });

  test("hiring_manager cannot perform upload and is redirected", async ({ page }) => {
    await loginAs(page, "manager@acme.com", "SecurePassword123!");
    await page.goto("/candidates/upload");
    await page.waitForURL("/candidates");
    await expect(page).toHaveURL(/\/candidates$/);
  });

  test("unauthenticated user is redirected appropriately", async ({ page }) => {
    await page.goto("/candidates/upload");
    await page.waitForURL("**/login");
    await expect(page).toHaveURL(/.*\/login/);
  });

  test("invalid file type is rejected client-side", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/candidates/upload");
    
    const fileInput = page.getByTestId("resume-upload-input");
    await fileInput.setInputFiles(dummyJpgPath);
    
    await expect(page.getByText("dummy.jpg")).toBeVisible();
    await expect(page.getByText("Unsupported file type")).toBeVisible();
  });

  test("file larger than 10 MB is rejected client-side", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/candidates/upload");
    
    const fileInput = page.getByTestId("resume-upload-input");
    await fileInput.setInputFiles(dummyLargePdfPath);
    
    await expect(page.getByText("dummy-large.pdf")).toBeVisible();
    await expect(page.getByText("File exceeds 10 MB limit")).toBeVisible();
  });

  test("valid PDF can be selected and successful upload reaches the REAL backend", async ({ page }) => {
    page.on("console", msg => console.log("BROWSER CONSOLE:", msg.text()));
    page.on("requestfailed", request => console.log("FAILED REQUEST:", request.url(), request.failure()?.errorText));

    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/candidates/upload");
    
    const fileInput = page.getByTestId("resume-upload-input");
    await fileInput.setInputFiles(dummyPdfPath);
    
    await expect(page.getByText("dummy.pdf")).toBeVisible();
    await expect(page.getByText("Ready to upload")).toBeVisible();
    
    // Intercept API to verify it reaches backend
    const uploadPromise = page.waitForResponse(response => response.url().includes("/api/v1/resumes/upload") && response.request().method() === "POST");
    
    await page.getByRole("button", { name: "Start Upload" }).click();
    
    const uploadResponse = await uploadPromise;
    expect(uploadResponse.status()).toBe(202); // 202 Accepted per API contract
    
    // Wait for parsing state or parsed state
    await expect(page.getByText("Parsed").or(page.getByText("Parsing..."))).toBeVisible();
  });

  test("valid DOCX can be selected and successful upload reaches the REAL backend", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/candidates/upload");
    const fileInput = page.getByTestId("resume-upload-input");
    await fileInput.setInputFiles(dummyDocxPath);
    await expect(page.getByText("dummy.docx")).toBeVisible();
    const uploadPromise = page.waitForResponse(response => response.url().includes("/api/v1/resumes/upload") && response.request().method() === "POST");
    await page.getByRole("button", { name: "Start Upload" }).click();
    const uploadResponse = await uploadPromise;
    expect(uploadResponse.status()).toBe(202);
  });

  test("valid TXT can be selected and successful upload reaches the REAL backend", async ({ page }) => {
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/candidates/upload");
    const fileInput = page.getByTestId("resume-upload-input");
    await fileInput.setInputFiles(dummyTxtPath);
    await expect(page.getByText("dummy.txt")).toBeVisible();
    const uploadPromise = page.waitForResponse(response => response.url().includes("/api/v1/resumes/upload") && response.request().method() === "POST");
    await page.getByRole("button", { name: "Start Upload" }).click();
    const uploadResponse = await uploadPromise;
    expect(uploadResponse.status()).toBe(202);
  });

  test("responsive behavior works at 390px mobile width without horizontal page overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await loginAs(page, "admin@acme.com", "SecurePassword123!");
    await page.goto("/candidates/upload");
    
    const hasHorizontalOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    
    expect(hasHorizontalOverflow).toBe(false);
  });
});
