import { describe, expect, it } from 'vitest'
import { formatLimit } from '../utils/subscriptionUtils'

describe('limit formatting', () => {
  it('formats unlimited and thousand values', () => {
    expect(formatLimit(Infinity)).toBe('Unlimited')
    expect(formatLimit(1500)).toBe('1.5k')
  })
})
