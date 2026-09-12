import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useBillingPlans, fallbackPlans } from '../hooks/useBillingPlans'
import { getAvailablePlans } from '../services/paymentService'

vi.mock('../services/paymentService', () => ({ getAvailablePlans: vi.fn() }))

describe('useBillingPlans', () => {
  it('starts with fallback plans when the billing service is unavailable', async () => {
    getAvailablePlans.mockRejectedValue(new Error('offline'))

    const { result } = renderHook(() => useBillingPlans())

    expect(result.current).toEqual(fallbackPlans)
    await waitFor(() => expect(getAvailablePlans).toHaveBeenCalledOnce())
  })

  it('maps plans returned by the billing service', async () => {
    getAvailablePlans.mockResolvedValue({
      plans: {
        plus: {
          name: 'Plus',
          price: 15,
          billing_cycle: 'monthly',
          features: { ai_composition: true, internal_flag: false },
        },
      },
    })

    const { result } = renderHook(() => useBillingPlans())

    await waitFor(() => expect(result.current[0]).toMatchObject({ id: 'plus', price: 15, period: '/month' }))
    expect(result.current[0].features).toEqual(['ai composition'])
  })
})
