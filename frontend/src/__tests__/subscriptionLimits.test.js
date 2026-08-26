import { describe, expect, it } from 'vitest'
import { getLimitPercentage, hasReachedLimit, isApproachingLimit } from '../utils/subscriptionUtils'

describe('subscription limits', () => {
  it('detects reached and approaching limits', () => {
    expect(hasReachedLimit(10, 10)).toBe(true)
    expect(isApproachingLimit(8, 10)).toBe(true)
  })
  it('caps percentages and handles unlimited plans', () => {
    expect(getLimitPercentage(12, 10)).toBe(100)
    expect(getLimitPercentage(500, Infinity)).toBe(0)
  })
})
