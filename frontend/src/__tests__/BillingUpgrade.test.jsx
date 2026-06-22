import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import BillingUpgrade from '../components/billing/BillingUpgrade';
import { AuthProvider } from '../context/AuthContext';

// Basic render test and Paystack default behavior
describe('BillingUpgrade', () => {
  it('renders plan cards and starts hosted checkout flow without preselecting payment controls', async () => {
    render(
      <AuthProvider>
        <BillingUpgrade />
      </AuthProvider>
    );

    // Expect plan price elements to render (e.g., $)
    const priceElems = await screen.findAllByText(/\$/i);
    expect(priceElems.length).toBeGreaterThan(0);

    // Checkout now defers payment method selection to hosted provider UI
    expect(
      screen.getByText(/opens hosted checkout with card as default/i)
    ).toBeDefined();
  });
});
