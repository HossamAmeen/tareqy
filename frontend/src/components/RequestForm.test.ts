import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import RequestForm from './RequestForm.vue'

const areas = [
  { id: 1, name: 'المحطة' },
  { id: 2, name: 'الأربعين' },
]

function mountForm(props = {}) {
  return mount(RequestForm, { props: { areas, submitLabel: 'نشر', ...props } })
}

describe('RequestForm', () => {
  it('disables submit until both areas are chosen', async () => {
    const wrapper = mountForm()
    expect(wrapper.find('button[type=submit]').attributes('disabled')).toBeDefined()
    const [pickup, destination] = wrapper.findAll('select')
    await pickup.setValue(1)
    expect(wrapper.find('button[type=submit]').attributes('disabled')).toBeDefined()
    await destination.setValue(2)
    expect(wrapper.find('button[type=submit]').attributes('disabled')).toBeUndefined()
  })

  it('rejects identical pickup and destination', async () => {
    const wrapper = mountForm()
    const [pickup, destination] = wrapper.findAll('select')
    await pickup.setValue(1)
    await destination.setValue(1)
    expect(wrapper.text()).toContain('يجب أن يكونا مختلفين')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('emits a payload with numeric area ids and trimmed notes', async () => {
    const wrapper = mountForm()
    const [pickup, destination] = wrapper.findAll('select')
    await pickup.setValue(1)
    await destination.setValue(2)
    await wrapper.find('input').setValue('  البوابة  ')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')![0]).toEqual([{ pickup_area: 1, destination_area: 2, notes: 'البوابة' }])
  })

  it('shows approximate location by default', () => {
    expect(mountForm().get('[data-testid=precision]').text()).toContain('تقريبي')
  })

  it('prefills values when editing', () => {
    const initial = {
      id: 5,
      pickup_area: areas[0],
      destination_area: areas[1],
      pickup_location_is_precise: true,
      notes: 'x',
      preferred_pickup_at: null,
      status: 'OPEN' as const,
      expires_at: '',
      created_at: '',
    }
    const wrapper = mountForm({ initial })
    expect((wrapper.findAll('select')[0].element as HTMLSelectElement).value).toBe('1')
    expect(wrapper.get('[data-testid=precision]').text()).toContain('دقيق')
  })
})
