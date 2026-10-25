import { expect, test, type Browser } from '@playwright/test'
import { BACKEND_URL } from '../playwright.config'
import {
  api,
  chooseDriver,
  interestCard,
  createRequest,
  goLive,
  matchedRequest,
  newNote,
  openMatches,
  signIn,
  signInAs,
  STAFF_PHONE,
} from './helpers'

async function showInterest(driverPage: import('@playwright/test').Page, note: string) {
  await openMatches(driverPage)
  const card = matchedRequest(driverPage, note)
  await card.getByRole('button', { name: 'مهتم' }).click()
  await expect(card.getByRole('button', { name: 'سحب الاهتمام' })).toBeVisible()
}

/** Customer with an open request and one live, interested driver. */
async function interestedPair(browser: Browser) {
  const driver = await goLive(browser)
  const customer = await signInAs(browser, 'customer')
  const note = newNote('trip')
  const requestId = await createRequest(customer.page, { note })
  await showInterest(driver.page, note)
  await customer.page.reload()
  return { driver, customer, note, requestId }
}

/** …and the trip confirmed; the customer is on the request page, the driver on its trip page. */
async function confirmedTrip(browser: Browser) {
  const pair = await interestedPair(browser)
  await chooseDriver(pair.customer.page, pair.driver.phone, '45')
  await expect(pair.customer.page.getByText('تم تأكيد المشوار')).toBeVisible()
  await pair.driver.page.goto('/driver/interests')
  await pair.driver.page.getByRole('link', { name: 'تفاصيل المشوار' }).click()
  await expect(pair.driver.page.getByRole('heading', { name: 'تفاصيل المشوار' })).toBeVisible()
  return pair
}

test('AC8: confirming with a price links exactly one driver; a second confirmation is refused', async ({
  browser,
}) => {
  const first = await interestedPair(browser)
  // A second driver also shows interest in the same request.
  const second = await goLive(browser)
  const note = first.note
  await showInterest(second.page, note)

  // Two customer tabs, both showing both drivers, race to confirm different drivers.
  const tab2 = await first.customer.context.newPage()
  await tab2.goto(`/customer/requests/${first.requestId}`)
  await first.customer.page.reload()
  await expect(first.customer.page.getByTestId('interest')).toHaveCount(2)
  await expect(tab2.getByTestId('interest')).toHaveCount(2)

  await chooseDriver(first.customer.page, first.driver.phone, '40')
  await expect(first.customer.page.getByText('تم تأكيد المشوار')).toBeVisible()

  await chooseDriver(tab2, second.phone, '30')
  await expect(tab2.getByRole('alert')).toContainText(/no longer be changed|already|CONFIRMED/)

  // Exactly one trip exists for the request and it belongs to the first driver.
  const staff = await signIn(browser, STAFF_PHONE)
  const trips = await api<{ data: { results: { trip_request: number; driver: string }[] } }>(
    staff.page,
    'GET',
    '/admin/trips/',
  )
  const forRequest = trips.body.data.results.filter((t) => t.trip_request === first.requestId)
  expect(forRequest).toHaveLength(1)
  expect(forRequest[0].driver).toBe(first.driver.phone)

  // The losing driver sees the outcome.
  await second.page.goto('/driver/interests')
  await expect(second.page.getByTestId('driver-interest').first()).toContainText('لم يتم اختيارك')
  await expect(second.page.getByRole('link', { name: 'تفاصيل المشوار' })).toHaveCount(0)
})

test('AC9/AC10/AC14: trip must start before it completes; every state change is logged', async ({
  browser,
}) => {
  const { driver, customer, requestId } = await confirmedTrip(browser)
  const tripId = Number(driver.page.url().match(/trips\/(\d+)/)![1])
  const dp = driver.page

  // Not started yet: no way to complete in the UI, and the API refuses too.
  await expect(dp.getByText('مؤكد', { exact: true })).toBeVisible()
  await expect(dp.getByRole('button', { name: 'إنهاء المشوار' })).toHaveCount(0)
  expect((await api(dp, 'POST', `/trips/${tripId}/complete/`)).status).toBe(409)
  // The customer cannot start it.
  await customer.page.goto(`/trips/${tripId}`)
  await expect(customer.page.getByRole('button', { name: 'بدء المشوار' })).toHaveCount(0)
  expect((await api(customer.page, 'POST', `/trips/${tripId}/start/`)).status).toBe(400)

  await dp.getByRole('button', { name: 'بدء المشوار' }).click()
  await expect(dp.getByTestId('status')).toHaveText('جارٍ')
  // Started trips cannot be cancelled or started again.
  await expect(dp.getByRole('button', { name: 'إلغاء المشوار' })).toHaveCount(0)
  expect((await api(dp, 'POST', `/trips/${tripId}/start/`)).status).toBe(409)
  expect((await api(dp, 'POST', `/trips/${tripId}/cancel/`)).status).toBe(409)

  dp.once('dialog', (dialog) => dialog.accept())
  await dp.getByRole('button', { name: 'إنهاء المشوار' }).click()
  await expect(dp.getByTestId('status')).toHaveText('مكتمل')
  await expect(dp.getByRole('button', { name: 'إنهاء المشوار' })).toHaveCount(0)

  // Audit trail, read as staff.
  const staff = await signIn(browser, STAFF_PHONE)
  type Detail = { data: { history: { to_status: string; created_at: string }[] } }
  const trip = await api<Detail>(staff.page, 'GET', `/admin/trips/${tripId}/`)
  expect(trip.body.data.history.map((e) => e.to_status)).toEqual(['CONFIRMED', 'IN_PROGRESS', 'COMPLETED'])
  expect(trip.body.data.history.every((e) => !!e.created_at)).toBe(true)
  const request = await api<Detail>(staff.page, 'GET', `/admin/requests/${requestId}/`)
  expect(request.body.data.history.map((e) => e.to_status)).toEqual(['OPEN', 'CONFIRMED'])
})

test('customer cancels a confirmed trip before it starts and the driver is freed', async ({ browser }) => {
  const { driver, customer } = await confirmedTrip(browser)
  const tripUrl = driver.page.url()
  await customer.page.goto(tripUrl)
  customer.page.once('dialog', (dialog) => dialog.accept())
  await customer.page.getByRole('button', { name: 'إلغاء المشوار' }).click()
  await expect(customer.page.getByTestId('status')).toHaveText('ملغي')

  await driver.page.reload()
  await expect(driver.page.getByTestId('status')).toHaveText('ملغي')
  await expect(driver.page.getByRole('button', { name: 'بدء المشوار' })).toHaveCount(0)
  const tripId = Number(tripUrl.match(/trips\/(\d+)/)![1])
  expect((await api(driver.page, 'POST', `/trips/${tripId}/start/`)).status).toBe(409)
})

test('AC12: an expired request can no longer be confirmed', async ({ browser }) => {
  const { customer, driver, requestId } = await interestedPair(browser)
  // The agreement form is open (and filled in) while the request's time runs out underneath it.
  await interestCard(customer.page, driver.phone)
    .getByRole('button', { name: 'اتفقنا، أريد تأكيد هذا السائق' })
    .click()
  await customer.page.getByLabel('السعر المتفق عليه').fill('45')
  const res = await customer.page.request.post(`${BACKEND_URL}/e2e/expire/${requestId}/`)
  expect(res.ok()).toBe(true)
  await customer.page.getByRole('button', { name: 'تأكيد المشوار' }).click()
  await expect(customer.page.getByRole('alert')).toContainText('expired')
  await customer.page.goto(`/customer/requests/${requestId}`)
  await expect(customer.page.locator('.badge')).toHaveText('منتهي')
  await expect(customer.page.getByText('تم تأكيد المشوار')).toHaveCount(0)
})

test('AC13: the real state shows up after reconnecting, with no notification involved', async ({
  browser,
}) => {
  const { driver, customer } = await interestedPair(browser)
  await driver.page.goto('/driver/interests')
  await expect(driver.page.getByTestId('driver-interest').first()).toContainText('بانتظار العميل')

  await driver.context.setOffline(true)
  await expect(driver.page.getByRole('status')).toContainText('لا يوجد اتصال')
  await chooseDriver(customer.page, driver.phone)
  await expect(customer.page.getByText('تم تأكيد المشوار')).toBeVisible()

  // Still the old (cached) view while offline, then the server state arrives when the connection returns.
  await expect(driver.page.getByTestId('driver-interest').first()).toContainText('بانتظار العميل')
  await driver.context.setOffline(false)
  await expect(driver.page.getByTestId('driver-interest').first()).toContainText('تم اختيارك')
  await expect(driver.page.getByRole('link', { name: 'تفاصيل المشوار' })).toBeVisible()
})

test('a participant can report a problem with a trip and staff resolves it', async ({ browser }) => {
  const { driver, customer } = await confirmedTrip(browser)
  await customer.page.goto(driver.page.url())
  await customer.page.getByRole('button', { name: 'الإبلاغ عن مشكلة' }).click()
  const reason = `e2e report ${Date.now()}`
  await customer.page.getByLabel('ما المشكلة؟').fill(reason)
  await customer.page.getByRole('button', { name: 'إرسال البلاغ' }).click()
  await expect(customer.page.getByText('وصلنا بلاغك')).toBeVisible()

  const staff = await signIn(browser, STAFF_PHONE)
  await staff.page.goto('/admin')
  await staff.page.getByRole('tab', { name: 'البلاغات' }).click()
  const report = staff.page.getByTestId('admin-report').filter({ hasText: reason })
  await expect(report).toContainText(driver.phone)
  await report.getByPlaceholder('ملاحظة المراجعة').fill('تمت المراجعة')
  await report.getByRole('button', { name: 'تمت المعالجة' }).click()
  await expect(report).toContainText('RESOLVED')
  await expect(report.getByRole('button')).toHaveCount(0)
})
