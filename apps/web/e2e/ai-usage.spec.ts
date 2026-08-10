import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

const mockSummaryData = {
  data: {
    totalCostUsd: 12.34,
    totalTokens: 1000000,
    totalOperations: 50,
    cacheHitRate: 0.45,
    byOperation: [
      {
        operation: "candidate_scoring",
        count: 40,
        costUsd: 10.0,
        avgLatencyMs: 1500
      },
      {
        operation: "resume_parsing",
        count: 10,
        costUsd: 2.34,
        avgLatencyMs: 800
      }
    ],
    byDay: [
      { date: "2026-08-01", costUsd: 5.0, operations: 20 },
      { date: "2026-08-02", costUsd: 7.34, operations: 30 }
    ]
  }
};

const mockEmptySummaryData = {
  data: {
    totalCostUsd: 0,
    totalTokens: 0,
    totalOperations: 0,
    cacheHitRate: 0,
    byOperation: [],
    byDay: []
  }
};

test.describe('AI Usage Analytics Page', () => {
  test('redirects recruiter', async ({ page }) => {
    await loginAs(page, 'recruiter@acme.com');
    await page.goto('/ai-usage');
    await page.waitForURL((url) => url.pathname !== "/ai-usage", { timeout: 10000 });
    expect(page.url()).not.toContain('/ai-usage');
  });

  test('redirects hiring_manager', async ({ page }) => {
    await loginAs(page, 'manager@acme.com');
    await page.goto('/ai-usage');
    await page.waitForURL((url) => url.pathname !== "/ai-usage", { timeout: 10000 });
    expect(page.url()).not.toContain('/ai-usage');
  });

  test('allows org_admin to access and renders correctly', async ({ page }) => {
    await loginAs(page, 'admin@acme.com');
    
    // Mock API
    await page.route('**/api/v1/ai-usage/summary*', async route => {
      await route.fulfill({ json: mockSummaryData });
    });

    await page.goto('/ai-usage');
    
    // Verify headings
    await expect(page.getByRole('heading', { name: 'AI Usage Analytics' })).toBeVisible();
    
    // Verify metrics
    await expect(page.getByText('$12.34')).toBeVisible();
    await expect(page.getByText('1,000,000')).toBeVisible();
    await expect(page.getByText('50', { exact: true })).toBeVisible(); // operations
    await expect(page.getByText('45.0%')).toBeVisible();
    
    // Verify chart heading
    await expect(page.getByRole('heading', { name: 'Daily Cost Trend (USD)' })).toBeVisible();
    
    // Verify operations table
    await expect(page.getByRole('heading', { name: 'Operation Breakdown' })).toBeVisible();
    await expect(page.getByText('candidate_scoring')).toBeVisible();
    await expect(page.getByText('resume_parsing')).toBeVisible();
    await expect(page.getByText('$10.0000')).toBeVisible();
    await expect(page.getByText('1,500 ms')).toBeVisible();
    
    // Verify informational note
    await expect(page.getByText('Note: Token usage and cache hit rate per-operation are not currently provided by the API.')).toBeVisible();
  });

  test('period selector triggers new API call', async ({ page }) => {
    await loginAs(page, 'admin@acme.com');
    
    await page.route('**/api/v1/ai-usage/summary*', async route => {
      if (route.request().url().includes('period=90d')) {
        await route.fulfill({ json: { ...mockSummaryData, data: { ...mockSummaryData.data, totalCostUsd: 100.5 } } });
      } else {
        await route.fulfill({ json: mockSummaryData });
      }
    });

    await page.goto('/ai-usage');
    await expect(page.getByText('$12.34')).toBeVisible();
    
    // Change period
    await page.locator('select').selectOption('90d');
    
    // Verify new data is loaded
    await expect(page.getByText('$100.50')).toBeVisible();
  });

  test('empty state renders correctly', async ({ page }) => {
    await loginAs(page, 'admin@acme.com');
    
    await page.route('**/api/v1/ai-usage/summary*', async route => {
      await route.fulfill({ json: mockEmptySummaryData });
    });

    await page.goto('/ai-usage');
    await expect(page.getByText('No AI Usage Data')).toBeVisible();
  });

  test('error state renders correctly and allows retry', async ({ page }) => {
    await loginAs(page, 'admin@acme.com');
    
    let shouldFail = true;
    await page.route('**/api/v1/ai-usage/summary*', async route => {
      if (shouldFail) {
        await route.fulfill({ status: 500, json: { error: { message: "Internal server error" } } });
      } else {
        await route.fulfill({ json: mockSummaryData });
      }
    });

    await page.goto('/ai-usage');
    await expect(page.getByText('Failed to load AI usage')).toBeVisible();
    
    // Click retry
    shouldFail = false;
    await page.getByRole('button', { name: 'Retry' }).click();
    
    // Verify success
    await expect(page.getByText('$12.34')).toBeVisible();
  });

  test.describe('Responsive behavior', () => {
    test.use({ viewport: { width: 390, height: 844 } });
    test('mobile layout has no horizontal overflow', async ({ page }) => {
      await loginAs(page, 'admin@acme.com');
      await page.route('**/api/v1/ai-usage/summary*', async route => {
        await route.fulfill({ json: mockSummaryData });
      });
      await page.goto('/ai-usage');
      await expect(page.getByText('$12.34')).toBeVisible();
      
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(scrollWidth).toBeLessThanOrEqual(390);
    });
  });

  test.describe('Tablet behavior', () => {
    test.use({ viewport: { width: 768, height: 1024 } });
    test('tablet layout has no horizontal overflow', async ({ page }) => {
      await loginAs(page, 'admin@acme.com');
      await page.route('**/api/v1/ai-usage/summary*', async route => {
        await route.fulfill({ json: mockSummaryData });
      });
      await page.goto('/ai-usage');
      await expect(page.getByText('$12.34')).toBeVisible();
      
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(scrollWidth).toBeLessThanOrEqual(768);
    });
  });
});
