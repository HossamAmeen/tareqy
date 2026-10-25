import { expect, test } from '@playwright/test'
import {
  createRequest,
  goLive,
  interestCard,
  matchedRequest,
  newNote,
  openMatches,
  signInAs,
  verifyDriver,
} from './helpers'

test('AC3: an unverified driver is blocked, a verified one toggles receiving on and off', async ({
  browser,
}) => {
  const driver = await signInAs(browser, 'driver')
  const { page } = driver
  await expect(page.getByTestId('unverified')).toBeVisible()
  await expect(page.getByRole('button', { name: 'ابدأ استقبال الطلبات' })).toBeDisabled()

  await verifyDriver(browser, driver.phone)
  await page.reload()
  await expect(page.getByTestId('unverified')).toHaveCount(0)

  await page.getByLabel('الوجهة').selectOption({ label: 'الأربعين' })
  await page.getByRole('button', { name: 'تحديد الوجهة' }).click()
  await expect(page.getByText('تنتهي')).toBeVisible()

  await page.getByRole('button', { name: 'ابدأ استقبال الطلبات' }).click()
  await expect(page.getByText('استقبال الطلبات: مفعّل')).toBeVisible()
  await expect(page.getByTestId('freshness')).toContainText('حديث')
  await expect(page.getByTestId('freshness')).toContainText('المحطة')

  await page.getByRole('button', { name: 'إيقاف استقبال الطلبات' }).click()
  await expect(page.getByText('استقبال الطلبات: متوقف')).toBeVisible()
})

test('AC4/AC11: matching requests show up, and closed or cancelled ones disappear', async ({ browser }) => {
  const driver = await goLive(browser)
  const customer = await signInAs(browser, 'customer')
  const keep = newNote('keep')
  const cancelled = newNote('cancel')
  await createRequest(customer.page, { note: keep })
  await customer.page.goto('/customer')
  await createRequest(customer.page, { note: cancelled })

  await openMatches(driver.page)
  await expect(matchedRequest(driver.page, keep)).toBeVisible()
  await expect(matchedRequest(driver.page, cancelled)).toBeVisible()
  await expect(matchedRequest(driver.page, keep)).toContainText('المحطة ← الأربعين')

  customer.page.once('dialog', (dialog) => dialog.accept())
  await customer.page.getByRole('button', { name: 'إلغاء الطلب' }).click()
  await expect(customer.page.locator('.badge')).toHaveText('ملغي')

  await driver.page.reload()
  await expect(matchedRequest(driver.page, keep)).toBeVisible()
  await expect(matchedRequest(driver.page, cancelled)).toHaveCount(0)
})

test('non-matching requests are not shown to the driver', async ({ browser }) => {
  const driver = await goLive(browser)
  const customer = await signInAs(browser, 'customer')
  const other = newNote('other-route')
  await createRequest(customer.page, { note: other, pickup: 'المعلمين', destination: 'المحطة' })
  await openMatches(driver.page)
  await expect(matchedRequest(driver.page, other)).toHaveCount(0)
})

test('AC5/AC6/AC7: interest is not duplicated and does not confirm; the customer can contact the driver', async ({
  browser,
}) => {
  const driver = await goLive(browser)
  const customer = await signInAs(browser, 'customer')
  const note = newNote('interest')
  await createRequest(customer.page, { note })

  await openMatches(driver.page)
  const card = matchedRequest(driver.page, note)
  await card.getByRole('button', { name: 'مهتم' }).click()
  await expect(card.getByRole('button', { name: 'سحب الاهتمام' })).toBeVisible()
  // Withdraw and show interest again: still a single interest.
  await card.getByRole('button', { name: 'سحب الاهتمام' }).click()
  await expect(card.getByRole('button', { name: 'مهتم' })).toBeVisible()
  await card.getByRole('button', { name: 'مهتم' }).click()
  await expect(card.getByRole('button', { name: 'سحب الاهتمام' })).toBeVisible()
  await driver.page.reload()
  await expect(matchedRequest(driver.page, note).getByRole('button', { name: 'سحب الاهتمام' })).toBeVisible()

  // The customer sees exactly one interested driver, with ways to contact them, and the request is still open.
  await customer.page.reload()
  await expect(customer.page.getByTestId('interest')).toHaveCount(1)
  const interest = interestCard(customer.page, driver.phone)
  await expect(interest.getByRole('link', { name: 'اتصال' })).toHaveAttribute('href', `tel:${driver.phone}`)
  await expect(interest.getByRole('link', { name: 'واتساب' })).toHaveAttribute('href', /wa\.me\//)
  await expect(customer.page.locator('.badge')).toHaveText('مفتوح')

  // Interest alone confirms nothing: the driver still has no trip.
  await driver.page.goto('/driver/interests')
  await expect(driver.page.getByTestId('driver-interest').first()).toContainText('بانتظار العميل')
  await expect(driver.page.getByRole('link', { name: 'تفاصيل المشوار' })).toHaveCount(0)

  // Marking contact reveals the customer's number to the driver.
  await interest.getByRole('button', { name: 'تم التواصل' }).click()
  await driver.page.reload()
  await expect(driver.page.getByRole('link', { name: 'اتصال بالعميل' })).toBeVisible()
  await expect(driver.page.getByTestId('driver-interest').first()).toContainText('تم التواصل معك')
})
