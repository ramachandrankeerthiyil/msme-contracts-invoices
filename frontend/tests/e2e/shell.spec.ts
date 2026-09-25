import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

// PLT-001 end-to-end: runs against the full stack behind the gateway.

const ROUTES: { path: string; title: string; activeNav?: string; breadcrumb: boolean }[] = [
  { path: '/', title: 'Overview', activeNav: 'Home', breadcrumb: false },
  { path: '/contracts/dashboard', title: 'Contract dashboard', activeNav: 'Dashboard', breadcrumb: true },
  { path: '/contracts', title: 'All contracts', activeNav: 'All contracts', breadcrumb: true },
  { path: '/contracts/upload', title: 'Upload contract', activeNav: 'Upload contract', breadcrumb: true },
  { path: '/contracts/some-id', title: 'Contract not found', activeNav: 'All contracts', breadcrumb: true },
  { path: '/invoices/dashboard', title: 'Invoice dashboard', activeNav: 'Dashboard', breadcrumb: true },
  { path: '/invoices', title: 'All invoices', activeNav: 'All invoices', breadcrumb: true },
  { path: '/invoices/upload', title: 'Upload invoices', activeNav: 'Upload invoices', breadcrumb: true },
  { path: '/no/such/page', title: 'Page not found', breadcrumb: false },
]

const mainNav = (page: Page) => page.getByRole('navigation', { name: 'Main', exact: true })

for (const route of ROUTES) {
  test(`PLT_001_AC1_AC3_AC4 shell on ${route.path}`, async ({ page }) => {
    await page.goto(route.path)

    await expect(page.getByRole('banner').getByRole('link', { name: 'MSME Contracts & Invoices' })).toBeVisible()
    await expect(mainNav(page)).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(route.title)
    await expect(page).toHaveTitle(`${route.title} · MSME Contracts & Invoices`)
    await expect(page.getByRole('navigation', { name: 'Breadcrumb' })).toHaveCount(route.breadcrumb ? 1 : 0)

    const current = mainNav(page).locator('[aria-current="page"]')
    if (route.activeNav) {
      await expect(current).toHaveCount(1)
      await expect(current).toHaveText(route.activeNav)
    } else {
      await expect(current).toHaveCount(0)
    }
  })

  test(`PLT_001_AC11 accessibility and minimum text size on ${route.path}`, async ({ page }) => {
    await page.goto(route.path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze()
    const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
    expect(serious, JSON.stringify(serious.map((v) => [v.id, v.nodes.map((n) => n.target)]), null, 2)).toEqual([])

    const tooSmall = await page.evaluate(() => {
      const offenders: string[] = []
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        const element = node.parentElement
        if (!element || !node.textContent?.trim()) continue
        const size = parseFloat(getComputedStyle(element).fontSize)
        if (size < 16) offenders.push(`${size}px: ${node.textContent.trim().slice(0, 40)}`)
      }
      return offenders
    })
    expect(tooSmall).toEqual([])
  })
}

test('PLT_001_AC2 sidebar groups with icons and labels', async ({ page }) => {
  await page.goto('/')
  const nav = mainNav(page)

  await expect(nav.getByRole('list', { name: 'Contracts' }).getByRole('link')).toHaveText([
    'Dashboard',
    'All contracts',
    'Upload contract',
  ])
  await expect(nav.getByRole('list', { name: 'Invoices' }).getByRole('link')).toHaveText([
    'Dashboard',
    'All invoices',
    'Upload invoices',
  ])
  for (const link of await nav.getByRole('link').all()) {
    await expect(link.locator('svg')).toHaveCount(1)
  }
})

test('PLT_001_AC5 Home links to both dashboards', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('link', { name: 'Go to invoice dashboard' }).click()
  await expect(page).toHaveURL(/\/invoices\/dashboard$/)
  await page.goBack()
  await page.getByRole('link', { name: 'Go to contract dashboard' }).click()
  await expect(page).toHaveURL(/\/contracts\/dashboard$/)
})

test('PLT_001_AC6 deep links keep their query string and Back restores the view', async ({ page }) => {
  await page.goto('/invoices?status=outstanding&q=acme')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('All invoices')

  await mainNav(page).getByRole('link', { name: 'All contracts' }).click()
  await expect(page).toHaveURL(/\/contracts$/)
  await page.goBack()

  await expect(page).toHaveURL(/\/invoices\?status=outstanding&q=acme$/)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('All invoices')
})

test.describe('PLT_001_AC7 narrow screens', () => {
  test.use({ viewport: { width: 800, height: 900 } })

  test('sidebar collapses behind a Menu button', async ({ page }) => {
    await page.goto('/')
    await expect(mainNav(page)).toBeHidden()

    const menuButton = page.getByRole('button', { name: 'Menu' })
    await menuButton.click()
    const dialog = page.getByRole('dialog', { name: 'Main menu' })
    await expect(dialog).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
    await expect(menuButton).toBeFocused()

    await menuButton.click()
    await dialog.getByRole('link', { name: 'All invoices' }).click()
    await expect(dialog).toBeHidden()
    await expect(page).toHaveURL(/\/invoices$/)
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused()
  })
})

test.describe('PLT_001_AC8 keyboard', () => {
  test('first Tab reaches the skip link, which jumps to the content', async ({ page }) => {
    await page.goto('/')

    await page.keyboard.press('Tab')
    const skip = page.getByRole('link', { name: 'Skip to content' })
    await expect(skip).toBeFocused()
    await expect(skip).toBeVisible()
    await page.keyboard.press('Enter')
    await expect(page.locator('#content')).toBeFocused()
  })

  test('navigation works by keyboard alone and focuses the new heading', async ({ page }) => {
    await page.goto('/')

    let reached = false
    for (let i = 0; i < 30 && !reached; i++) {
      await page.keyboard.press('Tab')
      reached = await page.evaluate(() => document.activeElement?.textContent?.trim() === 'All invoices')
    }
    expect(reached).toBe(true)
    await page.keyboard.press('Enter')

    await expect(page).toHaveURL(/\/invoices$/)
    await expect(page.getByRole('heading', { level: 1 })).toBeFocused()
  })
})

test('PLT_001_AC9 unknown page offers a way back', async ({ page }) => {
  await page.goto('/definitely/not/here')
  const main = page.getByRole('main')

  await expect(main.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/')
  await expect(main.getByRole('link', { name: 'Contract dashboard' })).toBeVisible()
  await expect(main.getByRole('link', { name: 'Invoice dashboard' })).toBeVisible()
})

test('PLT_001_AC10 the UI still loads when an API is unavailable', async ({ page }) => {
  await page.route('**/api/**', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'SERVICE_UNAVAILABLE', message: 'down', request_id: 'x' } }),
    }),
  )
  await page.goto('/invoices/dashboard')

  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Invoice dashboard')
  await mainNav(page).getByRole('link', { name: 'All contracts' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('All contracts')
})
