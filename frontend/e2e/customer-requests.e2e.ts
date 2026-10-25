import { expect, test } from '@playwright/test'
import { api, createRequest, newNote, signInAs } from './helpers'

test('AC1/AC2: customer creates a valid request, invalid ones are rejected, status is visible', async ({
  browser,
}) => {
  const { page } = await signInAs(browser, 'customer')
  await page.getByRole('link', { name: 'اطلب توصيلة جديدة' }).click()

  const submit = page.getByRole('button', { name: 'نشر الطلب' })
  await expect(submit).toBeDisabled() // neither pickup nor destination chosen
  await page.getByLabel('مكان الركوب').selectOption({ label: 'المحطة' })
  await expect(submit).toBeDisabled() // destination missing
  await page.getByLabel('الوجهة').selectOption({ label: 'المحطة' })
  await expect(page.getByRole('alert')).toContainText('يجب أن يكونا مختلفين')
  await expect(submit).toBeDisabled()

  await page.getByLabel('الوجهة').selectOption({ label: 'الأربعين' })
  await expect(submit).toBeEnabled()
  await submit.click()

  await expect(page.getByRole('heading', { name: 'تفاصيل الطلب' })).toBeVisible()
  await expect(page.getByText('المحطة ← الأربعين')).toBeVisible()
  await expect(page.locator('.badge')).toHaveText('مفتوح')

  await page.goto('/customer/requests')
  await expect(page.getByRole('link', { name: /المحطة ← الأربعين/ })).toBeVisible()
  await expect(page.locator('.badge').first()).toHaveText('مفتوح')
})

test('AC2 (server side): the API itself rejects a request without a destination', async ({ browser }) => {
  const { page } = await signInAs(browser, 'customer')
  const res = await api(page, 'POST', '/requests/', { pickup_area: 1 })
  expect(res.status).toBe(400)
})

test('customer edits then cancels a request', async ({ browser }) => {
  const { page } = await signInAs(browser, 'customer')
  const note = newNote('edit')
  await createRequest(page, { note })

  await page.getByRole('link', { name: 'تعديل الطلب' }).click()
  await expect(page.getByRole('heading', { name: 'تعديل الطلب' })).toBeVisible()
  await page.getByLabel('الوجهة').selectOption({ label: 'المعلمين' })
  await page.getByRole('button', { name: 'حفظ التعديلات' }).click()
  await expect(page.getByText('المحطة ← المعلمين')).toBeVisible()

  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'إلغاء الطلب' }).click()
  await expect(page.locator('.badge')).toHaveText('ملغي')
  // Cancelled requests offer no more actions.
  await expect(page.getByRole('button', { name: 'إلغاء الطلب' })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'تعديل الطلب' })).toHaveCount(0)
})
