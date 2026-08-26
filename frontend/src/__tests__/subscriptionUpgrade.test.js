import { describe, expect, it } from 'vitest'
import { getRecommendedPlan, getUpgradeSuggestion } from '../utils/subscriptionUtils'

describe('upgrade recommendations', () => {
  it('raises a critical suggestion near exhaustion', () =>
    expect(getUpgradeSuggestion(96, 100).priority).toBe('critical'))
  it('recommends Plus when Personal usage grows', () =>
    expect(getRecommendedPlan('personal', { aiCreditsUsed: 81 })).toBe('plus'))
})
