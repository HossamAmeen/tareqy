import { expect, test } from '@playwright/test'
import { BACKEND_URL } from '../playwright.config'
import { signIn, signInAs, STAFF_PHONE } from './helpers'

test('staff can open the admin dashboard and see KPIs', async ({ browser }) => {
  const { page } = await signIn(browser, STAFF_PHONE)
  await page.getByRole('link', { name: 'لوحة الإدارة' }).click()
  await expect(page.getByRole('heading', { name: 'لوحة الإدارة' })).toBeVisible()
  await expect(page.getByTestId('kpis')).toContainText('الطلبات المنشورة')
  for (const tab of ['المستخدمون', 'الطلبات', 'البلاغات']) {
    await page.getByRole('tab', { name: tab }).click()
    await expect(page.getByRole('tab', { name: tab })).toHaveAttribute('aria-selected', 'true')
  }
})

test('customers and drivers cannot reach the admin dashboard', async ({ browser }) => {
  for (const role of ['customer', 'driver'] as const) {
    const { page } = await signInAs(browser, role)
    await page.goto('/admin')
    await expect(page.getByRole('heading', { name: 'لوحة الإدارة' })).toHaveCount(0)
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('link', { name: 'لوحة الإدارة' })).toHaveCount(0)
  }
})

test('staff can suspend an account, which then cannot sign in again', async ({ browser }) => {
  const victim = await signIn(browser)
  await victim.context.close()

  const staff = await signIn(browser, STAFF_PHONE)
  await staff.page.goto('/admin')
  await staff.page.getByRole('tab', { name: 'المستخدمون' }).click()
  await staff.page.getByPlaceholder('بحث بالهاتف أو الاسم').fill(victim.phone)
  await staff.page.getByRole('button', { name: 'بحث' }).click()
  const row = staff.page.getByTestId('admin-user').filter({ hasText: victim.phone })
  staff.page.once('dialog', (dialog) => dialog.accept())
  await row.getByRole('button', { name: 'إيقاف الحساب' }).click()
  await expect(row).toContainText('موقوف')

  // A new sign-in attempt for the suspended account is rejected.
  const context = await browser.newContext({ locale: 'ar-EG' })
  const page = await context.newPage()
  await page.goto('/login')
  await page.getByLabel('رقم الهاتف').fill(victim.phone)
  const sent = page.waitForResponse('**/api/auth/otp/request/')
  await page.getByRole('button', { name: 'إرسال رمز التحقق' }).click()
  await sent
  const otp = await page.request.get(`${BACKEND_URL}/e2e/otp/`, { params: { phone: victim.phone } })
  await page.getByLabel(/رمز التحقق/).fill((await otp.json()).code)
  await page.getByRole('button', { name: 'دخول' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page).toHaveURL(/\/login$/)
})
