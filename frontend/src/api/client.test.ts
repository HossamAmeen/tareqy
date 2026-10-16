import { beforeEach, describe, expect, it } from 'vitest'
import { errorMessage, loadTokens, saveTokens } from './client'

describe('token storage', () => {
  beforeEach(() => localStorage.clear())

  it('round-trips tokens', () => {
    saveTokens({ access: 'a', refresh: 'r' })
    expect(loadTokens()).toEqual({ access: 'a', refresh: 'r' })
    saveTokens(null)
    expect(loadTokens()).toBeNull()
  })

  it('ignores corrupted storage', () => {
    localStorage.setItem('tariqi.tokens', '{oops')
    expect(loadTokens()).toBeNull()
  })
})

describe('errorMessage', () => {
  it('prefers the first field error', () => {
    const err = {
      response: {
        data: { message: 'Validation failed.', errors: { phone: ['Enter a valid phone number.'] } },
      },
    }
    expect(errorMessage(err)).toBe('Enter a valid phone number.')
  })

  it('falls back to the API message, then the default', () => {
    expect(errorMessage({ response: { data: { message: 'Invalid or expired code.', errors: {} } } })).toBe(
      'Invalid or expired code.',
    )
    expect(errorMessage(new Error('network'), 'fallback')).toBe('fallback')
  })
})
