import { describe, expect, it } from 'vitest';
import { canAccessFeature, getRequiredPlanForFeature } from '../utils/subscriptionUtils';

describe('feature entitlements', () => {
  it('checks enabled and disabled features', () => {
    expect(canAccessFeature('plus', 'campaigns')).toBe(true);
    expect(canAccessFeature('personal', 'campaigns')).toBe(false);
  });
  it('returns the minimum feature plan', () =>
    expect(getRequiredPlanForFeature('apiAccess')).toBe('professional'));
});
