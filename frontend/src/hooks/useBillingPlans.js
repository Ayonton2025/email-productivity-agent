import { useEffect, useState } from 'react'
import { logger } from '../utils/logger.js'
import { getAvailablePlans } from '../services/paymentService'

export const fallbackPlans = [
  {
    id: 'personal',
    name: 'Free',
    price: 0,
    period: '/day',
    features: ['50 AI credits/day', '1 email account'],
    cta: 'Current Plan',
    highlighted: false,
    disabled: false,
    perks: [],
  },
  {
    id: 'plus',
    name: 'Plus',
    price: 12,
    period: '/month',
    features: ['1,500 AI credits/month', '3 email accounts'],
    cta: 'Upgrade to Plus',
    highlighted: true,
    disabled: false,
    perks: [],
  },
  {
    id: 'professional',
    name: 'Professional',
    price: 29,
    period: '/month',
    features: ['5,000 AI credits/month', 'Unlimited accounts'],
    cta: 'Upgrade to Professional',
    highlighted: false,
    disabled: false,
    perks: [],
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: null,
    period: 'Custom',
    features: ['Enterprise features'],
    cta: 'Contact Sales',
    highlighted: false,
    disabled: false,
    perks: [],
  },
]

export function useBillingPlans() {
  const [plans, setPlans] = useState(fallbackPlans)

  useEffect(() => {
    const loadPlans = async () => {
      try {
        const data = await getAvailablePlans()
        const serverPlans = Object.entries(data?.plans || {}).map(([id, plan]) => ({
          id,
          name: plan.name || id,
          price: typeof plan.price === 'number' ? plan.price : null,
          period: plan.billing_cycle === 'monthly' ? '/month' : plan.billing_cycle === 'annual' ? '/year' : '',
          description: plan.description || '',
          features: Object.entries(plan.features || {})
            .filter(([, enabled]) => Boolean(enabled))
            .map(([feature]) => feature.replace(/_/g, ' ')),
          cta: id === 'enterprise' ? 'Contact Sales' : `Upgrade to ${plan.name || id}`,
          highlighted: id === 'professional',
          disabled: false,
          perks: [],
        }))
        setPlans(serverPlans.length ? serverPlans : fallbackPlans)
      } catch (error) {
        logger.warn('Failed to load plans from backend, using fallback plans', error)
        setPlans(fallbackPlans)
      }
    }

    loadPlans()
  }, [])

  return plans
}
