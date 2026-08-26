import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '../services/api'
import { getAvailablePaymentMethods, initiateUpgrade, processPaystackPayment } from '../services/paymentService'

vi.mock('../services/api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

describe('payment service', () => {
  beforeEach(() => vi.clearAllMocks())
  it('sends normalized upgrade details', async () => {
    api.post.mockResolvedValue({ data: { success: true } })
    await initiateUpgrade('plus', 'card', { countryCode: 'KE', preferLocalCurrency: true })
    expect(api.post).toHaveBeenCalledWith('/billing/upgrade', {
      plan_id: 'plus',
      payment_method: 'card',
      country_code: 'KE',
      prefer_local_currency: true,
    })
  })
  it('loads country-specific payment methods', async () => {
    api.get.mockResolvedValue({ data: { methods: [] } })
    await getAvailablePaymentMethods('KE')
    expect(api.get).toHaveBeenCalledWith('/billing/payment-methods/KE')
  })
  it('reports a missing Paystack script', () => {
    const old = window.PaystackPop
    window.PaystackPop = undefined
    const onError = vi.fn()
    processPaystackPayment({}, vi.fn(), onError)
    expect(onError).toHaveBeenCalledWith(expect.any(Error))
    window.PaystackPop = old
  })
})
