import { expect, type Browser, type BrowserContext, type Page } from '@playwright/test'
import { BACKEND_URL } from '../playwright.config'

export const STAFF_PHONE = '+201999000001'
// Seeded by `manage.py e2e_seed`; the mocked browser position resolves to المحطة.
export const STATION_POSITION = { latitude: 30.0001, longitude: 32.0001 }

let counter = 0
const runId = String(Date.now()).slice(-6)

/** A phone number no other test uses. */
export const newPhone = () => `+2010${runId}${String(++counter).padStart(2, '0')}`
/** Unique notes so a test finds its own request even though the database is shared. */
export const newNote = (label: string) => `e2e-${label}-${runId}-${++counter}`

export interface Session {
  context: BrowserContext
  page: Page
  phone: string
}

async function currentCode(page: Page, phone: string) {
  const res = await page.request.get(`${BACKEND_URL}/e2e/otp/`, { params: { phone } })
  return res.ok() ? ((await res.json()).code as string) : ''
}

/** The code sent after `previous` (the phone may have had earlier codes, e.g. a repeated staff login). */
async function newCode(page: Page, phone: string, previous: string) {
  let code = ''
  await expect
    .poll(async () => {
      code = await currentCode(page, phone)
      return code !== '' && code !== previous
    })
    .toBe(true)
  return code
}

/** Sign in through the real OTP screens in a fresh browser context. */
export async function signIn(
  browser: Browser,
  phone = newPhone(),
  options: { geolocation?: boolean } = {},
): Promise<Session> {
  const context = await browser.newContext({
    locale: 'ar-EG',
    ...(options.geolocation ? { geolocation: STATION_POSITION, permissions: ['geolocation'] } : {}),
  })
  const page = await context.newPage()
  await page.goto('/login')
  await page.getByLabel('رقم الهاتف').fill(phone)
  const previous = await currentCode(page, phone)
  await page.getByRole('button', { name: 'إرسال رمز التحقق' }).click()
  const code = await newCode(page, phone, previous)
  await page.getByLabel(/رمز التحقق/).fill(code)
  await page.getByRole('button', { name: 'دخول' }).click()
  await expect(page.getByRole('heading', { name: /أهلًا/ })).toBeVisible()
  return { context, page, phone }
}

export async function chooseRole(page: Page, role: 'customer' | 'driver') {
  await page.getByRole('button', { name: role === 'customer' ? 'اطلب توصيلة' : 'أنا سائق' }).click()
  await expect(page).toHaveURL(role === 'customer' ? /\/customer$/ : /\/driver$/)
}

export async function signInAs(browser: Browser, role: 'customer' | 'driver') {
  const session = await signIn(browser, newPhone(), { geolocation: role === 'driver' })
  await chooseRole(session.page, role)
  return session
}

/** Call the JSON API as the signed-in user of `page` (for assertions the UI does not show). */
export async function api<T = unknown>(page: Page, method: 'GET' | 'POST', path: string, body?: unknown) {
  return page.evaluate(
    async ({ method, path, body }) => {
      const tokens = JSON.parse(localStorage.getItem('tariqi.tokens') ?? '{}')
      const res = await fetch(`/api${path}`, {
        method,
        headers: { Authorization: `Bearer ${tokens.access}`, 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      })
      return { status: res.status, body: (await res.json()) as T }
    },
    { method, path, body },
  )
}

export async function createRequest(
  page: Page,
  options: { note: string; pickup?: string; destination?: string } = { note: '' },
) {
  await page.getByRole('link', { name: 'اطلب توصيلة جديدة' }).click()
  await page.getByLabel('مكان الركوب').selectOption({ label: options.pickup ?? 'المحطة' })
  await page.getByLabel('الوجهة').selectOption({ label: options.destination ?? 'الأربعين' })
  await page.getByLabel(/ملاحظات للالتقاء/).fill(options.note)
  await page.getByRole('button', { name: 'نشر الطلب' }).click()
  await expect(page.getByRole('heading', { name: 'تفاصيل الطلب' })).toBeVisible()
  const id = Number(page.url().match(/requests\/(\d+)/)![1])
  return id
}

/** Staff verifies a driver through the admin dashboard. */
export async function verifyDriver(browser: Browser, driverPhone: string) {
  const staff = await signIn(browser, STAFF_PHONE)
  await staff.page.goto('/admin')
  await staff.page.getByRole('tab', { name: 'المستخدمون' }).click()
  await staff.page.getByPlaceholder('بحث بالهاتف أو الاسم').fill(driverPhone)
  await staff.page.getByRole('button', { name: 'بحث' }).click()
  const row = staff.page.getByTestId('admin-user').filter({ hasText: driverPhone })
  await row.getByRole('button', { name: 'توثيق السائق' }).click()
  await expect(row.getByRole('button', { name: 'إلغاء التوثيق' })).toBeVisible()
  await staff.context.close()
}

/** A verified driver, live in المحطة heading to الأربعين, on /driver. */
export async function goLive(browser: Browser) {
  const driver = await signInAs(browser, 'driver')
  await verifyDriver(browser, driver.phone)
  await driver.page.reload()
  await driver.page.getByLabel('الوجهة').selectOption({ label: 'الأربعين' })
  await driver.page.getByRole('button', { name: 'تحديد الوجهة' }).click()
  await expect(driver.page.getByText('تنتهي')).toBeVisible()
  await driver.page.getByRole('button', { name: 'ابدأ استقبال الطلبات' }).click()
  await expect(driver.page.getByTestId('freshness')).toContainText('حديث')
  return driver
}

export function matchedRequest(page: Page, note: string) {
  return page.getByTestId('matched-request').filter({ hasText: note })
}

export async function openMatches(page: Page) {
  await page.goto('/driver/requests')
  await expect(page.getByRole('heading', { name: 'الطلبات المناسبة' })).toBeVisible()
}

export const interestCard = (customer: Page, driverPhone: string) =>
  customer.getByTestId('interest').filter({ has: customer.locator(`a[href="tel:${driverPhone}"]`) })

export async function chooseDriver(customer: Page, driverPhone: string, price = '45') {
  await interestCard(customer, driverPhone)
    .getByRole('button', { name: 'اتفقنا، أريد تأكيد هذا السائق' })
    .click()
  await customer.getByLabel('السعر المتفق عليه').fill(price)
  await customer.getByRole('button', { name: 'تأكيد المشوار' }).click()
}
