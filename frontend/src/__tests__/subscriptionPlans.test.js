import { describe, expect, it } from 'vitest';
import { getPlanLimits } from '../utils/subscriptionUtils';

describe('subscription plans', () => {
  it('returns the requested plan case-insensitively', () =>
    expect(getPlanLimits('PLUS').name).toBe('Plus'));
  it('falls back to Personal for unknown plans', () =>
    expect(getPlanLimits('unknown').name).toBe('Personal'));
});
