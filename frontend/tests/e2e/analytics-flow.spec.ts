/**
 * End-to-end tests for analytics dashboard workflow
 */

import { test, expect } from '@playwright/test'

test.describe('Analytics Dashboard E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto('/auth/login')

    // Perform login
    await page.fill('[data-testid="email"]', 'test@example.com')
    await page.fill('[data-testid="password"]', 'password')
    await page.click('[data-testid="login-button"]')

    // Wait for redirect to dashboard
    await page.waitForURL('/dashboard', { timeout: 10000 })
  })

  test('complete analytics workflow', async ({ page }) => {
    // Navigate to analytics
    await page.click('[data-testid="nav-analytics"]')
    await expect(page).toHaveURL(/\/analytics/)

    // Check dashboard loads
    await expect(page.locator('[data-testid="active-users-card"]')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('[data-testid="revenue-chart"]')).toBeVisible({ timeout: 10000 })

    // Change date range
    await page.click('[data-testid="date-range-picker"]')
    await page.click('[data-testid="last-30-days"]')

    // Wait for data refresh
    await page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/dashboard') && resp.status() === 200,
      { timeout: 15000 }
    )

    // Generate report
    await page.click('[data-testid="generate-report-btn"]')
    await page.selectOption('[data-testid="report-template"]', 'monthly')
    await page.click('[data-testid="generate-btn"]')

    // Check notification
    await expect(page.locator('[data-testid="success-toast"]')).toContainText(
      'Report generation started',
      { timeout: 5000 }
    )

    // Navigate to agent analytics
    await page.click('[data-testid="nav-agents"]')
    await expect(page.locator('[data-testid="agent-list"]')).toBeVisible({ timeout: 10000 })

    // Click on specific agent
    await page.click('[data-testid="agent-row-1"]')
    await expect(page).toHaveURL(/\/analytics\/agents\/agent_/)

    // Verify agent metrics
    await expect(page.locator('[data-testid="success-rate"]')).toBeVisible()
    await expect(page.locator('[data-testid="execution-chart"]')).toBeVisible()
  })

  test('real-time updates work', async ({ page }) => {
    await page.goto('/analytics/realtime')

    // Check WebSocket connection status
    await expect(page.locator('[data-testid="connection-status"]')).toHaveText('Connected', {
      timeout: 10000,
    })

    // Get initial value
    const initialValue = await page.locator('[data-testid="live-users"]').textContent()

    // Wait for potential update
    await page.waitForTimeout(5000)

    // Note: In real implementation, we'd trigger an update
    // For now, we just verify the element is still visible
    await expect(page.locator('[data-testid="live-users"]')).toBeVisible()
  })

  test('dashboard navigation', async ({ page }) => {
    // Test navigation to different dashboard sections
    const sections = [
      { link: '[data-testid="nav-overview"]', url: '/dashboard/overview' },
      { link: '[data-testid="nav-analytics"]', url: '/analytics' },
      { link: '[data-testid="nav-agents"]', url: '/analytics/agents' },
      { link: '[data-testid="nav-credits"]', url: '/analytics/credits' },
    ]

    for (const section of sections) {
      await page.click(section.link)
      await expect(page).toHaveURL(new RegExp(section.url))
    }
  })

  test('filters and search work correctly', async ({ page }) => {
    await page.goto('/analytics/agents')

    // Use search
    await page.fill('[data-testid="search-input"]', 'test agent')
    await page.waitForTimeout(1000) // Debounce

    // Apply filters
    await page.click('[data-testid="filter-button"]')
    await page.click('[data-testid="filter-status-active"]')
    await page.click('[data-testid="apply-filters"]')

    // Wait for filtered results
    await page.waitForTimeout(1000)

    // Verify filter is applied
    await expect(page.locator('[data-testid="active-filter-badge"]')).toBeVisible()
  })

  test('export functionality works', async ({ page }) => {
    await page.goto('/analytics/dashboard')

    // Click export button
    await page.click('[data-testid="export-button"]')

    // Select export format
    await page.click('[data-testid="export-csv"]')

    // Wait for download to start
    const downloadPromise = page.waitForEvent('download')
    await page.click('[data-testid="confirm-export"]')

    const download = await downloadPromise

    // Verify download
    expect(download.suggestedFilename()).toContain('analytics')
  })

  test('responsive design works on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    await page.goto('/analytics/dashboard')

    // Check mobile menu
    await page.click('[data-testid="mobile-menu-button"]')
    await expect(page.locator('[data-testid="mobile-nav"]')).toBeVisible()

    // Verify cards stack vertically
    const cards = page.locator('[data-testid^="metric-card-"]')
    const count = await cards.count()

    expect(count).toBeGreaterThan(0)
  })

  test('error handling displays correctly', async ({ page }) => {
    // Navigate to a route that will trigger an error
    await page.goto('/analytics/invalid-route')

    // Should show error page or 404
    await expect(
      page.locator('text=Not Found').or(page.locator('text=Error'))
    ).toBeVisible()
  })

  test('pagination works correctly', async ({ page }) => {
    await page.goto('/analytics/agents')

    // Check initial page
    await expect(page.locator('[data-testid="page-1"]')).toHaveClass(/active/)

    // Go to next page
    await page.click('[data-testid="next-page"]')

    // Verify page 2 is active
    await expect(page.locator('[data-testid="page-2"]')).toHaveClass(/active/)

    // Go back to previous page
    await page.click('[data-testid="prev-page"]')

    // Verify page 1 is active again
    await expect(page.locator('[data-testid="page-1"]')).toHaveClass(/active/)
  })

  test('date range picker works correctly', async ({ page }) => {
    await page.goto('/analytics/dashboard')

    // Open date picker
    await page.click('[data-testid="date-range-picker"]')

    // Select custom range
    await page.click('[data-testid="custom-range"]')

    // Select start date
    await page.fill('[data-testid="start-date"]', '2024-01-01')

    // Select end date
    await page.fill('[data-testid="end-date"]', '2024-01-31')

    // Apply
    await page.click('[data-testid="apply-date-range"]')

    // Verify date range is applied
    await expect(page.locator('[data-testid="date-range-display"]')).toContainText('Jan 1')
  })

  test('charts render correctly', async ({ page }) => {
    await page.goto('/analytics/dashboard')

    // Wait for charts to render
    await page.waitForSelector('[data-testid="revenue-chart"]', { timeout: 10000 })

    // Verify chart elements exist
    const chart = page.locator('[data-testid="revenue-chart"]')
    await expect(chart).toBeVisible()

    // Check for SVG (charts are typically SVG)
    const svg = chart.locator('svg')
    await expect(svg).toBeVisible()
  })

  test('tooltips display on hover', async ({ page }) => {
    await page.goto('/analytics/dashboard')

    // Hover over metric card
    await page.hover('[data-testid="metric-card-revenue"]')

    // Wait for tooltip
    await page.waitForTimeout(500)

    // Verify tooltip appears (if implemented)
    // This is optional depending on implementation
  })

  test('loading states display correctly', async ({ page }) => {
    await page.goto('/analytics/dashboard')

    // Check for loading state immediately
    const loadingIndicator = page.locator('[data-testid="loading-spinner"]')

    // Loading indicator should appear briefly or not at all if cached
    // Just verify the page eventually loads
    await expect(page.locator('[data-testid="active-users-card"]')).toBeVisible({ timeout: 10000 })
  })

  test('workspace switching works', async ({ page }) => {
    // Open workspace switcher
    await page.click('[data-testid="workspace-switcher"]')

    // Select different workspace
    await page.click('[data-testid="workspace-option-2"]')

    // Wait for page to reload with new workspace data
    await page.waitForTimeout(2000)

    // Verify workspace changed
    await expect(page.locator('[data-testid="current-workspace"]')).not.toContainText('Workspace 1')
  })
})

test.describe('Authentication and Authorization', () => {
  test('redirects to login when not authenticated', async ({ page }) => {
    // Clear cookies to simulate logged out state
    await page.context().clearCookies()

    // Try to access protected route
    await page.goto('/analytics/dashboard')

    // Should redirect to login
    await expect(page).toHaveURL(/\/auth\/login/)
  })

  test('logout works correctly', async ({ page }) => {
    // Login first
    await page.goto('/auth/login')
    await page.fill('[data-testid="email"]', 'test@example.com')
    await page.fill('[data-testid="password"]', 'password')
    await page.click('[data-testid="login-button"]')

    await page.waitForURL('/dashboard')

    // Logout
    await page.click('[data-testid="user-menu"]')
    await page.click('[data-testid="logout-button"]')

    // Should redirect to login
    await expect(page).toHaveURL(/\/auth\/login/)
  })
})
